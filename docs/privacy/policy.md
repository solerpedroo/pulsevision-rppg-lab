# Privacidade e retenção — política v1

Onda 0: não há captura, upload, telemetria, persistência de sessões ou inferência.
A página inicial não solicita câmera nem apresenta resultados simulados.

## Requisitos para as ondas futuras

Webcam: iniciar e parar apenas por ação explícita, encerrar tracks ao sair;
processamento local, sem gravação, envio de frames ou logs de imagens por padrão.
Exportação de derivados somente por ação explícita.
Uploads: antes do envio mostrar destino e retenção. Padrão planejado: backend
local, diretório isolado por job, descarte do original ao concluir/falhar/cancelar;
limite de retenção de 24 h para sobras após interrupções, verificado na inicialização
e periodicamente. Resultados derivados expiram em 24 h, salvo exportação explícita.
Exclusão deverá remover original e derivados e revogar acesso ao job. Esses
mecanismos serão implementados e testados na Onda 7, não estão ativos nesta base.
Logs não conterão frames, RGB bruto, nomes originais ou caminhos pessoais.

Dados de terceiros exigem consentimento/autorização e licença compatível.
Não inferir identidade ou atributos sensíveis. Uso experimental; não é dispositivo
médico. Nenhuma autorização ética ou validação clínica é alegada.
