# zapmask

*[English](README.md) · [Português (BR)](README.pt-BR.md)*

ANATEL phone-number hashcat masks — mobile (SMP) + landline (STFC).

## Authorized-use notice

> zapmask is for auditing networks you own or are explicitly authorized to test. It is built entirely on public ANATEL numbering data and ships no personal data, handshakes, or targeting.

## Getting the data

zapmask does not download anything for you. Get the source dump yourself from the ABR Telecom EASI portal:

```
https://easi.abrtelecom.com.br/nsapn/#/public/files
```

The portal is captcha-gated, so this has to be a manual download. Pick a numbering-plan export:

- **SMP** (`Serviço Móvel Pessoal`) — mobile allocations. Feeds mobile masks.
- **STFC** (`Serviço Telefônico Fixo Comutado`) — landline allocations. Feeds landline masks.

Both come as semicolon-delimited `.txt` files. zapmask auto-detects which one you gave it by column count (7 columns → SMP, 13 columns → STFC); pass `--service smp` or `--service stfc` to override the detection if needed.

## Try it with sample data

No dump yet? Two **synthetic** sample files ship in [`examples/`](examples/) so you can try zapmask without the portal — fictional carriers and prefixes, not real allocations:

```
python -m zapmask --src examples/SMP_sample.txt --ddd 21 --out out    # mobile
python -m zapmask --src examples/STFC_sample.txt --ddd 21 --out out   # landline (shows sub-thousand decomposition)
```

See [`examples/README.md`](examples/README.md) for what each file exercises.

## Install

Requires Python 3.9+. No third-party dependencies.

Install the `zapmask` command onto your PATH:

```
pipx install .
```

Or run it in place without installing — these two are equivalent:

```
python -m zapmask
python run.py
```

## Interactive mode (drag & drop)

Don't want to remember flags? **Drag an ANATEL `.txt` onto `run.py`** and answer the prompts. It's a colorful, zero-dependency wizard — it detects whether the file is SMP or STFC, shows which area codes the file actually contains, and prompts for every option with its default in brackets (press Enter to accept):

```
python run.py                          # start the wizard, it asks for the file
python run.py SMP_20260829_GERAL.txt   # same as dragging the file onto run.py
```

On Windows the file's path is passed straight through when you drop it on `run.py`; on macOS/Linux, launch it and paste (or drop) the path at the first prompt. Either way you get:

```
zapmask - interactive mode

Detected SMP  -  2 area code(s) present
  11      1   21  3,821

Area code(s) to build masks for  (e.g. 21,22 or 21-43, or 'all') [all]:
Digit length(s)  (valid: 8,9,11) [9]:
Granularity (fine/coarse/both) [both]:
Coarse target (min base words per mask) [240000]:
Output directory [masks]:
```

The area-code prompt defaults to **`all`** — press Enter to build masks for every DDD in the file, so you never have to type out a long list. You can also enter specific codes (`21,22`), a **range** (`21-43`), or mix them (`21-24,31,41-43`). Ranges expand to only the codes actually present in the file, so gaps in the numbering plan are skipped automatically.

**Drop more than one file at once** (e.g. a mobile SMP export *and* a landline STFC export) and each is handled in turn — the wizard detects each file's service and asks its options separately, writing both mask sets.

The classic flag-driven CLI below is unchanged — pass any `--flag` (or use `python -m zapmask`) and you get the non-interactive interface, ideal for scripts and CI.

## Usage

Basic run — mobile masks for DDD 21 (Rio de Janeiro), default 9-digit length:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21
```

This writes two files to `masks/`:

- `masks/smp_21_9digit_fine.hcmask` — 3,821 masks / 38.2M candidates, tight to the assigned ranges.
- `masks/smp_21_9digit_coarse.hcmask` — 51 masks / 51M candidates, 25.2% over-coverage, sized to keep a GPU saturated.

Emit more than one digit length at once with `--length`:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --length 9,11
```

