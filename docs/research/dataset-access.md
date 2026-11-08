# Datasets — estado de acesso em 2026-11-07

Nenhum dataset foi obtido; o usuário confirmou não possuir cópias autorizadas.
Não houve contato com terceiros, solicitação enviada ou download de vídeos/PPG.

## UBFC-rPPG

A página dos responsáveis disponibiliza vídeos para pesquisa e pede citação.
Isso não foi tratado como uma licença aberta genérica ou permissão de redistribuir.
Antes da avaliação, obter distribuição/termos completos e registrar a versão,
direitos de uso e evidências temporais da sessão concreta.
Fonte oficial: https://sites.google.com/view/ybenezeth/ubfcrppg.
Referência pedida: Bobbia et al., Unsupervised skin tissue segmentation for remote
photoplethysmography, Pattern Recognition Letters (2017).

Organização candidata conferida também no loader publicado do rPPG-Toolbox:
https://github.com/ubicomplab/rPPG-Toolbox/blob/b7500b848f84ad7f86e277b4612563b69f4f88f9/dataset/data_loader/UBFCrPPGLoader.py
Esse loader não foi copiado. O parser local exige três linhas (PPG, HR, segundos)
e deve ser conferido nos arquivos recebidos. Não presumir sincronização só pela
quantidade de amostras ou FPS nominal.

## PURE

A página oficial consultada solicita contato a partir de conta de instituição
acadêmica; contas pessoais e empresas não são atendidas segundo o aviso atual.
Uma eventual solicitação deverá ser feita pelo responsável elegível, com os termos
fornecidos pelos mantenedores. Não foi enviada solicitação nesta sessão.
Fonte oficial:
https://www.tu-ilmenau.de/universitaet/fakultaeten/fakultaet-informatik-und-automatisierung/profil/institute-und-fachgebiete/institut-fuer-technische-informatik-und-ingenieurinformatik/fachgebiet-neuroinformatik-und-kognitive-robotik/data-sets-code/pulse-rate-detection-dataset-pure

Parser FullPackage preparado a partir da organização publicada, ainda sem validar
o pacote real, imagens ou sincronização:
https://github.com/ubicomplab/rPPG-Toolbox/blob/b7500b848f84ad7f86e277b4612563b69f4f88f9/dataset/data_loader/PURELoader.py
Amostras Timestamp devem ser inteiros em nanossegundos; conversão para float64 em
segundos não preserva precisão de nanossegundos em épocas grandes.
Não reinterpretar timestamps por posição de linha nem FPS.

## Registro mínimo de acesso/alinhamento

Manter em data/ um registro com dataset/versão, origem oficial, termos recebidos,
responsável pelo acesso e permissão de uso/redistribuição. O manifesto guarda o
caminho; o lock exporta apenas o hash, sem copiar dados pessoais do registro.
Para alinhamento, registrar unidades, origens de vídeo/RGB/referência, offset,
como foi obtido e evidência. Zero segundos não é valor default comprovado.
Registrar também proveniência de qualquer RGB pré-computado.

Esses registros são evidências externas declaradas pelo pesquisador. O software
verifica existência/integridade, não autenticidade institucional, termos jurídicos
ou sincronização física automaticamente.
