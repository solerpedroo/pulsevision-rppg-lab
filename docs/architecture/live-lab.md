# Live Lab — Onda 9

## Preparar e executar localmente

Da raiz:

```bash
uv sync --locked
npm ci
uv run python scripts/fetch_face_model.py
npm run live:assets
npm run dev -w apps/web
```

Abra http://localhost:3000/live. O Live Lab não precisa da API FastAPI. Use localhost
ou HTTPS e um navegador com Worker, OffscreenCanvas, ImageBitmap, WASM e suporte
ao detector. Chromium foi testado; demais navegadores/dispositivos precisam de QA.

A preparação verifica o modelo já obtido, copia assets de `node_modules` e o modelo
local para `apps/web/public/mediapipe/`, ignorado pelo Git. Não acessa a rede.
A página lê esses arquivos locais quando o detector é iniciado, sem CDN.
Não publicar essa pasta sem revisar termos/avisos de redistribuição.

## Usar

1. Escolha método e ROI; clique em Iniciar câmera e responda à permissão do navegador.
2. Confira enquadramento, regiões e cadência analisada. Espelhar só muda a exibição.
3. Aguarde ao menos 20 s de captura íntegra; confirmação/recuperação pode exigir mais.
   Sinal insuficiente, rosto ausente ou quadro inválido devem manter BPM ausente.
4. Inspecione janela, sinal, PSD e motivos. A estimativa resume uma janela passada;
   não representa frequência instantânea nem qualidade clínica calibrada.
5. Se desejar, exporte séries JSON antes de parar. A exportação inclui RGB/abstenções,
   timestamps, análises, parâmetros, versão do SDK e hash do modelo; não inclui imagens.
6. Stop desliga a câmera e descarta séries/worker. Voltar de outra aba ou página
   não reinicia automaticamente. Trocar câmera exige iniciar uma nova sessão.

O buffer é circular: no máximo 900 observações por ROI e 30 análises no export.
A contagem de callbacks não analisados não é uma medição de frames perdidos no sensor.
Processamento em milissegundos é observado por frame, não latência sensor→tela.
Se nenhum frame/resposta chegar por 3 s, a sessão é encerrada por watchdog.

## Módulos e regressões

- `features/live/session.ts`: captura, backpressure, recursos e descarte.
- `processor.worker.ts`: MediaPipe e agendamento científico fora da UI.
- `roi.ts` / `buffer.ts`: geometria, fotometria e armazenamento limitado.
- `dsp.ts` / `display.ts`: GREEN/POS/CHROM, qualidade, continuidade e exibição.
- `live-lab.tsx`: estados, preview/overlay, parâmetros e gráficos compartilhados.
- `generated-config.json`: fonte geradora Python; não editar manualmente.

```bash
uv run python scripts/export_live_reference.py --check
npm test
npx playwright install chromium
npm run test:e2e
```

Para regenerar referências após alteração deliberada da especificação:
`uv run python scripts/export_live_reference.py`, seguido de revisão do diff e testes.
Coeficientes são definidos para a grade 30 Hz; não reutilizar com outro fs.
As fixtures compartilhadas são artificiais e não simulam ground truth humano.
A tolerância Python/TS é de 1e-9 para os nove casos congelados; veja ADR 0011.

O E2E prepara câmera Y4M sem rosto em `artifacts/wave9-camera.y4m`, inicia serviços
locais nas portas 3000/8000 e usa exclusivamente dispositivos falsos do Chromium.
Rotas/assets são locais; teste monitora ausência de métodos de envio e chamadas à API.
Foco/visibilidade e desconexão também são exercitados por eventos simulados.
Não requer nem acessa webcam física. Peso local é requisito explícito do teste.

Não há validação em pessoas, precisão fisiológica demonstrada, inspeção positiva
em rosto autorizado ou garantia para todo navegador/codec/timeline. Não foi
implementado Benchmark Lab ou experimento da Onda 10.
