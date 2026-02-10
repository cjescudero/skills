# Instalacion para Codex

## Requisitos

- Git
- Codex CLI

## Instalacion

1. Clona este repositorio:

```bash
git clone <URL_DE_TU_REPO> ~/.codex/my-skills
```

2. Crea el symlink para descubrimiento nativo de skills:

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/my-skills/skills ~/.agents/skills/my-skills
```

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\my-skills" "$env:USERPROFILE\.codex\my-skills\skills"
```

3. Reinicia Codex.

## Verificacion

```bash
ls -la ~/.agents/skills/my-skills
```

Debe apuntar a `~/.codex/my-skills/skills`.
