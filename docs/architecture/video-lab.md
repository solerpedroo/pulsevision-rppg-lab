# Video Lab — Onda 8

## Executar

Da raiz, após `uv sync --locked` e `npm ci`, em dois terminais:

```bash
uv run python scripts/fetch_face_model.py
uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

```bash
npm run dev -w apps/web
```

Abra http://localhost:3000/video. A API deve estar no mesmo computador que o
navegador. Não há dependência de servidor remoto, fonte externa ou câmera.
A interface permite alterar a origem local e informar a chave, se configurada
na API; a chave não fica em URL, arquivo ou armazenamento persistente do cliente.

## Fluxo

1. Confira conexão, destino e limites; escolha um vídeo próprio/autorizado.
2. Confira o preview local, método e ROI. Vídeo não é enviado nessa seleção.
3. Marque a autorização e clique em Iniciar análise.
4. Acompanhe fila/progresso; cancele ou exclua quando necessário.
5. Inspecione janela, motivos, cobertura, RGB, rPPG, PSD e BPM quando disponível.
   A timeline e o scrubber controlam o vídeo. Regiões detectadas aparecem no frame;
   sem geometria válida, não há contorno. Contorno não significa sinal aceito.
6. Alterar método/ROI não muda resultados existentes. Reanalisar exclui o job
   anterior e envia o arquivo novamente com a configuração escolhida.
7. Exporte CSV, JSON ou PNG explicitamente; exclua a sessão ao terminar.
   Excluir também descarta a seleção local, revoga o preview e desmarca a autorização.

BPM ausente é resultado legítimo, inclusive em vídeo curto ou sem rosto. Não há
interpolação durante rejeições nem indicadores clínicos. Os eixos de amplitude
são unidades arbitrárias; RGB está na escala 0–255. Qualidade e cobertura não
medem erro contra referência. A validação em pessoas continua pendente.

Limites visíveis vêm de `/policy`; FPS, assinatura, corrupção e codecs também
são verificados no worker. Um codec pode funcionar apenas em um dos decoders.
O endpoint de vídeo original não existe; o preview continua usando o arquivo
local escolhido, e o servidor descarta o original no estado terminal.

## Implementação e verificação

- `features/video/api.ts`: contratos de transporte, validação, paginação e lookup temporal.
- `video-lab.tsx`: sessão, configuração, polling, cancelamento/exclusão e exportação.
- `video-preview.tsx`: sincronização do overlay com frames apresentados.
- `signal-charts.tsx` e `chart.tsx`: sinais/estimativas com lacunas e unidades.
- `e2e/video.spec.ts`: navegador, API e worker real; adversidades simuladas identificadas.

```bash
npm test
npx playwright install chromium
npm run test:e2e
```

O E2E inicia e encerra seus servidores nas portas 3000/8000, que precisam estar
livres. Requer o modelo local já obtido e verificado; não baixa pesos ou datasets
automaticamente. Gera vídeo H.264 sem rosto em `artifacts/wave8-fixture.mp4`;
storage, downloads, screenshots e traces também ficam em `artifacts/`, fora do Git.
Não são medidas de pessoas. A CI foi configurada para executar os mesmos testes.

Veja ADR 0010, [API](video-api.md) e [privacidade](../privacy/policy.md).
