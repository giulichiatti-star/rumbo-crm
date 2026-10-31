"""Publicar Rumbo en GitHub Pages, con verificación y vuelta atrás.

  python3 scripts/publicar.py              resumen: qué se publicaría (no toca nada)
  python3 scripts/publicar.py --preparar   corre TODAS las pruebas; si dan verde, deja la versión marcada como preparada
  python3 scripts/publicar.py --desplegar  publica (git push), espera a que el sitio sirva la versión nueva y la verifica
  python3 scripts/publicar.py --revertir   deshace el último commit con un commit nuevo (después hay que --desplegar)

Un push es una acción visible para el productor: lo hace quien corre --desplegar, después del «dale» de quien administra.
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SITIO = "https://giulichiatti-star.github.io/rumbo-crm/"
MARCA = RAIZ / ".git" / "rumbo_preparado"


def git(*a, check=True):
    r = subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} falló: {r.stderr.strip()}")
    return r.stdout.strip()


def version_local():
    return json.loads((RAIZ / "version.json").read_text())["v"]


def version_en_vivo():
    try:
        with urllib.request.urlopen(f"{SITIO}version.json?t={time.time()}", timeout=15) as r:
            return json.loads(r.read())["v"]
    except Exception:
        return None


def pendientes():
    return [l for l in git("log", "origin/main..HEAD", "--oneline", check=False).splitlines() if l]


def resumen():
    git("fetch", "-q", check=False)
    sucio = git("status", "--porcelain")
    pend = pendientes()
    print(f"Versión en vivo: {version_en_vivo() or '(no se pudo leer)'}")
    print(f"Versión local:   {version_local()}")
    print(f"Cambios sin guardar en un commit: {'SÍ' if sucio else 'no'}")
    if sucio:
        print(sucio)
    print(f"Commits para publicar: {len(pend)}")
    for l in pend:
        print("  -", l)
    if pend:
        print("Archivos que cambian:")
        print(git("diff", "--stat", "origin/main..HEAD"))
    preparado = MARCA.exists() and MARCA.read_text().strip() == git("rev-parse", "HEAD")
    print(f"Pruebas hechas para esta versión: {'SÍ' if preparado else 'no (correr --preparar)'}")
    print("Pruebas que corren: pantallas en 13 anchos, fechas, cálculos, aviso de versión, sincronización (~2 min).")


def preparar():
    if git("status", "--porcelain"):
        sys.exit("Hay cambios sin guardar en un commit: guardalos (commit) y volvé a correr --preparar.")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-B", str(RAIZ / "tests" / "correr_todo.py")], cwd=RAIZ)
    if r.returncode:
        MARCA.unlink(missing_ok=True)
        sys.exit("Las pruebas dieron ROJO: no se puede publicar. Arreglá la causa y repetí --preparar.")
    MARCA.write_text(git("rev-parse", "HEAD"))
    print(f"Pruebas en verde ({time.time() - t0:.0f} s). Versión {version_local()} lista para publicar.")


def desplegar():
    if git("status", "--porcelain"):
        sys.exit("Hay cambios sin guardar en un commit.")
    if not (MARCA.exists() and MARCA.read_text().strip() == git("rev-parse", "HEAD")):
        sys.exit("Esta versión no tiene las pruebas hechas: correr primero --preparar.")
    if not pendientes():
        sys.exit("No hay nada nuevo para publicar.")
    anterior, nueva, t0 = version_en_vivo(), version_local(), time.time()
    git("push", "-q", "origin", "main")
    print(f"Enviado. Esperando que el sitio sirva la versión {nueva}...")
    while time.time() - t0 < 300:
        if version_en_vivo() == nueva:
            html = urllib.request.urlopen(f"{SITIO}?t={time.time()}", timeout=15).read().decode("utf-8", "ignore")
            ok = f'name="app-version" content="{nueva}"' in html
            print(f"PUBLICADO en {time.time() - t0:.0f} s. Versión en vivo: {nueva} (antes: {anterior}). Página y version.json {'coinciden' if ok else 'NO coinciden: revisar'}.")
            print(f"Si algo salió mal: python3 scripts/publicar.py --revertir  y después  --desplegar.")
            return
        time.sleep(5)
    sys.exit("Pasaron 5 minutos y el sitio todavía no sirve la versión nueva. Revisar en GitHub > Actions.")


def revertir():
    if git("status", "--porcelain"):
        sys.exit("Hay cambios sin guardar en un commit.")
    ultimo = git("log", "-1", "--format=%h %s")
    git("revert", "--no-commit", "HEAD")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "estampar_version.py")], cwd=RAIZ, check=True)
    git("add", "-A")
    git("commit", "-q", "-m", f"Vuelta atrás: deshace «{ultimo}»\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>")
    MARCA.unlink(missing_ok=True)
    print(f"Se deshizo «{ultimo}» con un commit nuevo. Falta correr --preparar y --desplegar para que llegue al sitio.")


if __name__ == "__main__":
    {"--preparar": preparar, "--desplegar": desplegar, "--revertir": revertir}.get(sys.argv[1] if len(sys.argv) > 1 else "", resumen)()
