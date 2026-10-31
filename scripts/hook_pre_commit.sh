#!/bin/sh
# Antes de cada commit que cambia index.html, estampa la versión nueva (para el aviso «hay una versión nueva»).
# Instalar una vez en cada copia del repositorio:  cp scripts/hook_pre_commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
if git diff --cached --name-only | grep -qx 'index.html'; then
  python3 scripts/estampar_version.py && git add index.html version.json
fi
