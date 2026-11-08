# Privacidade e retenção — política v2 (Onda 7)

A API local aceita vídeos enviados explicitamente. A página Next.js atual ainda
não solicita câmera nem envia arquivos; interface de vídeo pertence à Onda 8.

## Webcam

Não há captura/streaming de webcam nesta API. O futuro modo live continuará no
navegador por padrão, sem gravação ou envio de frames. Iniciar/parar/exportar
dependem de ação explícita. Nenhum comportamento de câmera é ativado pela API.

## Uploads e destino

Cliente deve mostrar destino, retenção e aviso experimental antes do envio.
GET /api/v1/policy fornece essas informações; acesso padrão é loopback.
O upload binário copia o arquivo para o backend local configurado. Não processa
a câmera automaticamente. Nome original é ignorado e não é armazenado nos jobs.

## Retenção e exclusão

Arquivos ficam em diretório UUID privado por job; fila e processamento têm limites.
Original removido ao concluir, falhar, cancelar, atingir limite ou timeout.
CSV intermediário de extração também é removido. Somente derivados são acessíveis
por endpoints explícitos: estimativas, séries RGB/rPPG/PSD, CSV/JSON/PNG e hashes.
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
