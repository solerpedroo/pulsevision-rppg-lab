# GREEN, CHROM e POS — Onda 4

Os três métodos compartilham o engine offline; o registro seleciona a extração
e os contratos preservam BPM null e motivos de falha.

## Execução

```bash
uv run python -m rppg_core.signals.synthetic \
  --output artifacts/classical-demo/rgb_synthetic.csv --bpm 90
uv run python -m rppg_core.signals.analyze_rgb artifacts/classical-demo/rgb_synthetic.csv \
  --method all --method-config configs/methods/classical-v1.json \
  --output artifacts/classical-demo/comparison
```

Saída comparison.json: parâmetros, hash da entrada, versões, estimativas e
contagens/cobertura por método, além do sinal e PSD da última janela.
comparison.png mostra os três sinais, espectros e BPM ao longo das janelas;
falhas ficam como lacunas, sem carregar resultado anterior.
Essas contagens não são métricas de precisão contra um sensor.

Para um único método, use --method CHROM ou --method POS; GREEN continua padrão.
Saídas individuais: estimates.json e chrom_diagnostics.png/pos_diagnostics.png.
Não reutilizar diretório existente. O engine mantém imports da Onda 3 compatíveis.

## API

```python
from rppg_core.estimation.pipeline import analyze_trace
from rppg_core.methods.config import MethodConfig
from rppg_core.signals.synthetic import synthetic_rgb

t, rgb = synthetic_rgb(bpm=90)
for window in analyze_trace(t, rgb, method="POS", method_config=MethodConfig()):
    print(window.estimate.bpm, window.estimate.reasons)
```

get_method seleciona extrator no registro imutável. MethodSignal expõe valid_mask,
filtered e edge_margin_s. A análise recusa suporte insuficiente e projeções
degeneradas, em vez de fabricar uma forma de onda.
Configuração versionada em configs/methods/classical-v1.json.

## Interpretação

Comparações --method all usam o mesmo agendamento, ROI, máscara válida, banda,
ordem, Welch e margem útil. CHROM filtra componentes antes da escala relativa;
POS/GREEN filtram depois da extração. Escalas de amplitude diferem: valores maiores
de sinal/PSD não significam maior qualidade.
Análises individuais podem cortar margens diferentes; use o modo comparativo
para controlar isso. Não há causalidade/live nem qualidade clínica calibrada.

Detalhes numéricos e diferenças de referência: ADR 0006 e
docs/research/classical-references.md.
