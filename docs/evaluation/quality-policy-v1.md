# Política experimental de qualidade v1

Status: heurística inicial, sem calibração em dados reais.
Configuração: configs/quality/quality-v1.json; DSP: SignalConfig.

Registrar config, método, ROI e código com cada execução. Ajustes futuros só em
desenvolvimento/validação; congelar antes de testar em participantes reservados.
Não escolher gates pelo menor erro no teste final.

## O que reportar

Total de janelas agendadas, aceitas, abstenções e cobertura; distribuição de status
e motivos, incluindo warming_up/recuperação. Mostrar múltiplas causas por janela
sem somá-las como se fossem contagens de janelas independentes.
Motivos descritivos (no_face, excessive_motion, saturated_roi etc.) não indicam
diagnósticos de saúde. Métricas instrumentais não são probabilidade de BPM correto.

O helper summarize_quality é reutilizável pelo runner futuro. O runner da Onda 6
ainda precisará definir elegibilidade do dataset, exclusões prévias e alinhamento
de referência. Nenhuma métrica de acurácia é calculada sem essa referência.

## Trade-offs conhecidos

- Uma única amostra inválida bloqueia toda a janela: cobertura pode cair bastante.
- Confirmação consecutiva demora e pode suprimir mudanças reais de frequência.
- Janela de análise sobreposta não constitui uma observação independente.
- Energia do G antes do filtro pode rejeitar dados recuperáveis por CHROM/POS.
- Média RGB não revela distribuição completa de brilho/saturação dos pixels.
- Ausência de indicadores faciais não é evidência de que a aquisição era adequada.
- Periodicidade de luz/movimento pode sobreviver aos gates e gerar BPM plausível.

A Onda 6 deverá medir erro e cobertura juntos em dados autorizados.
Não alegar robustez geral com base apenas nos testes sintéticos.
