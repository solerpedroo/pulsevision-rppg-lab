# Privacidade e retenção — política v4 (Onda 9)

O Video Lab abre preview local por object URL. Selecionar arquivo não o envia.
Após autorização marcada e clique explícito, a UI envia o vídeo à API local
indicada, exibindo destino e retenção. Essa rota não solicita câmera. Chave da API e arquivo
escolhido ficam em memória da aba, sem localStorage ou serviços de terceiros.

## Webcam

`/live` inicia getUserMedia somente após clique e permissão do navegador, sem áudio.
Detector, máscaras, RGB e DSP executam no navegador, em worker. Frames não são
enviados à API nem gravados. Assets do detector/modelo são lidos da mesma origem
local após preparação explícita; não há CDN, analytics ou backend de webcam.

Stop, saída da página, perda de foco/visibilidade, troca de câmera, desconexão,
erro ou timeout liberam tracks, encerram worker e descartam séries em memória.
Permissão que chega após cancelamento também tem seus tracks liberados. Retorno
de foco/refresh não reinicia captura. Buffer é limitado a 900 observações por ROI;
no máximo 30 análises são retidas para exportação na aba. Não há localStorage.

Somente ação explícita exporta JSON de derivados: RGB, motivos, timestamps,
análises e parâmetros/hash do modelo, sem imagens. Derivados ainda são dados
sensíveis de pesquisa; downloads pertencem ao usuário e não são retraídos por Stop.
Sem captura em contexto seguro/recursos compatíveis, a UI informa indisponibilidade.

## Uploads e destino

Cliente deve mostrar destino, retenção e aviso experimental antes do envio.
GET /api/v1/policy fornece essas informações; acesso padrão é loopback.
O upload binário copia o arquivo para o backend local configurado. Não processa
a câmera automaticamente. Nome original é ignorado e não é armazenado nos jobs.

## Retenção e exclusão

Arquivos ficam em diretório UUID privado por job; fila e processamento têm limites.
Original removido ao concluir, falhar, cancelar, atingir limite ou timeout.
CSV intermediário de extração também é removido. Somente derivados são acessíveis
por endpoints explícitos: estimativas, séries RGB/rPPG/PSD, contornos geométricos temporais de ROI, CSV/JSON/PNG e hashes.
Contornos são derivados faciais sujeitos à mesma retenção e exclusão; não há
frames de preview no servidor. Object URLs locais são revogados ao descartar
o arquivo ou desmontar a interface. Fechar a aba não cancela job já aceito.
Derivados expiram 24 h após término. Limpeza ocorre periodicamente e na inicialização;
consulta de job vencido revoga acesso. Serviço desligado não tem timer independente:
sobras de crash são limpas na próxima inicialização. Não prometer apagamento forense.
Metadados mínimos de tombstone expired permanecem por mais um período de retenção.
DELETE remove job e arquivos e torna consultas futuras 404. Não desfaz downloads
ou cópias que o próprio usuário já realizou.

## Acesso e limites

Storage não é exposto como diretório web. Respostas usam no-store/nosniff.
Origem/host restritos; acesso não local exige chave. O serviço é para um operador,
sem contas/autorização por pessoa. Não expor como serviço público sem controles
de implantação adequados. Logs da aplicação não registram frames, RGB bruto,
nome original ou mensagens de decoder com caminhos; worker retorna códigos sanitizados.
A quota é por arquivo/job/fila, não global de disco.

Dados de terceiros exigem consentimento/autorização e licença compatível.
Não inferir identidade ou atributos sensíveis. Uso experimental; não é dispositivo
médico. Nenhuma validação clínica ou autorização ética é alegada.
A ausência de dataset autorizado/validação real da Onda 6 permanece registrada.
