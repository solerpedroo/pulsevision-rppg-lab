# ADR 0001 — Processamento híbrido

Status: aceito · 2026-11-07 · PV-0005

## Contexto

A webcam requer minimização de imagens transmitidas. Experimentos offline exigem
ferramentas científicas e rastreabilidade temporal.

## Decisão

Webcam e DSP live no navegador; arquivos voluntários na API Python local;
núcleo científico Python sem HTTP. Implementações TS seguirão especificação
numérica comum com testes de equivalência. Filtros causais e offline serão distintos.

## Consequências

Há duas implementações a manter. Fixtures compartilhadas e documentação de
latência/bordas são obrigatórias antes de alegar equivalência.
