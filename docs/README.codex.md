# Uso con Codex

Codex detecta skills desde `~/.agents/skills/` al iniciar.

Este repo se conecta creando un symlink:

`~/.agents/skills/my-skills -> ~/.codex/my-skills/skills`

Si anades una skill nueva, reinicia Codex para garantizar descubrimiento limpio.

Skill incluida en este repo:
- `bus-arrivals-coruna-data`
