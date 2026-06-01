# =============================================================================
#  parte1_rsi_simple.py  —  ARCHIVO MAESTRO
#  RSI  |  Análisis multimercado  |  América Latina + S&P 500
# =============================================================================
#
#  Este es el único archivo que ejecutas (F5 en Spyder).
#  No contiene funciones propias — solo ORQUESTA las funciones
#  definidas en los archivos fn_*.py.
#
#  ANALOGÍA: es como un archivo LaTeX maestro que usa \input{capitulo1},
#  \input{capitulo2}, etc. Cada fn_*.py es un "capítulo".
#
#  ESTRUCTURA DE ARCHIVOS (todos en la misma carpeta):
#    ├── fn_descargar.py       → descarga datos de Yahoo Finance / Alpha Vantage
#    ├── fn_calcular_rsi.py    → calcula el RSI y su media móvil
#    ├── fn_senales.py         → detecta señales BUY/SELL por cruce de bandas
#    ├── fn_rendimientos.py    → mide el retorno futuro tras cada señal
#    ├── fn_sharpe.py          → calcula el Sharpe Ratio de las señales
#    ├── fn_benchmark.py       → calcula el Buy & Hold de referencia
#    ├── fn_tabla.py           → genera y exporta las tablas de resultados
#    ├── fn_grafica.py         → genera y guarda las figuras
#    └── parte1_rsi_simple.py  ← ESTÁS AQUÍ
#
#  PARA CAMBIAR EL ANÁLISIS:
#    Solo modifica los valores en la SECCIÓN DE PARÁMETROS más abajo.
#    No necesitas tocar ningún fn_*.py.
#
# =============================================================================

# ── Importaciones ─────────────────────────────────────────────────────────────
# Cada línea importa UNA función desde SU archivo.
# Si en el futuro mejoras fn_calcular_rsi.py, este archivo usa la versión nueva
# automáticamente la próxima vez que lo ejecutes.

from fn_descargar     import descargar_datos
from fn_calcular_rsi  import calcular_rsi, calcular_ma_rsi
from fn_senales       import detectar_senales
from fn_rendimientos  import calcular_rendimientos_futuros
#from fn_tabla import tabla_estadisticas, tabla_comparativa_maestra, tabla_ranking_efectividad
from fn_tabla         import tabla_estadisticas, tabla_comparativa_maestra
from fn_sharpe        import calcular_sharpe
from fn_benchmark     import calcular_benchmark, imprimir_benchmark
from fn_grafica       import graficar_rsi, graficar_heatmap, graficar_retorno_horizonte

import itertools   # para generar combinaciones: itertools.product(PERIODOS, BANDAS)
import pandas as pd


# =============================================================================
#  SECCIÓN DE PARÁMETROS — AQUÍ ESTÁ TODO LO QUE PUEDES CAMBIAR
# =============================================================================

TICKERS = [
    "^GSPC",  # S&P 500 — USA (índice de referencia global)
    "^BVSP",  # Bovespa — Brasil
    "^MXX",   # IPC — México
    "^MERV",  # Merval — Argentina
    "^IPSA",  # IPSA — Chile (puede fallar; no disponible en Yahoo Finance)
    "GXG",    # ETF iShares MSCI Colombia (proxy del COLCAP)
    "EPU",    # ETF iShares MSCI Peru
    "ILF",    # ETF iShares Latin America 40 (canasta regional)
]

AÑOS        = 5      # ventana de tiempo en años (cambia aquí para más o menos historia)
                     # IMPORTANTE: con menos de 3 años hay pocas señales y
                     # los resultados no son estadísticamente confiables

PERIODOS    = [7, 14, 20, 30, 45]        # períodos del RSI a analizar
                                          # RSI(7)  → muy sensible, muchas señales
                                          # RSI(45) → muy lento, pocas señales

BANDAS      = [(20, 80), (30, 70), (10, 90)]
# Cada tupla es (sobreventa, sobrecompra):
#   (30, 70) → banda estándar de Wilder (la más usada en la literatura)
#   (20, 80) → banda más conservadora (menos señales, más extremas)
#   (10, 90) → banda muy extrema (muy pocas señales)

DIAS_FUTURO = [1, 3, 5, 10, 30, 60, 90]
# Horizontes temporales para medir el retorno DESPUÉS de cada señal
# Ej: ret_30d = retorno del precio 30 días después de la señal BUY/SELL

INTERVALO   = "1d"   # "1d" = datos diarios (recomendado)
                     # "1wk" = semanal, "1mo" = mensual (menos precisión)

# Parámetros de la Media Móvil del RSI (solo para visualización en gráficas)
VENTANA_MA  = 5        # ventana de la MA del RSI (días)
TIPO_MA     = "simple" # "simple" o "exponencial"


# =============================================================================
#  DICCIONARIOS GLOBALES — acumulan resultados de TODOS los mercados
# =============================================================================