`9` is the bare subscriber number; `11` prepends the DDD. Add `8` to also emit the legacy pre-2012 form with no leading 9:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --length 9,11,8
```

Landline dumps work the same way, just point `--src` at an STFC export:

```
python -m zapmask --src STFC_20260829_GERAL.txt --ddd 21
```

Landline numbers default to 8 digits. Valid lengths differ by service:

| service | valid `--length` values | default |
|---|---|---|
| SMP (mobile) | 9, 11, 8 | 9 |
| STFC (landline) | 8, 10 | 8 |

If your GPU is bigger than the default coarse mask assumes, raise `--coarse-target` so coarse masks are sized for it:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --coarse-target 2500000
```

Other flags: `--granularity {fine,coarse,both}` (default `both`) to emit only one flavor, and `--out DIR` (default `masks`) to change the output directory.

Feed a `coarse` file straight to hashcat against a captured handshake (`-m 22000` is WPA-PBKDF2-PMKID+EAPOL):

```
hashcat -m 22000 -a 3 <hash.hc22000> masks/smp_21_9digit_coarse.hcmask
```

The exact command line is also written into the header comment of every `.hcmask` file zapmask produces, so you don't have to remember it.

## fine vs coarse — why both exist

`-m 22000` is a slow hash (PBKDF2-backed WPA/WPA2), and hashcat's `-a 3` (mask attack) has no inner-loop amplifier the way a fast hash with rule/combinator attacks does — every candidate the mask produces is exactly one base word tried against the target. To keep a GPU's pipeline full, hashcat needs roughly

```
kernel_power ≈ compute_units × threads × accel
```

base words in flight at once (`hashcat -m 22000 -b` prints your device's actual `kernel_power`). Hand it a mask that's smaller than that and it can't fill the pipeline — you'll see it warn something like *"the wordlist or mask you are using is too small"* and throughput craters.

That's the reason zapmask emits two granularities of the same coverage:

- **`fine`** masks are the exact assigned keyspace — one mask per allocated block, with just enough trailing `?d` digits to cover it and essentially no over-coverage. Precise, but individual masks can be far smaller than a GPU needs.
- **`coarse`** masks fix fewer leading digits per mask, so each one expands to at least `--coarse-target` base words (default `240000`, i.e. masks of roughly 1,000,000 candidates). That's large enough to keep most GPUs saturated. This does mean a coarse mask covers some numbers that were never actually assigned — the trade is over-coverage in exchange for throughput — but it never *drops* a valid number: coarse masks are strictly a superset of the fine coverage.

Use `coarse` for the actual hashcat run; keep `fine` around as the precise record of what was assigned.

## Carrier ordering

Within a `.hcmask` file, masks are emitted carrier-sorted — ranked by total allocation across the carriers in your selected area code(s), largest first — so if you kill the job early, the masks most likely to hit are tried first.

For `coarse` masks specifically, one shortened stem can span numbers from more than one carrier (that's the point of shortening it). In that case the group is attributed to whichever carrier present in the group has the largest total allocation among the carriers in your selected DDD(s), not to whichever carrier happens to hold the most numbers within that one group. This keeps the ordering deterministic across runs instead of depending on a per-group majority vote.

## Output

Files are named:

```
<service>_<ddd>_<length>digit_<fine|coarse>.hcmask
```

e.g. `smp_21_9digit_coarse.hcmask` for mobile, DDD 21, 9-digit, coarse granularity.

The `<ddd>` part is the single area code when you pick one; when you select several it collapses to `all` (every code in the file) or `multi` (some of them) so the name stays short instead of listing dozens of codes — e.g. `smp_all_9digit_coarse.hcmask`. The exact codes are still recorded in the file's header comment.

Every file opens with a header describing what it contains:

```
# zapmask smp 9-digit fine | DDD 21
# source: SMP_20260829_GERAL.txt
# carriers (biggest first): VIVO, CLARO, TIM, OI
# 3,821 masks / 38,210,000 candidates / 0.0% over-coverage
# hashcat -m 22000 -a 3 <hash.hc22000> <this file>
```

or, for the coarse companion file:

```
# zapmask smp 9-digit coarse | DDD 21
# source: SMP_20260829_GERAL.txt
# carriers (biggest first): VIVO, CLARO, TIM, OI
# 51 masks / 51,000,000 candidates / 25.2% over-coverage
# hashcat -m 22000 -a 3 <hash.hc22000> <this file>
```

followed by one hashcat mask per line.

## License

MIT, see [LICENSE](LICENSE).
