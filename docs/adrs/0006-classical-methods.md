# ADR 0006 — CHROM, POS e comparação controlada

Status: aceito · 2026-11-07 · PV-0401–PV-0408

## Contexto

GREEN e os contratos temporais da Onda 3 já estão testados. Projeções de cor
precisam de normalização local, tratamento de degenerescência e suporte temporal.
Frequência sintética recuperada não demonstra precisão em fisiologia real.

## Decisão e configuração

Métodos registrados em METHOD_REGISTRY, configuração imutável classical-v1:
janela interna 1,6 s e epsilon 1e-9. Parâmetros em configs/methods/classical-v1.json;
MethodConfig valida versão e valores. A CLI aceita --method-config.
O engine compartilhado está em estimation/pipeline.py; green_pipeline permanece
como import compatível. Interfaces retornam MethodSignal com sinal, máscara de
suporte, posição do filtro e margem conservadora de borda. Não preencher
degenerescências com zeros ou dividir por desvios quase nulos.

## CHROM

Normalizar canais pela média de cada janela interna. Projeções:
X=3R−2G; Y=1,5R+G−1,5B.
Filtrar X e Y usando Butterworth SOS/banda/ordem da SignalConfig, antes de
alpha=std(Xf)/std(Yf). Combinar Xf−alpha*Yf, Hann simétrico e overlap-add 50%.
Comprimento = ceil(1,6*fs), arredondado para par; hop=metade.
Sem renormalização pela soma de pesos, seguindo a convenção de composição
Hann. Não filtrar novamente o resultado final.
A documentação e implementação de referência do Toolbox motivaram a composição;
seus defaults de ordem 3 e banda 0,7–2,5 Hz diferem do padrão local ordem 4/0,7–3 Hz.
Não chamar resultados com parâmetros diferentes de equivalentes.

## POS

Normalização temporal por média+epsilon. Projeções:
S1=G−B; S2=−2R+G+B.
h=S1+std(S1)/(std(S2)+epsilon)*S2; remover média de h e overlap-add com passo 1.
Janela ceil(1,6*fs), sem divisão pela contagem de sobreposições.
Só a área com todas as sobreposições é marcada como plenamente válida.
O filtro comum opera após composição, como em GREEN, e é offline não causal.

## Comparação justa e bordas

Entrada RGB, ROI, máscara válida, timestamps, agendamento, banda, ordem e Welch
são os mesmos. Respeitar que CHROM filtra componentes e POS/GREEN filtram saída:
essa diferença é parte do método, não equivalência de toda operação de DSP.
A CLI --method all usa margem comum >= janela interna + dois intervalos,
limitando esse incremento ao max_gap_s aceito, para cobrir ceil/paridade.
O teste verifica igualdade exata dos timestamps úteis e das janelas reportadas.
Em análise individual, margem é max(edge_trim_s, margem do método); portanto,
não comparar resultados individuais sem controlar esse detalhe.
Amplitudes entre métodos têm escalas distintas e não medem qualidade diretamente.

## Referência e regressão

Fixar pyVHR no commit a6270f04a97f05a13d145dd0a5e8c8df48d8bd62.
Script explícito executa somente cpu_CHROM/cpu_POS extraídos do arquivo oficial,
sem instalar dependências GPU. Nenhum código upstream é incorporado ao runtime.
CI usa fixture numérica sintética offline com URL, commit, hash e versões.

CHROM: referência na projeção, com normalização, filtro e Hann/OLA controlados
pelo harness; não é equivalência do pipeline completo pyVHR.
POS: pyVHR usa floor(1,6*fs) e omite a primeira janela. Local inclui a primeira e
usa ceil; comparar a 30 Hz (comprimento 48), excluindo 48 amostras de cada borda.
Epsilon coincide. Diferenças de arredondamento em FPS não inteiro permanecem
documentadas, sem alegar identidade.
GREEN: golden independente com normalização e detrend via ajuste linear.
Testar waveform interno atol=1e-11/rtol=1e-9 e pico de referência sob o mesmo DSP.
Referência numérica não avalia taxa de erro em pessoas nem substitui benchmark.

## Consequências

CPU suficiente; nenhuma biblioteca de treinamento adicionada. Variantes são
offline e versões futuras causais precisam de contrato/teste próprio. Qualidade
completa, estabilidade entre janelas e validação com ground truth ficam nas
Ondas 5–6. Licenças/fontes e limites em docs/research/classical-references.md.