# resultados_globales[ticker][periodo][banda_str] = {rsi, senales, tabla_rendimientos}
# Ejemplo de acceso: resultados_globales["^GSPC"][7]["30/70"]["tabla_rendimientos"]
resultados_globales = {}

# benchmarks[ticker] = {retorno_total_%, retorno_anual_%, volatilidad_%, sharpe}
# Se usa al final para la tabla comparativa de todos los mercados
benchmarks = {}


# =============================================================================
#  BUCLE PRINCIPAL — un mercado a la vez
# =============================================================================

for TICKER in TICKERS:

    print("\n" + "#" * 60)
    print(f"  MERCADO: {TICKER}")
    print("#" * 60)

    try:
        # ── PASO 1: Descargar datos ───────────────────────────────────────────
        # descargar_datos intenta Yahoo Finance primero, luego Alpha Vantage
        # Si ambas fallan, lanza una excepción y el except de abajo la captura
        df = descargar_datos(TICKER, años=AÑOS, intervalo=INTERVALO)
        # df es un DataFrame con columnas: Open, High, Low, Close, Volume
        # El índice es DatetimeIndex (fechas de trading)

        # ── PASO 2: Benchmark Buy & Hold ─────────────────────────────────────
        # El benchmark responde: ¿cuánto ganaría alguien que simplemente
        # compra el índice al inicio y lo mantiene hasta el final?
        # Es la referencia mínima que debe superar la estrategia RSI.
        bnh = calcular_benchmark(df)
        imprimir_benchmark(bnh, ticker=TICKER)

        # Guardar el benchmark de ESTE mercado en el diccionario global
        # IMPORTANTE: se guarda AQUÍ, antes del bucle de combinaciones,
        # para que esté disponible en el resumen final aunque algo falle después
        benchmarks[TICKER] = bnh

        # ── PASO 3: Inicializar acumuladores para este mercado ────────────────
        resultados = {}          # se llena en el bucle de combinaciones
        graficas_pendientes = [] # acumula datos para hacer UNA figura al final

        # ── PASO 4: Bucle sobre todas las combinaciones periodo × banda ───────
        # itertools.product genera el producto cartesiano:
        # PERIODOS=[7,14] × BANDAS=[(30,70),(20,80)] → 4 combinaciones:
        #   (7, (30,70)), (7, (20,80)), (14, (30,70)), (14, (20,80))
        for PERIODO_RSI, (SOBREVENTA, SOBRECOMPRA) in itertools.product(PERIODOS, BANDAS):

            # PASO 4a: Calcular RSI y su media móvil
            # rsi: pd.Series con valores entre 0 y 100
            # ma_rsi: media móvil del RSI (solo para graficar)
            rsi    = calcular_rsi(df["Close"], PERIODO_RSI)
            ma_rsi = calcular_ma_rsi(rsi, ventana=VENTANA_MA, tipo=TIPO_MA)

            # PASO 4b: Detectar señales de compra y venta
            # senales: pd.Series con valores +1 (BUY), -1 (SELL), 0 (nada)
            # BUY  → cuando el RSI SALE de la zona de sobreventa (cruza hacia arriba)
            # SELL → cuando el RSI SALE de la zona de sobrecompra (cruza hacia abajo)
            senales = detectar_senales(rsi, SOBREVENTA, SOBRECOMPRA)
            n_buy   = (senales ==  1).sum()   # contar señales de compra
            n_sell  = (senales == -1).sum()   # contar señales de venta

            # Advertir si hay pocas señales (resultado no confiable estadísticamente)
            # Se usa "or" para advertir si CUALQUIERA de los dos tipos es insuficiente
            if n_buy < 5 or n_sell < 5:
                print(f"  ⚠️  RSI({PERIODO_RSI}) banda {SOBREVENTA}/{SOBRECOMPRA} "
                      f"— menos de 5 señales, resultado NO confiable")

            # PASO 4c: Calcular rendimientos futuros tras cada señal
            # df_rend: DataFrame con columnas [date, signal, ret_1d, ret_3d, ..., ret_90d]
            # Cada fila corresponde a UNA señal detectada
            df_rend = calcular_rendimientos_futuros(df["Close"], senales, DIAS_FUTURO)

            # PASO 4d: Guardar en el diccionario de resultados
            # Inicializar el nivel de periodo si no existe
            if PERIODO_RSI not in resultados:
                resultados[PERIODO_RSI] = {}

            # La clave de banda es un string: "30/70", "20/80", etc.
            clave_banda = f"{SOBREVENTA}/{SOBRECOMPRA}"
            resultados[PERIODO_RSI][clave_banda] = {
                "rsi":                rsi,      # valores del RSI (para graficar)
                "senales":            senales,  # señales detectadas (para graficar)
                "tabla_rendimientos": df_rend,  # retornos futuros (para tablas)
            }

            # PASO 4e: Acumular para la figura conjunta
            # En lugar de generar UNA gráfica por combinación (que serían muchas),
            # acumulamos todas las combinaciones y generamos UNA figura al final
            graficas_pendientes.append(
                (rsi, senales, ma_rsi, PERIODO_RSI, SOBREVENTA, SOBRECOMPRA)
            )

        # ── PASO 5: Guardar resultados de este mercado ANTES de las salidas ──
        # IMPORTANTE: se guarda AQUÍ, antes de generar tablas y gráficas,
        # para que quede en resultados_globales aunque algo falle en las salidas
        resultados_globales[TICKER] = resultados

        # ── PASO 6: Generar salidas por mercado (tablas y gráficas) ──────────

        # Tabla comparativa maestra: 3 tablas en consola + Excel + CSV + LaTeX
        print("\n  Generando tabla comparativa maestra...")
        tabla_comparativa_maestra(resultados, PERIODOS, BANDAS, DIAS_FUTURO, ticker=TICKER)

        # Heatmap de Win Rate: mapa de calor verde/rojo por combinación
        print("\n  Generando heatmap...")
        graficar_heatmap(resultados, PERIODOS, BANDAS, DIAS_FUTURO, horizonte=30, ticker=TICKER)

        # Gráfico de retorno por horizonte: ¿mejora manteniéndola más días?
        print("\n  Generando gráfico de horizonte temporal...")
        graficar_retorno_horizonte(resultados, PERIODOS, BANDAS, DIAS_FUTURO, ticker=TICKER)

        # Figura conjunta RSI: todos los subplots en UNA sola imagen
        print("\n  Generando figura conjunta de señales RSI...")
        graficar_rsi(df, graficas_pendientes, guardar=True, ticker=TICKER)

    except Exception as e:
        # Si algo falla (descarga, cálculo, etc.), imprimimos el error
        # y continuamos con el siguiente mercado en lugar de detener todo
        print(f"  Error con {TICKER}: {e}")
        continue   # saltar al siguiente TICKER


