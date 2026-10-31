"""Corre las tres pruebas, una tras otra, y dice cuánto tardó cada una.
Uso: python3 tests/correr_todo.py   (sale con 1 si alguna falla)"""
import pathlib
import subprocess
import sys
import time

AQUI = pathlib.Path(__file__).resolve().parent
PRUEBAS = [("Pantallas que cuadran", "pantallas_cuadran_test.py"), ("Fechas aaaa/mm/dd", "fechas_test.py"), ("Cálculos", "calculos_test.py"), ("Aviso de versión nueva", "version_test.py")]
rojo = []
for nombre, archivo in PRUEBAS:
    t0 = time.time()
    r = subprocess.run([sys.executable, "-B", str(AQUI / archivo)], capture_output=True, text=True)
    seg = time.time() - t0
    ult = (r.stdout.strip().splitlines() or ["(sin salida)"])[-1]
    print(f"{'OK  ' if r.returncode == 0 else 'FALLA'} {nombre} ({seg:.0f} s): {ult}")
    if r.returncode:
        rojo.append(nombre)
        print(r.stdout[-1500:], r.stderr[-500:])
sys.exit(1 if rojo else 0)
