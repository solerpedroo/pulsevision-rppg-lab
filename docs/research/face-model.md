# Registro de modelo — Face Landmarker

Verificado em 2026-11-07. Artefato para uso local, não redistribuído neste repositório.

- Runtime: MediaPipe 1.2.2, CPU, detecção e landmarks; expressões desabilitadas.
- Bundle: face_landmarker/float16/1.
- URL: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
- SHA256: 64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff
- Origem oficial: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- Download: scripts/fetch_face_model.py, acionado explicitamente.
- Pesos: models/face_landmarker.task, ignorado pelo Git.

As model cards dos três componentes declaram Apache License 2.0:

- Detector: https://storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20%28Short%20Range%29.pdf
- Mesh: https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf
- Blendshape: https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf

A licença do código deste projeto não substitui a licença dos componentes.
Não derivar autorização do rodapé da documentação: a verificação acima usa os
cartões dos modelos. Em eventual redistribuição, preservar avisos e termos
aplicáveis. Não existe redistribuição dos pesos nesta entrega.
Uso experimental; não inferir identidade, emoções, demografia ou diagnóstico.
As limitações de posição, iluminação e oclusão declaradas nas cards continuam
aplicáveis. O teste local sem rosto confirma carregamento/execução, não robustez.

Onda 9: SDK JavaScript `@mediapipe/tasks-vision` 1.2.2 (Apache-2.0), pinado no lock.
Usa o mesmo bundle/hash em worker CPU. `npm run live:assets` copia runtime/WASM
pinados e modelo local verificado para public/mediapipe ignorado; não faz download
nem versiona/redistribui pesos. O browser verifica o hash novamente ao inicializar.
