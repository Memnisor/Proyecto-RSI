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
#from fn_descargar_alpha import descargar_datos_alpha    # para Alpha Vantage
from fn_calcular_rsi  import calcular_rsi, calcular_ma_rsi
from fn_senales       import detectar_senales
from fn_rendimientos  import calcular_rendimientos_futuros
from fn_tabla         import tabla_estadisticas, tabla_comparativa_maestra
from fn_sharpe        import calcular_sharpe
from fn_benchmark     import calcular_benchmark, imprimir_benchmark
from fn_grafica       import graficar_rsi, graficar_heatmap,graficar_retorno_horizonte

import itertools

# ── SECCIÓN DE PARÁMETROS ─────────────────────────────────────────────────────
#
# Aquí está TODO lo que puedes cambiar libremente.
# El resto del script se adapta solo.

#TICKER      = "^GSPC", 
#TICKERS     = ["^GSPC", "^MXX", "^BVSP", "^COLCAP", "^IPSA", "^MERV"]
#TICKERS = ["^GSPC"]#, "^BVSP", "^MXX", "^IPSA", "^COLCAP", "^MERV", "^IGBVL", "^IBC", "^ECUINDEX", "^BVMBG", "^IACR"]            # activo a analizar
TICKERS = [
    "^GSPC",  # S&P 500 — USA (índice directo, funciona)
    "^BVSP",  # Bovespa — Brasil (funciona)
    "^MXX",   # IPC — México (funciona)
    "^MERV",  # Merval — Argentina (funciona)
    "^IPSA",  # IPSA — Chile (funciona)
    "GXG",    # ETF Colombia (replica COLCAP)
    "EPU",    # ETF Perú
    "ILF",    # ETF América Latina (canasta regional)
]
AÑOS        = 2                    # ventana de tiempo en años
PERIODOS = [7, 14, 20, 30, 45 ]                    # período del RSI
#SOBREVENTA  = 30                   # umbral inferior de la banda
#SOBRECOMPRA = 70                   # umbral superior de la banda
BANDAS = [(20, 80), (30, 70), (10, 90)]
DIAS_FUTURO = [1, 3, 5, 10, 30, 60, 90]   # horizontes de rendimiento
INTERVALO = "1d" 

# Parámetros para la Media Móvil del RSI
# La MA suaviza el RSI para visualizar mejor su tendencia
VENTANA_MA  = 5          # cuántos días de ventana tiene la MA del RSI
TIPO_MA     = "simple"   # "simple" o "exponencial"


# Diccionario maestro que guarda resultados DE TODOS los mercados
# resultados_globales["^BVSP"][7]["30/70"] = {...}
resultados_globales = {}

