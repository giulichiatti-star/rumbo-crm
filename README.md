# Rumbo

CRM para asesores y productores de recría y engorde, basado en el modelo Excel *Modelo_Recria_Engorde_V4_3*.
Es un solo archivo (`index.html`), sin instalación.

## Cómo funcionan los datos

- **Sin configurar nada**: cada navegador guarda sus datos en el propio aparato. No se sincronizan entre celular y computadora.
- **Con Supabase** (recomendado para la prueba): los datos quedan en una base propia, con correo y contraseña. Lo que se carga en un aparato aparece en el otro.

## Activar la sincronización (10 minutos)

1. Crear una cuenta gratis en https://supabase.com y un proyecto nuevo.
2. En el proyecto: **SQL Editor** → pegar el contenido de `supabase_setup.sql` → **Run**.
3. Para la prueba, en **Authentication → Providers → Email** desactivar *Confirm email* (así no hace falta confirmar por correo).
4. En **Project Settings → API** copiar la **Project URL** y la clave **anon public**.
5. Pegarlas en `index.html`, en la línea `const SUPA={url:'',key:''};`.
6. Subir el cambio. En 1 o 2 minutos el sitio pide correo y contraseña.

La clave *anon* es pública por diseño. Los datos de cada persona quedan protegidos por las reglas del paso 2: cada cuenta solo ve lo suyo.

## Qué datos trae

Lotes, precios de mercado, costos, dietas y curvas vienen del Excel. Los precios están marcados "verificar" en el original: revisarlos antes de usarlos con clientes.

## Para quien mantiene el proyecto

**Pruebas** (necesitan Python 3 y Playwright): `python3 tests/correr_todo.py` corre cuatro pruebas: pantallas que cuadran en 13 anchos, fechas aaaa/mm/dd, 113 comprobaciones de cálculo y el aviso de versión nueva. Tarda ~1,5 minutos y tiene que dar todo en verde antes de publicar.

**Aviso de «hay una versión nueva».** Cada versión publicada lleva un identificador, escrito igual en `index.html` (etiqueta `app-version`) y en `version.json`. Quien tiene la app abierta ve un aviso fijo con el botón *Actualizar* cuando el sitio ya tiene una versión más nueva. La página nunca se recarga sola (no se pierde lo que se está cargando) y actualizar no cierra la sesión. El identificador se estampa solo en cada commit que cambia `index.html`, con un hook de git. Instalarlo una vez en cada copia del repositorio:

    cp scripts/hook_pre_commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
