# GREEN offline — Onda 3

Esta etapa estima a frequência dominante de um trace RGB por janelas, com
abstenção explícita. Não valida o pulso de uma pessoa e não é dispositivo médico.

## Demonstração artificial

Na raiz:

```bash
uv sync --locked
uv run python -m rppg_core.signals.synthetic \
  --output artifacts/green-demo/rgb_synthetic.csv --bpm 90
uv run python -m rppg_core.signals.analyze_rgb artifacts/green-demo/rgb_synthetic.csv \
  --output artifacts/green-demo/analysis
```

Diretórios de saída devem ser novos; o comando recusa sobrescrita.
A geração usa seed 42, 30 s/30 Hz e ruído gaussiano de 0,1 unidade RGB por padrão.
--noise e --duration permitem variar essas condições.
Synthetic_rgb também permite fs, seed e harmonic_amplitude em Python.
Esses traces são artificiais; frequência conhecida não equivale a ground truth fisiológico.

## Traços reais da Onda 2

```bash
uv run python -m rppg_core.signals.analyze_rgb artifacts/sessao/rgb_traces.csv \
  --roi forehead --output artifacts/sessao/green
```

Não excluir linhas rejeitadas antes do DSP. O loader mantém timestamps,
RGB ausente como NaN e máscara de validade. Regiões aceitas não são garantia de pulso.
Use roi=combined apenas quando sua composição não muda na janela.

Saída: estimates.json com cada EstimateResult, config, hash e versões; PNG do
sinal filtrado e PSD da última janela, inclusive quando rejeitada. Não oculta
janelas sem estimativa. Todos os resultados estão no JSON; o PNG é diagnóstico.
eligible_windows significa janelas do agendamento, não protocolo de benchmark.
coverage é aceitas/elegíveis desse trace e não pode ser chamada de precisão.

## API Python

```python
from rppg_core.estimation.green_pipeline import analyze_trace
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.synthetic import synthetic_rgb

timestamps, rgb = synthetic_rgb(bpm=90)
for window in analyze_trace(timestamps, rgb, config=SignalConfig()):
    print(window.estimate.bpm, window.estimate.reasons)
```

analyze_window recebe janela explícita, arrays e máscara valid opcional.
Shape, timestamps e limites inconsistentes geram SignalInputError.
Falhas de qualidade em uma janela válida geram EstimateResult com bpm=None.
Status good significa apenas que gates instrumentais iniciais passaram.

## Verificação e resolução

```bash
uv run pytest tests/test_green.py
```

A tolerância sintética usa a largura do bin espectral registrada em metadata,
não um erro clínico prometido. Com janela 20 s e margem de 1 s em cada lado,
o segmento útil de ~18 s dá bins de ~3,33 BPM. Segmentos maiores/menores alteram
a resolução; zero-padding não é utilizado. Ajustes futuros só em validação.
Não há correção geral de harmônicos, robustez a movimento comprovada ou
equivalência com implementação causal TypeScript.
Detalhes numéricos e limites em docs/adrs/0005-offline-green-dsp.md.