for TICKER in TICKERS:

    print("\n" + "#" * 60)
    print(f"  MERCADO: {TICKER}")
    print("#" * 60)
    
    
    # ── PASO 1: Descargar datos ───────────────────────────────────────────────────
    try:
        df = descargar_datos(TICKER, años=AÑOS, intervalo=INTERVALO)
        # ── PASO 2: Benchmark Buy & Hold ─────────────────────────────────────────────
        # Calculamos el Buy & Hold ANTES del bucle porque es independiente
        # del período RSI o la banda. Solo depende del activo y el período.
        # Sirve como referencia para saber si nuestra estrategia vale la pena.
        bnh = calcular_benchmark(df)
        imprimir_benchmark(bnh, ticker=TICKER)

        # ── PASO 3: Bucle sobre todas las combinaciones ───────────────────────────────
        # itertools.product genera todas las combinaciones posibles entre dos listas.
        # Ejemplo: PERIODOS=[7,14] y BANDAS=[(40,60),(30,70)] genera:
        #   (7,  40, 60)
        #   (7,  30, 70)
        #   (14, 40, 60)
        #   (14, 30, 70)
            
        # El bucle genera las 4 combinaciones: (7,40,60) (7,30,70) (14,40,60) (14,30,70)
        resultados = {}
        for PERIODO_RSI, (SOBREVENTA, SOBRECOMPRA) in itertools.product(PERIODOS, BANDAS):
                
            print("\n" + "=" * 60)
            print(f"  RSI({PERIODO_RSI})  |  Banda {SOBREVENTA}/{SOBRECOMPRA}  |  {TICKER}")
            print("=" * 60 + "\n")
                
            # PASO 4: Calcular RSI y su media movil
            rsi = calcular_rsi(df["Close"], PERIODO_RSI)
            ma_rsi = calcular_ma_rsi(rsi, ventana=VENTANA_MA, tipo=TIPO_MA)
            """
            print(f"Últimos 5 valores del RSI({PERIODO_RSI}):")
            print(rsi.tail())
            print(f"\nÚltimos 5 valores de la MA({VENTANA_MA}) del RSI:")
            print(ma_rsi.tail())
            print()
            """

            # PASO 5: Detectar señales
            senales = detectar_senales(rsi, SOBREVENTA, SOBRECOMPRA)
            n_buy  = (senales ==  1).sum()
            n_sell = (senales == -1).sum()
            #print(f"Señales detectadas → BUY: {n_buy}  |  SELL: {n_sell}\n")
            if n_buy < 5 and n_sell < 5:
                print("  ⚠️  Menos de 5 señales — resultado NO estadísticamente confiable")
            
            # PASO 6: Calcular rendimientos futuros
            df_rend = calcular_rendimientos_futuros(df["Close"], senales, DIAS_FUTURO)
            # Guardamos esta combinación en el diccionario maestro
            # Si el período no existe todavía, creamos su entrada vacía
            if PERIODO_RSI not in resultados:
                resultados[PERIODO_RSI] = {}

            # La clave de banda es "40/60" o "30/70" etc.
            clave_banda = f"{SOBREVENTA}/{SOBRECOMPRA}"
    
            # Guardamos los 3 elementos que necesitan el heatmap y la tabla maestra
            resultados[PERIODO_RSI][clave_banda] = {
                "rsi":                rsi,
                "senales":            senales,
                "tabla_rendimientos": df_rend,
                }
            """
            print("Primeras señales con sus rendimientos futuros:")
            print(df_rend.head(8).to_string(index=False))
            print()
            """
            print(f"  Señales → BUY: {n_buy}  SELL: {n_sell}  "
                  f"| RSI actual: {rsi.iloc[-1]:.1f}")
    
            # PASO 7: Calcular Sharpe Ratio
            # Comparamos el Sharpe de nuestras señales contra el Buy & Hold.
            # Si nuestro Sharpe < Sharpe del BnH, la estrategia no agrega valor.
            print(f"\n{'─' * 60}")
            print(f" TABLA 2: Sharpe Ratio y Volatilidad")
            print(f"  Benchmark BnH → Sharpe: {bnh['sharpe']}  |  Retorno anual: {bnh['retorno_anual_%']}%")
            print("─" * 60)
 
            tbl_sharpe = calcular_sharpe(df_rend, DIAS_FUTURO)
            if tbl_sharpe.empty:
                print("  Sin datos suficientes para Sharpe.")
            else:
                cols_sharpe  = [c for c in tbl_sharpe.columns if "Sharpe"  in c]
                cols_volatil = [c for c in tbl_sharpe.columns if "Volatil" in c]
                print("\n  Sharpe Ratio (anualizado) — mayor es mejor, referencia BnH: " + str(bnh['sharpe']))
                print(tbl_sharpe[["N"] + cols_sharpe].to_string())
                print("\n  Volatilidad (%) — menor es mejor")
                print(tbl_sharpe[cols_volatil].to_string())
                print()
            # PASO 8: Tabla estadística
            print("=" * 60)
            print("  TABLA 1: Retorno promedio y Win Rate")
            print("=" * 55)
            tbl = tabla_estadisticas(df_rend, DIAS_FUTURO)
            if tbl.empty:
                print("⚠️  Sin señales suficientes.")
            else:
                cols_media   = [c for c in tbl.columns if "Media"   in c]
                cols_winrate = [c for c in tbl.columns if "WinRate" in c]
                print("\n  Retorno promedio (%) — positivo = operacion ganadora")
                print(tbl[["N"] + cols_media].to_string())
                print("\n  Win Rate (%) — porcentaje de operaciones ganadoras")
                print(tbl[cols_winrate].to_string())
                print()
            # PASO 9: Gráfica
            print(f"📊 Generando gráfica RSI({PERIODO_RSI}) banda {SOBREVENTA}/{SOBRECOMPRA}...")
            graficar_rsi(df, rsi, senales,
                         periodo=PERIODO_RSI,
                         sobreventa=SOBREVENTA,
                         sobrecompra=SOBRECOMPRA,
                         guardar=True,
                         ma_rsi=ma_rsi,
                         ticker=TICKER
                         )
    except Exception as e:                    # ← 4 espacios
        print(f"  Error con {TICKER}: {e}")   # ← 8 espacios
        continue 
    
    # Guardar resultados de este ticker en el diccionario global
    resultados_globales[TICKER] = resultados
    
    # ── PASO 5: Tabla comparativa maestra ────────────────────────────────────────
    # Reúne TODOS los resultados del bucle en una sola tabla ordenada.
    # Necesita el diccionario "resultados" que se fue llenando en el bucle.
    print("\n  Generando tabla comparativa maestra...")
    tabla_comparativa_maestra(resultados, PERIODOS, BANDAS, DIAS_FUTURO, ticker=TICKER)
    
    # ── PASO 6: Heatmap de Win Rate ───────────────────────────────────────────────
    # Mapa de calor visual: verde=bueno, rojo=malo, amarillo=neutro
    # horizonte=30 → muestra el Win Rate a 30 días
    print("\n  Generando heatmap...")
    graficar_heatmap(resultados, PERIODOS, BANDAS, DIAS_FUTURO, horizonte=30, ticker=TICKER)
    
    
    # ── PASO 7: Gráfico de retorno por horizonte ──────────────────────────────────
    # Muestra si la estrategia mejora manteniéndola más días
    print("\n  Generando grafico de horizonte temporal...")
    graficar_retorno_horizonte(resultados, PERIODOS, BANDAS, DIAS_FUTURO, ticker=TICKER)
 
    
