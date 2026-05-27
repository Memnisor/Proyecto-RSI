# =============================================================================
#  fn_tabla.py
#  FUNCIÓN: tabla_estadisticas
# =============================================================================
#
#  QUÉ HACE:
#    Toma la tabla de rendimientos futuros y calcula dos métricas
#    clave para evaluar si una estrategia funciona:
#      • Retorno promedio (Media%)
#      • Tasa de acierto   (Win Rate%)
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - Agregar más métricas: mediana, desviación estándar,
#      Sharpe ratio, peor pérdida, mejor ganancia
#    - Cambiar el formato de la tabla (decimales, nombres de columnas)
#    - Agregar colores con la librería "rich" o "tabulate"
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: tabla_estadisticas
#    - Los parámetros: (df_rend, dias_futuro)
#    - La estructura de salida: DataFrame con índice BUY/SELL
#
# =============================================================================

import pandas as pd
import numpy as np


def tabla_estadisticas(df_rend: pd.DataFrame,
                        dias_futuro: list) -> pd.DataFrame:
    """
    Calcula retorno promedio y Win Rate para señales BUY y SELL.

    ¿Qué es el Win Rate?
    ─────────────────────
    Porcentaje de operaciones que terminaron con ganancia.
        100% → todas ganadoras (imposible en práctica)
         70% → 7 de cada 10 operaciones fueron ganadoras ✅
         50% → igual que lanzar una moneda al azar
         30% → la mayoría perdedoras ❌

    ¿Qué es la Media%?
    ───────────────────
    Promedio de todos los retornos (positivos y negativos).
    Una estrategia puede tener Win Rate del 60% pero Media% negativa
    si las pérdidas son mucho mayores que las ganancias.
    Por eso hay que mirar AMBAS métricas juntas.

    Parámetros
    ----------
    df_rend     : pd.DataFrame  Salida de calcular_rendimientos_futuros
    dias_futuro : list          Misma lista usada al calcular rendimientos

    Retorna
    -------
    pd.DataFrame con filas BUY/SELL y columnas:
        N             → número de señales
        Media_Nd%     → retorno promedio a N días
        WinRate_Nd%   → % de señales ganadoras a N días
    """
    # Verificación defensiva: si no hay datos o no tiene la columna "signal"
    if df_rend.empty or "signal" not in df_rend.columns:
        return pd.DataFrame()

    filas = []

    for tipo in ["BUY", "SELL"]:
        sub = df_rend[df_rend["signal"] == tipo]

        if sub.empty:
            continue

        fila = {"Señal": tipo, "N": len(sub)}

        for n in dias_futuro:
            col  = f"ret_{n}d"
            vals = sub[col].dropna()

            if len(vals) == 0:
                fila[f"Media_{n}d%"]   = np.nan
                fila[f"WinRate_{n}d%"] = np.nan
            else:
                # Retorno promedio redondeado a 2 decimales
                fila[f"Media_{n}d%"]   = round(vals.mean(), 2)
                # Win Rate: fracción de retornos positivos × 100
                fila[f"WinRate_{n}d%"] = round((vals > 0).mean() * 100, 1)

        filas.append(fila)

    return pd.DataFrame(filas).set_index("Señal")



# =============================================================================
#  FUNCIÓN NUEVA PARA AGREGAR AL FINAL DE fn_tabla.py
#  Copia todo este contenido y pégalo al final del archivo fn_tabla.py
# =============================================================================


