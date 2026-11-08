# Benchmark Lab — Onda 10

## Demonstração artificial

Da raiz, após setup normal de Python/Node:

```bash
uv run python -m benchmarks.study demo --output artifacts/study-demo
npm run dev -w apps/web
```

Abra http://localhost:3000/benchmark e selecione
`artifacts/study-demo/results/review/benchmark-review-v1.json`.
Use diretório de saída novo: o comando não sobrescreve estudos existentes.
A demonstração é gerada de RGB e referência artificiais, não de pessoas.
Não requer câmera/modelo/API para o Benchmark Lab; testes E2E do monorepo ainda
preparam o modelo para os fluxos de vídeo/live das ondas anteriores.

A página não carrega exemplos automaticamente. JSON é lido nesta aba, sem upload,
localStorage ou fetch dos caminhos declarados no relatório. Limites: 20 MiB,
64 execuções e 100 mil janelas. Arquivo inválido retorna erro sem inventar dados.

## Revisar resultados existentes

```bash
uv run python -m benchmarks.analysis.review \
  artifacts/benchmark-results/benchmark-v1.json \
  --output artifacts/benchmark-review
```

Aceita vários relatórios como argumentos, com IDs run-1/run-2/... na revisão.
Não mistura avaliações artificiais e reais em um pacote. A saída tem:

- `benchmark-review-v1.json`: contrato para a UI, dados e proveniência.
- `summary.json`: métricas por participante/macro, cobertura, exclusões e bootstrap.
- `report.md`: hipótese, método, resultados descritivos, pendências e limites.
- `comparison.png`: MAE macro e cobertura, com unidades/natureza dos dados.

Cada execução original do runner mantém seus CSV/JSON/Markdown/figuras completos.
O conversor registra SHA256 do relatório e preserva o snapshot congelado/ambiente.
Uma referência sem suporte ordenado em janela já excluída aparece como null na
revisão, sem alterar o relatório original. Não é uma nova estimativa do sensor.

## Executar estudo predefinido

Prepare cada manifesto/lock com o fluxo da Onda 6 e crie study.json, por exemplo:

```json
{
  "version": "study-v1",
  "title": "Estudo declarado pelo pesquisador",
  "hypothesis": "Hipótese definida antes de avaliar o conjunto final.",
  "pending": ["Verificar acesso e alinhamento antes de avaliação real."],
  "variants": [
    {
      "id": "baseline",
      "experiment": "A",
      "manifest": "inputs/manifest.json",
      "lock": "inputs/lock.json",
      "split": "development"
    }
  ]
}
```

```bash
uv run python -m benchmarks.study freeze study.json --lock study-lock.json
uv run python -m benchmarks.study run study.json --lock study-lock.json --output artifacts/study-run
```

Paths são relativos ao plano. Inputs, locks, protocolo e código precisam continuar
iguais ao congelamento. A saída guarda resultados por variante, revisão e cópia
do lock do estudo. A execução não baixa datasets nem altera sinais silenciosamente.
Variantes B/D/E exigem entradas/evidências de extração/transformação realmente
preparadas pelo pesquisador; atribuir rótulo de experimento não executa uma
transformação de vídeo. Consulte o draft `benchmarks/protocols/experiments-v1.json`.

## Inspeção na interface

Filtros e agrupamentos são exploratórios. Confira coortes, condições, ROI, janela,
exclusões e suporte comum antes de comparar. Cada linha preserva sua execução.
MAE/RMSE/MedAE/bias macro dão o mesmo peso a cada participante com pares aceitos;
não são métricas agrupadas de todas as janelas. Falhas de sessão são repetidas
por método para contexto e não devem ser somadas como falhas independentes.

Ausência de pares mantém erro ausente. Cobertura conta todas as janelas elegíveis;
exclusões prévias e sessões sem comparação não são abstenções do estimador.
Grupos sem dados não ganham referência/BPM/cobertura inventados. O CSV contém o
recorte completo; o JSON contém a revisão completa, não apenas os grupos na página.

A aba valida forma e consistência, mas não autentica dados/licença/hash contra
arquivos originais. Não usa essas declarações como prova de precisão clínica.
Remover a revisão limpa o estado local, sem apagar fonte ou downloads realizados.

## Validação e pendências

```bash
uv run pytest tests/test_study.py
npm test
npm run test:e2e
```

Teste Python executa runner real em entradas artificiais, compara resumo original
com recomputação, verifica PNG e recusa mutação de plano/entrada congelados.
Testes web cobrem peso por participante, abstenção/exclusão, erro ausente,
elegibilidade, duplicação/natureza inválida e CSV. E2E cobre importação até descarte
com monitoramento da rede, filtros e layout mobile.

Experimentos reais A–E e relatório científico final continuam pendentes de dataset
autorizado e protocolo congelado. Esta entrega prepara infraestrutura e demonstra
execução com dados artificiais. ADR 0012 descreve a decisão.
