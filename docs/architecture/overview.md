# Arquitetura

PulseVision estima experimentalmente frequência cardíaca por variações RGB em pele
facial. Seu resultado central é uma estimativa rastreável ou abstenção explicada.

## Limites dos módulos

O núcleo Python independente de HTTP será a referência científica. A aquisição
preserva PTS; ROIs produzem amostras RGB; métodos produzem sinal; qualidade decide
se uma janela permite estimativa. Não há algoritmo implementado na Onda 0.
A API futura orquestra jobs de arquivos voluntariamente enviados. O navegador
executará câmera, ROIs e DSP localmente em worker. Nenhum frame ao vivo deve sair
do cliente por padrão. Equivalência Python/TS exige fixtures e tolerâncias numéricas.

## Sequência de desenvolvimento

0: fundação e protocolo; 1: ingestão temporal; 2: face/ROI/RGB; 3: GREEN/DSP;
4: CHROM/POS; 5: qualidade; 6: benchmark; 7: API; 8 e seguintes: produto e live.
Consulte o plano original para os critérios completos de cada onda.

## Contratos

Pydantic é a fonte de verdade. scripts/export_schemas.py exporta JSON Schema;
npm run contracts gera declarações TypeScript. Validações relacionais (como
fim maior que início e status compatível com BPM) existem em Python e não são
expressas por tipos TS nem por todo JSON Schema. Consumidores futuros devem
validá-las explicitamente. Timestamps são segundos relativos à origem da sessão;
produced_at_s usa a mesma origem. RGB está na escala 0–255; motion_score ainda
não possui escala calibrada. Status good representa elegibilidade instrumental,
nunca confiança clínica. Invariantes novos exigem versão e testes de contrato.

## Stack validada

Python 3.12 via uv e Node 24 via npm. Next.js 16 usa lint separado do build.
Tailwind 4 e configuração shadcn estão preparados; componentes serão adicionados
quando necessários na onda de UI. Não há dependência de GPU, vídeo ou MediaPipe
antes da onda correspondente.
Referências: https://nextjs.org/docs/app/getting-started/installation e
https://ui.shadcn.com/docs/installation/manual.
