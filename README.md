# My Skills Repository

Repositorio personal para gestionar y mantener skills.

## Objetivo

Este repositorio permite:
- mantener skills versionadas en Git,
- usarlas en Codex con descubrimiento nativo,
- usarlas en OpenCode con plugin + skills nativas,
- trabajar con comandos, hooks, documentacion y tests.

## Estructura

- `skills/`: tus skills reales (`<nombre>/SKILL.md`)
- `skills/_templates/`: recursos para definir nuevas skills
- `.codex/INSTALL.md`: instalacion rapida en Codex
- `.opencode/INSTALL.md`: instalacion rapida en OpenCode
- `.opencode/plugins/`: plugin de OpenCode
- `.claude-plugin/`: metadatos de plugin para Claude Code
- `commands/`: comandos de conveniencia
- `hooks/`: hook de inicio de sesion
- `docs/`: documentacion tecnica
- `tests/`: tests de activacion y workflows

## Primeros pasos

1. Crea una skill nueva en `skills/<nombre>/SKILL.md`.
2. Ajusta `.claude-plugin/plugin.json` y `.claude-plugin/marketplace.json` con tu nombre/proyecto.
3. Sigue `.codex/INSTALL.md` para activar skills en Codex.
4. Sigue `.opencode/INSTALL.md` para activar plugin y skills en OpenCode.

## Notas

- Este repositorio contiene tus skills y utilidades asociadas.

## Skills actuales

- `bus-arrivals-coruna-data`: consultas de llegadas de buses de A Coruna por API de iTranvias.
