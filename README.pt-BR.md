# zapmask

*[English](README.md) · [Português (BR)](README.pt-BR.md)*

Máscaras hashcat de números de telefone da ANATEL — celular (SMP) + fixo (STFC).

## Aviso de uso autorizado

> O zapmask serve para auditar redes que você possui ou tem autorização explícita para testar. Ele é construído inteiramente sobre dados públicos de numeração da ANATEL e não inclui dados pessoais, handshakes nem alvos.

## Obtendo os dados

O zapmask não baixa nada por você. Pegue o dump de origem você mesmo no portal EASI da ABR Telecom:

```
https://easi.abrtelecom.com.br/nsapn/#/public/files
```

O portal é protegido por captcha, então o download precisa ser manual. Escolha uma exportação do plano de numeração:

- **SMP** (`Serviço Móvel Pessoal`) — faixas de celular. Gera as máscaras de celular.
- **STFC** (`Serviço Telefônico Fixo Comutado`) — faixas de telefone fixo. Gera as máscaras de fixo.

Ambos vêm como arquivos `.txt` delimitados por ponto e vírgula. O zapmask detecta automaticamente qual deles você forneceu pela contagem de colunas (7 colunas → SMP, 13 colunas → STFC); use `--service smp` ou `--service stfc` para forçar a detecção, se necessário.

## Experimente com dados de exemplo

Ainda sem um dump? Dois arquivos de exemplo **sintéticos** vêm em [`examples/`](examples/) para você testar o zapmask sem o portal — operadoras e prefixos fictícios, não são faixas reais:

```
python -m zapmask --src examples/SMP_sample.txt --ddd 21 --out out    # celular
python -m zapmask --src examples/STFC_sample.txt --ddd 21 --out out   # fixo (mostra a decomposição de faixas sub-milhar)
```

Veja [`examples/README.md`](examples/README.md) para o que cada arquivo exercita.

## Instalação

Requer Python 3.9+. Sem dependências de terceiros.

```
pipx install .
```

ou execute no lugar, sem instalar — qualquer um destes funciona e é equivalente:

```
python -m zapmask
python run.py
```

## Uso

Execução básica — máscaras de celular para o DDD 21 (Rio de Janeiro), comprimento padrão de 9 dígitos:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21
```

Isso grava dois arquivos em `masks/`:

- `masks/smp_21_9digit_fine.hcmask` — 3.821 máscaras / 38,2 mi de candidatos, restritas às faixas atribuídas.
- `masks/smp_21_9digit_coarse.hcmask` — 51 máscaras / 51 mi de candidatos, 25,2% de cobertura excedente, dimensionadas para manter uma GPU saturada.

Emita mais de um comprimento de dígitos de uma vez com `--length`:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --length 9,11
```

