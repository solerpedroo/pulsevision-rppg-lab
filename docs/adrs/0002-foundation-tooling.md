# ADR 0002 — Fundação e contratos

Status: aceito · 2026-11-07 · PV-0001/PV-0002/PV-0003/PV-0007/PV-0009

## Contexto

Repositório inicial contém apenas README e plano. Python do sistema é 3.14.

## Decisão

Usar Python 3.12 isolado, uv.lock, npm workspaces, package-lock.json e Node 24.
Contratos Pydantic geram JSON Schema e TS. Não adicionar bibliotecas de inferência
antes de necessárias. Licenciar código próprio sob MIT; dados e modelos mantêm
seus termos originais. AGENTS.md centraliza orientação para todas as ferramentas.

## Consequências

Setup não altera Python do sistema. Atualizações de dependências passam por CI.
Schemas não carregam invariantes relacionais; validação de execução continua necessária.
