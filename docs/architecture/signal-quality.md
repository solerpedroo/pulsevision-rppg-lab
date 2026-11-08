# Qualidade e abstenção — Onda 5

O estimador retorna BPM ou null, status, motivos e auditoria instrumental.
Não usa porcentagem de confiança clínica.

## CLI

```bash
uv run python -m rppg_core.signals.analyze_rgb artifacts/sessao/rgb_traces.csv \
  --method all --quality-config configs/quality/quality-v1.json \
  --output artifacts/sessao/quality
```

--quality-config funciona tanto para método individual quanto para all.
Saídas JSON incluem quality_config e quality_summary por método:
eligible_windows, accepted_windows, abstained_windows, coverage, status_counts
e reason_counts. Cada estimativa possui quality com métricas/checks/warnings.
Fontes incompletas são sinalizadas; RGB ausente nunca é substituído por zero.
Flags não reconhecidas são rejeitadas com o nome preservado no diagnóstico.

## Uso Python

```python
from rppg_core.estimation.pipeline import analyze_trace
from rppg_core.quality.config import QualityConfig
from rppg_core.quality.continuity import display_estimate
from rppg_core.quality.summary import summarize_quality
from rppg_core.signals.synthetic import synthetic_rgb

t, rgb = synthetic_rgb()
results = [x.estimate for x in analyze_trace(t, rgb, quality_config=QualityConfig())]
summary = summarize_quality(results)
view = display_estimate(results[-1], now_s=results[-1].produced_at_s + 4)
assert view.bpm is None  # A estimativa histórica venceu para exibição como atual.
```

SampleQuality transporta estatísticas/flags opcionais por amostra, na mesma ordem
do RGB; evidence deve ter o mesmo tamanho do trace. load_trace_csv preserva
todas essas informações. load_csv permanece compatível, mas retorna apenas
timestamps/RGB/valid; use a interface completa para não perder causas específicas.
Dados faciais não fornecidos geram warning; não são inferidos dos canais médios.

## Estados e motivos

good permite BPM. unreliable/no_face/insufficient_data não permitem.
degraded marca candidata instável ou estimativa vencida; warming_up representa
recuperação que ainda requer confirmação. Esses dois estados também usam BPM null.
status unsupported_video continua reservado para erros de ingestão.
Catálogo de motivos: packages/rppg_core/quality/reasons.py.
Contrato: packages/rppg_types/models.py e schemas/tipos gerados.

## Continuidade

O engine aplica continuidade por método/ROI; analyze_window isolado não possui
histórico. Ao integrar janelas manualmente, use uma instância de EstimateContinuity
por fluxo, nunca misture sessões/métodos/ROIs. Não filtrar as janelas rejeitadas
antes dessa etapa. Uma falha interrompe o estado de aceitação e exige recuperação.
O helper de exibição recebe sempre o resultado mais recente, inclusive rejeitado;
não buscar o último resultado bom para preencher a tela.
now_s é tempo relativo à sessão, não relógio UTC. produced_at_s segue o fim da
janela offline; não representa tempo de processamento ou data de calendário.

## Validação

```bash
uv run pytest tests/test_quality.py
```

Cobertura inclui adversidades sintéticas, dados CSV com métricas, causas múltiplas,
flicker forte, saturação, escuridão, energia fora da banda, cadência irregular,
confirmação de mudanças, recuperação e vencimento. Regressões GREEN/CHROM/POS
continuam executadas. Não há medição de erro fisiológico nesta onda.
Thresholds, equações e limitações: docs/adrs/0007-instrumental-quality.md.