`9` é o número do assinante puro; `11` adiciona o DDD na frente. Inclua `8` para também emitir o formato legado (pré-2012), sem o 9 inicial:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --length 9,11,8
```

Os dumps de fixo funcionam da mesma forma, basta apontar o `--src` para uma exportação STFC:

```
python -m zapmask --src STFC_20260829_GERAL.txt --ddd 21
```

Números fixos usam 8 dígitos por padrão. Os comprimentos válidos variam por serviço:

| serviço | valores válidos de `--length` | padrão |
|---|---|---|
| SMP (celular) | 9, 11, 8 | 9 |
| STFC (fixo) | 8, 10 | 8 |

Se a sua GPU for maior do que a máscara coarse padrão pressupõe, aumente o `--coarse-target` para que as máscaras coarse sejam dimensionadas para ela:

```
python -m zapmask --src SMP_20260829_GERAL.txt --ddd 21 --coarse-target 2500000
```

Outras opções: `--granularity {fine,coarse,both}` (padrão `both`) para emitir só um dos tipos, e `--out DIR` (padrão `masks`) para mudar o diretório de saída.

Passe um arquivo `coarse` direto para o hashcat contra um handshake capturado (`-m 22000` é WPA-PBKDF2-PMKID+EAPOL):

```
hashcat -m 22000 -a 3 <hash.hc22000> masks/smp_21_9digit_coarse.hcmask
```

A linha de comando exata também é escrita no comentário de cabeçalho de todo arquivo `.hcmask` que o zapmask produz, então você não precisa decorá-la.

## fine vs coarse — por que os dois existem

O `-m 22000` é um hash lento (WPA/WPA2 baseado em PBKDF2), e o `-a 3` (ataque de máscara) do hashcat não tem o amplificador de laço interno que um hash rápido tem em ataques de regra/combinador — cada candidato que a máscara produz é exatamente uma base word testada contra o alvo. Para manter o pipeline de uma GPU cheio, o hashcat precisa de aproximadamente

```
kernel_power ≈ compute_units × threads × accel
```

base words simultâneas (`hashcat -m 22000 -b` mostra o `kernel_power` real do seu dispositivo). Dê a ele uma máscara menor que isso e ele não consegue encher o pipeline — você verá um aviso do tipo *"the wordlist or mask you are using is too small"* e a taxa de processamento despenca.

É por isso que o zapmask emite duas granularidades da mesma cobertura:

- As máscaras **`fine`** são o espaço de chaves exatamente atribuído — uma máscara por bloco alocado, com apenas os dígitos `?d` finais necessários para cobri-lo e praticamente nenhuma cobertura excedente. Precisas, mas cada máscara individual pode ser bem menor do que uma GPU precisa.
- As máscaras **`coarse`** fixam menos dígitos iniciais por máscara, de modo que cada uma se expande para pelo menos `--coarse-target` base words (padrão `240000`, ou seja, máscaras de cerca de 1.000.000 de candidatos). Isso é grande o bastante para manter a maioria das GPUs saturada. Em troca, uma máscara coarse cobre alguns números que nunca foram de fato atribuídos — a troca é cobertura excedente por desempenho —, mas ela nunca *descarta* um número válido: as máscaras coarse são estritamente um superconjunto da cobertura fine.

Use `coarse` para a execução real do hashcat; mantenha o `fine` como o registro preciso do que foi atribuído.

## Ordenação por operadora

Dentro de um arquivo `.hcmask`, as máscaras são emitidas ordenadas por operadora — classificadas pela alocação total entre as operadoras do(s) seu(s) DDD(s) selecionado(s), da maior para a menor — então, se você interromper o job cedo, as máscaras com maior chance de acerto são testadas primeiro.

Especificamente para as máscaras `coarse`, um prefixo encurtado pode abranger números de mais de uma operadora (esse é justamente o propósito de encurtá-lo). Nesse caso, o grupo é atribuído à operadora presente no grupo com a maior alocação total entre as operadoras do(s) seu(s) DDD(s) selecionado(s), e não à operadora que por acaso detém mais números dentro daquele grupo específico. Isso mantém a ordenação determinística entre execuções, em vez de depender de uma votação por maioria em cada grupo.

## Saída

Os arquivos são nomeados assim:

```
<serviço>_<ddd>_<comprimento>digit_<fine|coarse>.hcmask
```

por exemplo, `smp_21_9digit_coarse.hcmask` para celular, DDD 21, 9 dígitos, granularidade coarse.

Todo arquivo começa com um cabeçalho que descreve o que ele contém:

```
# zapmask smp 9-digit fine | DDD 21
# source: SMP_20260829_GERAL.txt
# carriers (biggest first): VIVO, CLARO, TIM, OI
# 3,821 masks / 38,210,000 candidates / 0.0% over-coverage
# hashcat -m 22000 -a 3 <hash.hc22000> <this file>
```

ou, para o arquivo coarse correspondente:

```
# zapmask smp 9-digit coarse | DDD 21
# source: SMP_20260829_GERAL.txt
# carriers (biggest first): VIVO, CLARO, TIM, OI
# 51 masks / 51,000,000 candidates / 25.2% over-coverage
# hashcat -m 22000 -a 3 <hash.hc22000> <this file>
```

seguido por uma máscara hashcat por linha.

## Licença

MIT, veja [LICENSE](LICENSE).
