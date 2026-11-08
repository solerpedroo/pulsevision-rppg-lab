# ADR 0008 — Benchmark, referência e bloqueio de avaliações não verificáveis

Status: aceito · 2026-11-07 · PV-0601–PV-0612
Estado científico: infraestrutura testada; avaliação em dataset real pendente.

## Contexto

O usuário confirmou que não possui dataset autorizado. Não há UBFC/PURE local.
A Onda 6 precisa preparar avaliação reproduzível sem fabricar experimentos em pessoas.

## Decisão

Pacote benchmarks instalado no workspace Python e CLI freeze/run. Manifesto
estrito declara dataset/versão, registro de acesso, split por participante,
sessões, origem da referência, offset e evidência de alinhamento.
Para dados reais, access_confirmed deve ser true e referir um registro externo.
RGB pré-computado de dados reais exige trace_provenance. Essas são declarações
auditáveis do responsável, não validações jurídicas ou confirmação automática do sensor.

Split é uma partição explícita: participante não pode aparecer em dois conjuntos,
nem a mesma sessão ser duplicada. O runner seleciona somente o split pedido.
Não otimizar parâmetros por resultado de teste. Sintéticos não podem usar split test.

## Congelamento

Lock contém SHA256 do manifesto, entradas, referências, evidências e pesos,
snapshot do código Python científico/benchmark + pyproject/uv.lock, commit e versões.
Verificar todos os hashes antes de qualquer execução. Código/dados/parâmetros/
ambiente alterados invalidam o lock. Dirty status é informação registrada;
criar um lock/relatório não deve alterar a identidade do código.
É um congelamento técnico verificável, não pré-registro independente: um responsável
poderia criar outro lock; alterações após avaliação final exigem nova versão e justificativa.
O estado dirty pode ser usado em desenvolvimento, mas deve ser explicitado.

## Adapters e referência

UBFC: descobrir subject*/vid.avi e ground_truth.txt; parser estrito de três linhas
PPG, HR do oxímetro e timestamps em segundos. Formato testado em fixtures próprias,
ainda não conferido em sessão real obtida dos responsáveis.
PURE: parser de /FullPackage, Timestamp inteiro em nanossegundos, Value.waveform
e Value.pulseRate. Preparação de referência somente; sequências PNG PURE e seu
mapeamento temporal não foram validados/convertidos para vídeo nesta entrega.
CSV normalizado de referência aceita timestamp_s/hr_bpm explícitos.

Transformação declarada: tempo_no_RGB = tempo_referência − reference_origin_s + offset_s.
Nunca reiniciar cada sinal em zero independentemente ou escolher offset pelo menor erro.
O CSV da extração usa zero no primeiro frame decodificado; a evidência deve considerar
essa origem. Sem verificação externa registrada, excluir a sessão e não calcular erro.

HR de referência: média ponderada pelo tempo da HR fornecida pelo sensor,
zero-order hold dentro do mesmo intervalo útil espectral [início,fim). Exigir duas amostras,
valores finitos/positivos, bordas cobertas e gaps <=0,2 s por padrão.
Extensão nas bordas é limitada a esse gap; não inferir referência além dele.
Não derivar uma referência artificial do próprio estimador rPPG.
PPG é preservado e verificado quanto a valores inválidos; não há extração de
batimentos/spectrum de referência nesta versão. HR do aparelho pode ser suavizada/defasada.

## Elegibilidade e falhas

Janela curta, referência ausente/inválida ou gap de referência são exclusões prévias;
não são abstenções do estimador. Janelas completas com referência válida são elegíveis.
Todas as abstenções instrumentais/recuperação continuam no denominador elegível.
Sessão sem comparação completa é registrada separadamente; não inventar seu número
de janelas nem misturar métricas parciais de apenas um método. Participantes sem
pares permanecem no relatório, com métricas/coverage indisponíveis conforme o caso.

Vídeo local pode passar por VideoReader→Face Landmarker→RGBExtractor no runner.
CSV derivado intermediário é temporário e removido; fonte original não é copiada.
RGB pré-computado é uma alternativa com hash/proveniência.
Não guardar rostos, ground truth ou dados restritos no Git.

## Métricas e agregação

Erros em pares aceitos: MAE, RMSE, MedAE e bias (estimado − referência).
Pearson por participante somente quando N>=2 e ambas séries têm variância.
LoA descritivos: bias ±1,96*std(error,ddof=1), indisponíveis quando N<2.
Resumo principal é média de cada métrica por participante com pares válidos,
peso igual entre participantes. Macro-RMSE é média dos RMSEs individuais;
macro-MedAE é média das medianas individuais, não mediana global de todas as janelas.
Coverage global de janelas e média de coverage por participante são mostradas juntas.
Participantes sem pares são listados; erros são condicionais às janelas aceitas.

Bootstrap percentil de participantes, seed declarada, 1000 reamostragens padrão,
somente com >=3 participantes com pares; abaixo disso CI é null com motivo.
Três participantes ainda podem produzir CI instável: não chamar o critério
computacional de garantia estatística. Não reamostrar janelas como independentes.
Concordância de médias por participante é separada dos LoA descritivos por janela.
Gráfico Bland–Altman com janelas repetidas tem ressalva explícita; não implementa
modelo hierárquico de LoA nem inferência clínica.

## Rastreabilidade, custo e limites

Relatórios JSON/CSV/Markdown e PNGs por método incluem exclusões, motivos,
parâmetros efetivos, hashes e versões. Custos reais de IO/aquisição e DSP separados;
acquisition_reference_io_s é custo compartilhado da sessão, repetido por método
por conveniência, não somar como se a extração tivesse sido refeita três vezes.
dsp_seconds_per_input_minute é tempo computacional, não tempo até primeiro BPM.
Fonte de hardware pode ficar indisponível; não inventar CPU ou medidas.

Sem datasets reais, PV-0610 científico e inspeção de formato/licença em arquivos
reais permanecem pendentes. A demonstração artificial é teste de infraestrutura.

O intervalo de referência é o interior espectral comum após corte de bordas,
derivado somente dos timestamps e da configuração, independentemente da aceitação
do método. reference_start_s/reference_end_s são exportados separadamente da
janela nominal de análise. Isso evita comparar média do sensor em 20 s contra
um espectro calculado em um interior menor. Em falha de temporização, usar o
interior nominal pré-declarado e preservar a abstenção; não otimizar o intervalo
para obter erro menor. Regra idêntica para os três métodos.
