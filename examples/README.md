# Example data

These two files are **synthetic** — fictional carriers, zeroed CNPJs, and
made-up prefixes. They let you try `zapmask` without downloading the real
ANATEL dump. They are **not** real allocation data.

- `SMP_sample.txt` — a **mobile (SMP)** numbering file (7 columns). Includes two
  full-block prefixes (each → one `?d?d?d?d` mask), one partial-range prefix
  (`98500`, `0000–4999` → per-thousand masks), an inactive row (dropped), and a
  wrong-DDD row (dropped when you filter to `--ddd 21`).
- `STFC_sample.txt` — a **landline (STFC)** numbering file (13 columns). The
  `3201` prefix uses a sub-thousand range (`1000–1524`) to show landline range
  decomposition into exact masks.

Real files come from the ABR Telecom EASI portal (captcha-gated, download
yourself): https://easi.abrtelecom.com.br/nsapn/#/public/files — named
`SMP_YYYYMMDD_GERAL.txt` (mobile) and `STFC_YYYYMMDD_GERAL.txt` (landline).

## Try it

```bash
# mobile, DDD 21 (writes fine + coarse into ./out)
python -m zapmask --src examples/SMP_sample.txt --ddd 21 --out out

# landline, DDD 21 (demonstrates sub-thousand decomposition)
python -m zapmask --src examples/STFC_sample.txt --ddd 21 --out out
```

Or drag either file onto `run.py` to walk through the interactive wizard
(colorful prompts, defaults shown, area-code ranges and `all`).
