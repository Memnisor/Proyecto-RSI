# =============================================================================
#  parte_optimizador_rsi.py  —  OPTIMIZADOR RSI POR MERCADO
# =============================================================================

from fn_descargar        import descargar_datos
from fn_benchmark        import calcular_benchmark, imprimir_benchmark
from fn_optimizador_rsi  import optimizar_rsi_random

import pandas as pd
import numpy as np


# =============================================================================
#  PARÁMETROS
# =============================================================================

TICKERS = [
    "^GSPC",
    "^BVSP",
    "^MXX",
    "^MERV",
    "GXG",
    "EPU",
    "ILF",
]

AÑOS = 5
INTERVALO = "1d"
N_INTENTOS = 300
HORIZONTE_OBJETIVO = 30
MIN_SEÑALES = 10      # ← CAMBIO CLAVE: mínimo 10 señales
SEMILLA = 42
DIAS_FUTURO = [1, 3, 5, 10, 30, 60, 90]


# =============================================================================
#  OPTIMIZACIÓN
# =============================================================================

resultados_optimos = []
todos_historiales = {}

for TICKER in TICKERS:

    print("\n" + "#" * 60)
    print(f"  OPTIMIZANDO RSI: {TICKER}")
    print("#" * 60)

    try:
        df = descargar_datos(TICKER, años=AÑOS, intervalo=INTERVALO)
        bnh = calcular_benchmark(df)
        imprimir_benchmark(bnh, ticker=TICKER)

        mejor_dict, mejor_score, historial = optimizar_rsi_random(
            df,
            dias_futuro=DIAS_FUTURO,
            n_intentos=N_INTENTOS,
            horizonte_objetivo=HORIZONTE_OBJETIVO,
            min_señales=MIN_SEÑALES,
            semilla=SEMILLA
        )

        if mejor_dict is None:
            print(f"  ❌ No se pudo optimizar {TICKER}")
            continue

        mejor_dict["ticker"] = TICKER
        mejor_dict["benchmark_sharpe"] = bnh["sharpe"]
        resultados_optimos.append(mejor_dict)
        todos_historiales[TICKER] = historial

        print(f"\n  📊 COMPARACIÓN CON BUY & HOLD:")
        print(f"     Buy & Hold Sharpe: {bnh['sharpe']:.2f}")
        print(f"     RSI Óptimo Sharpe: {mejor_score:.2f}")
        if mejor_score > bnh['sharpe']:
            print(f"     ✅ RSI SUPERA al benchmark")
        else:
            print(f"     ⚠️  RSI NO supera al benchmark")

    except Exception as e:
        print(f"  ❌ Error con {TICKER}: {e}")
        continue


# =============================================================================
#  RESUMEN FINAL
# =============================================================================

if resultados_optimos:
    print("\n" + "=" * 90)
    print("  🏆 RESUMEN: MEJORES COMBINACIONES RSI POR MERCADO")
    print("=" * 90)

    df_optimos = pd.DataFrame(resultados_optimos)

    cols_mostrar = [
        "ticker", "periodo_rsi", "sobreventa", "sobrecompra",
        "tipo_señal", "sharpe", "retorno_%", "winrate_%",
        "n_señales", "benchmark_sharpe"
    ]
    df_optimos = df_optimos[cols_mostrar]

    df_optimos.columns = [
        "Mercado", "Período", "Sobreventa", "Sobrecompra",
        "Señal", "Sharpe RSI", "Retorno%", "WinRate%",
        "N Señales", "Sharpe B&H"
    ]

    df_optimos = df_optimos.sort_values("Sharpe RSI", ascending=False)
    df_optimos = df_optimos.reset_index(drop=True)

    print(df_optimos.to_string(index=False))

    # Exportar
    nombre_optimos = "mejores_combinaciones_RSI.xlsx"
    df_optimos.to_excel(nombre_optimos, index=False)
    print(f"\n  💾 Exportado: {nombre_optimos}")

    nombre_historial = "optimizacion_RSI_historial.xlsx"
    with pd.ExcelWriter(nombre_historial, engine="openpyxl") as writer:
        for ticker, hist in todos_historiales.items():
            if not hist.empty:
                ticker_safe = ticker.replace("^", "").replace("/", "-")
                hist.to_excel(writer, sheet_name=ticker_safe[:31], index=False)
    print(f"  💾 Exportado: {nombre_historial}")

else:
    print("\n  ❌ Sin resultados.")

print("\n✅ Optimización RSI completada.")