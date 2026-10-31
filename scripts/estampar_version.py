"""Estampa una versión nueva: escribe el mismo identificador en index.html (meta app-version) y en version.json.
La app compara esos dos valores para avisar «hay una versión nueva» (skill aviso-version-nueva, receta B).
Lo corre solo el hook de git antes de cada commit que toca index.html. A mano: python3 scripts/estampar_version.py"""
import datetime
import json
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
v = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
idx = RAIZ / "index.html"
html = idx.read_text(encoding="utf-8")
nuevo, n = re.subn(r'(<meta name="app-version" content=")[^"]*(">)', rf"\g<1>{v}\g<2>", html)
assert n == 1, "No encontré la etiqueta <meta name=\"app-version\"> en index.html"
idx.write_text(nuevo, encoding="utf-8")
(RAIZ / "version.json").write_text(json.dumps({"v": v}) + "\n", encoding="utf-8")
print("versión estampada:", v)
