# =============================================================================
#  parte1_rsi_simple.py  —  ARCHIVO MAESTRO
#  RSI(7)  |  Banda 40/60  |  S&P 500
# =============================================================================
#
#  Este es el archivo que ejecutas con F5 en Spyder.
#  No contiene ninguna función — solo llama a las que están
#  en los archivos fn_*.py, igual que un archivo LaTeX maestro
#  que llama a \input{capitulo1}, \input{capitulo2}, etc.
#
#  ESTRUCTURA DE ARCHIVOS (todos deben estar en la misma carpeta):
#
#    RSI Modular/
#        ├── fn_descargar.py       → función descargar_datos
#        ├── fn_calcular_rsi.py    → función calcular_rsi
#        ├── fn_senales.py         → función detectar_senales
#        ├── fn_rendimientos.py    → función calcular_rendimientos_futuros
#        ├── fn_tabla.py           → función tabla_estadisticas
#        ├── fn_grafica.py         → función graficar_rsi
#        │
#        └── parte1_rsi_simple.py  ← ESTÁS AQUÍ (archivo maestro)
#
#  PARA CAMBIAR EL ANÁLISIS:
#    Solo modifica los parámetros en la SECCIÓN DE PARÁMETROS más abajo.
#    No necesitas tocar ningún archivo fn_*.
#
# =============================================================================

# ── Importaciones — un archivo por función ────────────────────────────────────
#
# Cada línea trae UNA función desde SU archivo.
# Si en el futuro mejoras la función calcular_rsi, solo editas
# fn_calcular_rsi.py y este archivo automáticamente usa la versión nueva.

from fn_descargar     import descargar_datos
from fn_calcular_rsi  import calcular_rsi
from fn_senales       import detectar_senales
from fn_rendimientos  import calcular_rendimientos_futuros
from fn_tabla         import tabla_estadisticas
from fn_grafica       import graficar_rsi


# ── SECCIÓN DE PARÁMETROS ─────────────────────────────────────────────────────
#
# Aquí está TODO lo que puedes cambiar libremente.
# El resto del script se adapta solo.

TICKER      = "^GSPC"              # activo a analizar
AÑOS        = 2                    # ventana de tiempo en años
PERIODO_RSI = 7                    # período del RSI
SOBREVENTA  = 40                   # umbral inferior de la banda
SOBRECOMPRA = 60                   # umbral superior de la banda
DIAS_FUTURO = [1, 3, 5, 10, 30, 60, 90]   # horizontes de rendimiento


# ── PASO 1: Descargar datos ───────────────────────────────────────────────────
print("=" * 55)
print(f"  RSI({PERIODO_RSI})  |  Banda {SOBREVENTA}/{SOBRECOMPRA}  |  {TICKER}")
print("=" * 55 + "\n")

df = descargar_datos(TICKER, años=AÑOS)


# ── PASO 2: Calcular RSI ──────────────────────────────────────────────────────
rsi = calcular_rsi(df["Close"], PERIODO_RSI)

print(f"Últimos 5 valores del RSI({PERIODO_RSI}):")
print(rsi.tail())
print()


# ── PASO 3: Detectar señales ──────────────────────────────────────────────────
senales = detectar_senales(rsi, SOBREVENTA, SOBRECOMPRA)

n_buy  = (senales ==  1).sum()
n_sell = (senales == -1).sum()
print(f"Señales detectadas → BUY: {n_buy}  |  SELL: {n_sell}\n")


# ── PASO 4: Calcular rendimientos futuros ─────────────────────────────────────
df_rend = calcular_rendimientos_futuros(df["Close"], senales, DIAS_FUTURO)

print("Primeras señales con sus rendimientos futuros:")
print(df_rend.head(8).to_string(index=False))
print()


# ── PASO 5: Tabla estadística ─────────────────────────────────────────────────
print("=" * 55)
print("  TABLA ESTADÍSTICA")
print("=" * 55)

tbl = tabla_estadisticas(df_rend, DIAS_FUTURO)

if tbl.empty:
    print("⚠️  Sin señales suficientes.")
else:
    cols_media   = [c for c in tbl.columns if "Media"   in c]
    cols_winrate = [c for c in tbl.columns if "WinRate" in c]

    print("\n▸ Retorno promedio (%) — positivo = operación ganadora en promedio")
    print(tbl[["N"] + cols_media].to_string())

    print("\n▸ Win Rate (%) — porcentaje de operaciones ganadoras")
    print(tbl[cols_winrate].to_string())

print()


# ── PASO 6: Gráfica ───────────────────────────────────────────────────────────
print("📊 Generando gráfica...")
graficar_rsi(df, rsi, senales,
             periodo=PERIODO_RSI,
             sobreventa=SOBREVENTA,
             sobrecompra=SOBRECOMPRA,
             guardar=True)

print("\n✅ Análisis completado.")