# ── RESUMEN GLOBAL — comparación entre todos los mercados ────────────────────
print("\n" + "=" * 70)
print("  RESUMEN GLOBAL — TOP BUY por mercado a 30 días")
print("=" * 70)

import pandas as pd
frames = []
for ticker_g, res_g in resultados_globales.items():
    for periodo_g in res_g:
        for banda_g, datos_g in res_g[periodo_g].items():
            tbl_g = datos_g["tabla_rendimientos"]
            if tbl_g.empty or "signal" not in tbl_g.columns:
                continue
            for tipo_g in ["BUY", "SELL"]:
                sub_g = tbl_g[tbl_g["signal"] == tipo_g]
                if sub_g.empty or len(sub_g) < 3:
                    continue
                r30 = sub_g["ret_30d"].dropna()
                if len(r30) == 0:
                    continue
                frames.append({
                    "Mercado":   ticker_g,
                    "RSI":       periodo_g,
                    "Banda":     banda_g,
                    "Señal":     tipo_g,
                    "N":         len(sub_g),
                    "Ret_30d%":  round(r30.mean(), 2),
                    "WR_30d%":   round((r30 > 0).mean() * 100, 1),
                })

if frames:
    df_global = pd.DataFrame(frames).sort_values("Ret_30d%", ascending=False)
    print("\n  TOP 10 combinaciones ganadoras (mínimo 3 señales):")
    print(df_global.head(10).to_string(index=False))
    print("\n  TOP 10 combinaciones perdedoras:")
    print(df_global.tail(10).to_string(index=False)) 
print("\n" + "=" * 60)
print("  ANALISIS COMPLETADO")
print("=" * 60)
print(f"""
RESUMEN:
 
BENCHMARK BUY AND HOLD:
  Retorno total  : {bnh['retorno_total_%']}%
  Retorno anual  : {bnh['retorno_anual_%']}%
  Volatilidad    : {bnh['volatilidad_%']}%
  Sharpe Ratio   : {bnh['sharpe']}
 
Si el Sharpe de alguna senal RSI supera {bnh['sharpe']},
esa combinacion periodo/banda es potencialmente mejor
que simplemente comprar y mantener el indice.
""")
print("\n✅ Todas las combinaciones completadas.")