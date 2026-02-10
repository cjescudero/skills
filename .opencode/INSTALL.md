# Instalacion para OpenCode

## Requisitos

- OpenCode instalado
- Git

## Instalacion

1. Clona este repositorio:

```bash
git clone <URL_DE_TU_REPO> ~/.config/opencode/my-skills
```

2. Registra plugin y skills:

```bash
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/skills
rm -f ~/.config/opencode/plugins/my-skills.js
rm -rf ~/.config/opencode/skills/my-skills
ln -s ~/.config/opencode/my-skills/.opencode/plugins/my-skills.js ~/.config/opencode/plugins/my-skills.js
ln -s ~/.config/opencode/my-skills/skills ~/.config/opencode/skills/my-skills
```

3. Reinicia OpenCode.

## Verificacion

```bash
ls -l ~/.config/opencode/plugins/my-skills.js
ls -l ~/.config/opencode/skills/my-skills
```