# =============================================================================
#  RESUMEN GLOBAL — comparación entre todos los mercados
# =============================================================================

print("\n" + "=" * 70)
print("  RESUMEN GLOBAL — TOP combinaciones por retorno a 30 días")
print("=" * 70)

# Construir una tabla plana con todas las combinaciones de todos los mercados
# para identificar cuáles funcionaron mejor y cuáles peor
frames = []   # lista de diccionarios, uno por combinación

for ticker_g, res_g in resultados_globales.items():
    for periodo_g in res_g:
        for banda_g, datos_g in res_g[periodo_g].items():
            tbl_g = datos_g["tabla_rendimientos"]

            if tbl_g.empty or "signal" not in tbl_g.columns:
                continue

            for tipo_g in ["BUY", "SELL"]:
                sub_g = tbl_g[tbl_g["signal"] == tipo_g]

                # Solo incluir combinaciones con al menos 3 señales
                if sub_g.empty or len(sub_g) < 3:
                    continue

                r30 = sub_g["ret_30d"].dropna()
                if len(r30) == 0:
                    continue

                frames.append({
                    "Mercado":  ticker_g,
                    "RSI":      periodo_g,
                    "Banda":    banda_g,
                    "Señal":    tipo_g,
                    "N":        len(sub_g),
                    "Ret_30d%": round(r30.mean(), 2),
                    "WR_30d%":  round((r30 > 0).mean() * 100, 1),
                })

if frames:
    # Ordenar de mayor a menor retorno a 30 días
    df_global = pd.DataFrame(frames).sort_values("Ret_30d%", ascending=False)
    print("\n  TOP 10 combinaciones ganadoras (mínimo 3 señales):")
    print(df_global.head(10).to_string(index=False))
    print("\n  TOP 10 combinaciones perdedoras:")
    print(df_global.tail(10).to_string(index=False))
else:
    print("\n  Sin resultados suficientes para el resumen global.")

# ── Tabla de Benchmarks — todos los mercados ──────────────────────────────────
# Esta tabla reemplaza el bloque antiguo que solo mostraba el último mercado
print("\n" + "=" * 60)
print("  ANÁLISIS COMPLETADO")
print("=" * 60)

if benchmarks:
    print("\n  BENCHMARK BUY & HOLD — todos los mercados")
    print("-" * 57)
    print(f"  {'Mercado':<10} {'Ret.Total%':>10} {'Ret.Anual%':>10} "
          f"{'Volat%':>8} {'Sharpe':>8}")
    print("-" * 57)
    for tkr, b in benchmarks.items():
        print(f"  {tkr:<10} {b['retorno_total_%']:>10} {b['retorno_anual_%']:>10} "
              f"{b['volatilidad_%']:>8} {b['sharpe']:>8}")
    print("-" * 57)

print("\n✅ Todas las combinaciones completadas.")