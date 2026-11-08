# Verificação da Onda 9 — 2026-11-08

História: Start explícito → permissão → detector local em worker → frames com
mediaTime → máscaras/RGB → buffers/DSP → estimativa ou abstenção → export → Stop.

- Chromium com dispositivos falsos e câmera Y4M original de cor constante, sem rosto.
  Nenhuma webcam física foi acessada. SDK/WASM e modelo local reais foram usados.
- Após >20 s: rosto ausente, BPM ausente, janela e motivo preservados; export contém
  observações RGB null e análises com BPM null, sem imagens. Limites do buffer verificados.
- Stop: srcObject null, tracks realmente ended, export desabilitado e dados descartados.
- Permissão negada retorna erro compreensível; uma permissão simuladamente atrasada
  que chega após Stop libera seus tracks e não inicia captura/detector.
- Seleção de câmera, blur, visibilitychange e track-ended acionam descarte; eventos de
  foco/visibilidade/hardware são simulados no headless. Unmount por navegação verifica
  tracks encerradas; reload de sessão ativa retorna com câmera desligada.
- Rede durante captura: somente GET da origem local; nenhuma chamada /api, método de
  envio ou origem externa. Não há backend de webcam.
- Sinal/PSD: nove regressões de GREEN/POS/CHROM em dados RGB artificiais, comparando
  arrays, timestamps e BPM com Python, tolerância 1e-9. Não é validação fisiológica.
- Geometria positiva/fotometria/movimento usam landmarks e pixels artificiais, com
  RGB/canais e rejeições testados. Máscaras de browser não são declaradas idênticas ao OpenCV.
- DisplayGuard bloqueia falha atual sem reescrever janela histórica; freshness tem
  deadline independente de novos frames. Cadência trata quantização sem fabricar tempos.
- UI desktop/mobile revisada em screenshots locais; teclado/labels/controles seguem
  componentes existentes. Nenhum overflow horizontal no viewport 390×844.

Foi isolada uma falha anterior da API: stack dump do worker mostrou import de
sounddevice/PortAudio, acionado indiretamente por MediaPipe, bloqueado em Pa_Initialize.
O worker exclusivamente visual agora trata esse módulo opcional como indisponível.
Regressão injeta módulo-armadilha: job real deve concluir sem importá-lo. Não há
patch no pacote instalado nem no processo HTTP. Diagnóstico temporário foi removido.

Validação final: Ruff, mypy (64 fontes), 225 pytest, ESLint, TypeScript, 25 Vitest,
7 Playwright, build, formatação e diff passaram. CI configurada, sem execução remota.
Screenshots/exports/fixtures de câmera/runtime e stacks de diagnóstico estão em
arquivos locais ignorados, sem pesos ou imagens pessoais versionados.

Permanecem sem validação: câmeras físicas/condições variadas, detecção positiva em
rosto autorizado, precisão fisiológica, equivalência de todo o pipeline e outros
browsers/dispositivos. Não há conclusão clínica ou avaliação real de dataset.
