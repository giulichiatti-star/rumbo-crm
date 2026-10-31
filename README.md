# Rumbo

CRM para asesores y productores de recría y engorde, basado en el modelo Excel *Modelo_Recria_Engorde_V4_3*.
Es un solo archivo (`index.html`), sin instalación.

## Cómo funcionan los datos

- **Sin configurar nada**: cada navegador guarda sus datos en el propio aparato. No se sincronizan entre celular y computadora.
- **Con Supabase** (recomendado para la prueba): los datos quedan en una base propia, con correo y contraseña. Lo que se carga en un aparato aparece en el otro.

## Cómo se cuidan los datos

- Cada cuenta tiene sus datos en Supabase (tabla `rumbo_state`). Nadie más puede leerlos: lo garantizan las reglas de la base, no la app.
- La app guarda solo cuando los datos cambian, y solo si el servidor sigue como lo dejó ese aparato. Si dos aparatos cambiaron a la vez, pregunta cuál conservar y guarda el otro como copia.
- Una copia por día y otra en cada choque o restauración (tabla `rumbo_backups`, quedan las últimas 14). Desde *Mi cuenta y datos* se puede descargar, cargar o restaurar una copia.
- Los comentarios de quien prueba llegan a la tabla `rumbo_feedback` (Supabase > Table Editor). Traen la pantalla, la versión y el ancho de pantalla.
- Un aviso automático (`.github/workflows/mantener-activo.yml`) pide un dato cada 3 días para que Supabase gratis no pause el proyecto. Si igual se pausa, se reactiva con un botón en el panel de Supabase y no se pierde nada.

## Publicar un cambio

    python3 scripts/publicar.py              # resumen: qué se publicaría
    python3 scripts/publicar.py --preparar   # corre todas las pruebas (~2 min)
    python3 scripts/publicar.py --desplegar  # publica, espera y verifica la versión en vivo
    python3 scripts/publicar.py --revertir   # deshace el último commit (después, --desplegar)

La guía para quien prueba se regenera con `python3 docs/generar_guia.py`.

## Activar la sincronización (10 minutos)

1. Crear una cuenta gratis en https://supabase.com y un proyecto nuevo.
2. En el proyecto: **SQL Editor** → pegar el contenido de `supabase_setup.sql` → **Run** (crea las tres tablas con sus reglas).
3. Para la prueba, en **Authentication → Providers → Email** desactivar *Confirm email* (así no hace falta confirmar por correo).
4. En **Project Settings → API** copiar la **Project URL** y la clave **anon public**.
5. Pegarlas en `index.html`, en la línea `const SUPA={url:'',key:''};`.
6. Subir el cambio. En 1 o 2 minutos el sitio pide correo y contraseña.

La clave *anon* es pública por diseño. Los datos de cada persona quedan protegidos por las reglas del paso 2: cada cuenta solo ve lo suyo.

## Qué datos trae

Lotes, precios de mercado, costos, dietas y curvas vienen del Excel. Los precios están marcados "verificar" en el original: revisarlos antes de usarlos con clientes.

## Para quien mantiene el proyecto

**Pruebas** (necesitan Python 3 y Playwright): `python3 tests/correr_todo.py` corre cinco pruebas: pantallas que cuadran en 13 anchos, fechas dd/mm/aaaa, 113 comprobaciones de cálculo, el aviso de versión nueva y la sincronización con copias y comentarios. Tarda unos 2 minutos y tiene que dar todo en verde antes de publicar.

**Aviso de «hay una versión nueva».** Cada versión publicada lleva un identificador, escrito igual en `index.html` (etiqueta `app-version`) y en `version.json`. Quien tiene la app abierta ve un aviso fijo con el botón *Actualizar* cuando el sitio ya tiene una versión más nueva. La página nunca se recarga sola (no se pierde lo que se está cargando) y actualizar no cierra la sesión. El identificador se estampa solo en cada commit que cambia `index.html`, con un hook de git. Instalarlo una vez en cada copia del repositorio:

    cp scripts/hook_pre_commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
