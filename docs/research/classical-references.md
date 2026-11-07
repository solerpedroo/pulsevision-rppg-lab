# Referências e rastreabilidade — métodos clássicos

Consultadas em 2026-11-07.

## Publicações

CHROM: de Haan e Jeanne (2013), Robust pulse rate from chrominance-based rPPG.
https://pubmed.ncbi.nlm.nih.gov/23744659/
DOI: 10.1109/TBME.2013.2266196.

POS: Wang, den Brinker, Stuijk e de Haan (2017), Algorithmic Principles of Remote PPG.
https://pubmed.ncbi.nlm.nih.gov/28113245/
DOI: 10.1109/TBME.2016.2609282.

## Implementações consultadas

pyVHR CPU CHROM e POS:
https://github.com/phuselab/pyVHR/blob/a6270f04a97f05a13d145dd0a5e8c8df48d8bd62/pyVHR/BVP/methods.py
Licença upstream GPLv3. Não redistribuímos esse arquivo nem o adicionamos ao runtime.
O script de regeneração consulta a origem explicitamente; os testes normais não
acessam rede nem executam código externo. A fixture contém números sintéticos,
proveniência e versões; não contém rostos, dados de participantes ou código upstream.

rPPG-Toolbox consultado para convenções e diferenças de integração:
https://github.com/ubicomplab/rPPG-Toolbox/tree/b7500b848f84ad7f86e277b4612563b69f4f88f9/unsupervised_methods/methods
A licença própria do Toolbox é Responsible AI Source Code License v1.1.
Não é dependência do projeto nem fonte de código incorporado. O runtime local
implementa as equações matemáticas e o contrato documentado no ADR 0006.

## Reprodução da comparação numérica

```bash
uv run python scripts/generate_method_references.py
uv run pytest tests/test_methods.py
```

A regeneração é opt-in, requer internet e executa duas funções do arquivo
upstream fixado por commit. O script registra SHA256 de origem e ambiente.
Revisar alterações da fixture ao atualizar referência ou dependências; não aceitar
novo golden apenas para fazer um teste passar.

Entrada: 600 amostras RGB artificiais, 30 Hz, 90 BPM conhecidos, seed 42 e
ruído gaussiano 0,03. Banda 0,7–3 Hz, Butterworth ordem 4, janela interna 48 samples.
GREEN compara detrend via ajuste linear independente. CHROM compara projeção
pyVHR com pré-processamento/composição explicitamente alinhados. POS compara
cpu_POS sem pós-filtro, no interior [48:552].
Desvios máximos observados no interior: CHROM ~5,3e-15 e POS ~6,5e-15.
Tolerância automatizada: atol=1e-11 e rtol=1e-9; pico após DSP coincidente
dentro de 1e-9 BPM nessa fixture. Não representa acurácia fisiológica.

Limites: uma fixture não cobre todos os sinais possíveis. Há testes adicionais
de frequências, degenerescência, rejeições e suporte temporal. Comparar métodos
em pessoas exige dataset autorizado e referência sincronizada da Onda 6.