def tabla_comparativa_maestra(resultados: dict,
                               periodos: list,
                               bandas: list,
                               dias_futuro: list,
                               ticker: str="") -> pd.DataFrame:
    """
    Reúne TODOS los resultados en una sola tabla ordenada por retorno
    promedio a 30 días (de mejor a peor).

    ¿Para qué sirve?
    ─────────────────
    Cuando tienes 5 períodos × 3 bandas × 2 señales = 30 combinaciones,
    es imposible compararlas mirando 30 tablas separadas.
    Esta función las junta todas y las ordena para que veas de un vistazo:
      • Qué combinación tuvo el mayor retorno promedio
      • Cuál tuvo el mejor Win Rate
      • El Top 5 de las mejores combinaciones

    Parámetros
    ----------
    resultados  : dict   Diccionario maestro con todos los resultados
                         resultados[periodo]["30/70"]["tabla_rendimientos"]
    periodos    : list   Lista de períodos RSI analizados, ej. [7, 14, 20]
    bandas      : list   Lista de bandas como tuplas, ej. [(30,70),(20,80)]
    dias_futuro : list   Horizontes usados, ej. [1, 3, 5, 10, 30, 60, 90]

    Retorna
    -------
    pd.DataFrame con todas las combinaciones ordenadas por Ret_30d%
    """

    filas = []   # lista vacía donde iremos acumulando una fila por combinación

    # ── Bucle triple: período × banda × tipo de señal ─────────────────────────
    for periodo in periodos:
        for sv, sc in bandas:
            clave_banda = f"{sv}/{sc}"   # convierte (30,70) → "30/70"

            try:
                # Accedemos al DataFrame de rendimientos de esta combinación
                tabla_rend = resultados[periodo][clave_banda]["tabla_rendimientos"]
            except KeyError:
                # Si no existe esta combinación en el diccionario, la saltamos
                continue

            # Si el DataFrame está vacío o no tiene la columna "signal" → saltar
            if tabla_rend.empty or "signal" not in tabla_rend.columns:
                continue

            for tipo_senal in ["BUY", "SELL"]:

                # Filtramos solo las filas de este tipo de señal
                sub = tabla_rend[tabla_rend["signal"] == tipo_senal]

                if sub.empty:
                    continue   # no hay señales de este tipo → siguiente iteración

                # ── Construir una fila de la tabla maestra ────────────────────
                fila = {
                    "RSI_Periodo": periodo,      # ej. 7
                    "Banda":       clave_banda,  # ej. "30/70"
                    "Senal":       tipo_senal,   # "BUY" o "SELL"
                    "N_senales":   len(sub),     # cuántas señales hubo
                }

                # Para cada horizonte calculamos retorno promedio y Win Rate
                for n in dias_futuro:
                    col  = f"ret_{n}d"          # nombre de la columna, ej. "ret_30d"
                    vals = sub[col].dropna()    # valores sin NaN

                    if len(vals) > 0:
                        # Retorno promedio redondeado a 2 decimales
                        fila[f"Ret_{n}d%"] = round(vals.mean(), 2)

                        # Win Rate: fracción positivos × 100
                        fila[f"WR_{n}d%"]  = round((vals > 0).mean() * 100, 1)
                    else:
                        # No hay datos suficientes para este horizonte
                        fila[f"Ret_{n}d%"] = np.nan
                        fila[f"WR_{n}d%"]  = np.nan

                filas.append(fila)   # agregamos esta fila a la lista

    # ── Verificar que hay datos ───────────────────────────────────────────────
    if not filas:
        print("  Sin datos para construir la tabla comparativa.")
        return pd.DataFrame()   # retorna tabla vacía

    # ── Construir el DataFrame ────────────────────────────────────────────────
    # pd.DataFrame(filas) convierte la lista de diccionarios en tabla
    df_resumen = pd.DataFrame(filas)

    # ── Ordenar por retorno a 30 días (mejor primero) ─────────────────────────
    # Si "Ret_30d%" existe → ordenamos por ella
    # Si no existe (ej. no calculamos 30 días) → usamos el último horizonte
    if "Ret_30d%" in df_resumen.columns:
        col_orden = "Ret_30d%"
    else:
        col_orden = f"Ret_{dias_futuro[-1]}d%"   # último horizonte disponible

    # ascending=False → de mayor a menor (mejor primero)
    # reset_index(drop=True) → renumera las filas desde 0
    df_resumen = df_resumen.sort_values(col_orden,
                                         ascending=False).reset_index(drop=True)

    # ── Imprimir tabla completa ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  TABLA COMPARATIVA MAESTRA -{ticker} — Ordenada por Retorno promedio a 30d")
    print("=" * 70)

    # Bloque 1: Retornos promedio
    # Seleccionamos columnas de identificación + columnas de retorno
    cols_ret = (["RSI_Periodo", "Banda", "Senal", "N_senales"] +
                [f"Ret_{n}d%" for n in dias_futuro
                 if f"Ret_{n}d%" in df_resumen.columns])

    print("\n  RETORNO PROMEDIO (%) — positivo = ganancia en promedio")
    # to_string(index=False) → imprime sin el número de fila a la izquierda
    print(df_resumen[cols_ret].to_string(index=False))

    # Bloque 2: Win Rate
    cols_wr = (["RSI_Periodo", "Banda", "Senal"] +
               [f"WR_{n}d%" for n in dias_futuro
                if f"WR_{n}d%" in df_resumen.columns])

    print("\n  WIN RATE (%) — porcentaje de operaciones ganadoras")
    print(df_resumen[cols_wr].to_string(index=False))

    # ── Top 5 ─────────────────────────────────────────────────────────────────
    # .head(5) → primeras 5 filas (las mejores porque ya está ordenado)
    print("\n" + "-" * 70)
    print("  TOP 5 combinaciones por Retorno a 30 dias:")
    print("-" * 70)
    print(df_resumen[cols_ret].head(5).to_string(index=False))

    return df_resumen   # retornamos el DataFrame por si se necesita después
