# Verificação Onda 7 — API/jobs locais

História verificada: cliente HTTP envia arquivo escolhido → FastAPI → fila/
subprocesso → pipeline offline → derivados consultáveis/exportáveis → exclusão.
Não há integração de UI nesta onda; browser/Video Lab serão verificados na Onda 8.

## Evidência HTTP real

Uvicorn iniciou em 127.0.0.1:8765 com storage próprio de smoke, modelo local,
vídeo artificial 128×128, 50 frames/2 s, cor constante e sem rosto.
Cliente urllib enviou vídeo/mp4 com método CHROM. POST retornou 202 e o job
terminou completed. Durante o job, health retornou 200 em uma amostra de 1,77 ms.
Isso é smoke funcional, não p50/p95 ou benchmark.

Resultados paginados retornaram BPM null. Downloads JSON, CSV e PNG retornaram 200. O original input.bin não existia após conclusão. DELETE retornou 204 e
consulta subsequente 404. Servidor recebeu SIGTERM e concluiu shutdown.
Nenhuma medição em pessoa ou precisão fisiológica foi alegada.

## Automação

25 testes de API cobrem fluxo real com modelo/subprocesso, concorrência, slots,
MIME/tamanho real de stream, desconexão, timeout de upload e processamento,
limites de vídeo/memória, cancelamento e SIGSTOP, restart, expiração/exclusão,
host/origin/API key, CORS e rate limit. Testes científicos anteriores preservados.
Total local: 223 testes Python e 2 web, lint, tipos, formatação e build passaram.

Storage do smoke em artifacts/wave7-smoke, ignorado pelo Git; job e seus
derivados foram apagados explicitamente. Vídeo de entrada artificial foi gerado
para o teste. Não houve envio a serviço remoto ou execução de CI no GitHub.

## Limites da evidência

Integrações com modelo são opcionais em pytest offline quando pesos faltam;
o workflow CI agora inclui fetch explícito/versionado/verificado do modelo.
O fluxo positivo testa execução e abstenção em vídeo sem face. Não valida
geometria/qualidade em rosto real nem substitui o benchmark autorizado da Onda 6.
