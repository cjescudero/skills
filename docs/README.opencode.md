# Uso con OpenCode

OpenCode puede usar:
- skills nativas desde `~/.config/opencode/skills/`,
- plugins desde `~/.config/opencode/plugins/`.

Este repo aporta ambos:
- plugin: `.opencode/plugins/my-skills.js`
- skills: `skills/`

El plugin carga automaticamente todas las skills disponibles en `skills/*/SKILL.md` (excluyendo `_templates`).
