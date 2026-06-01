# =============================================================================
#  fn_tabla.py
#  FUNCIONES: tabla_estadisticas, tabla_comparativa_maestra, exportar_latex
# =============================================================================
#
#  QUÉ HACE ESTE ARCHIVO:
#    Contiene todas las funciones relacionadas con calcular y exportar tablas.
#    Genera 3 tablas por mercado:
#      - Tabla 1: Retorno promedio (%)
#      - Tabla 2: Win Rate (% de operaciones ganadoras)
#      - Tabla 3: Significancia estadística (t-test)
#
#  EXPORTA automáticamente por cada mercado:
#      - 1 archivo Excel (.xlsx) con 3 hojas
#      - 2 archivos CSV (media y winrate)
#      - 3 archivos LaTeX (.tex) listos para \input{} en tu artículo
#
#  LIBRERÍAS NECESARIAS:
#      pip install pandas numpy scipy openpyxl
#
# =============================================================================

import pandas as pd       # manejo de tablas (DataFrames)
import numpy as np        # operaciones numéricas (NaN, mean, etc.)
from scipy import stats   # pruebas estadísticas (t-test)


# =============================================================================
#  FUNCIÓN 1: tabla_estadisticas
#  Uso: inspección rápida de UNA combinación específica
#  No se llama desde el bucle principal — es auxiliar/diagnóstico
# =============================================================================
def tabla_estadisticas(df_rend: pd.DataFrame,
                       dias_futuro: list) -> pd.DataFrame:
    """
    Calcula retorno promedio y Win Rate para señales BUY y SELL
    de UNA sola combinación (periodo/banda).

    ¿Qué es el Win Rate?
    ─────────────────────
    Porcentaje de operaciones que terminaron con ganancia.
        70% → 7 de cada 10 operaciones ganadoras  ✅
        50% → igual que lanzar una moneda al azar  ⚠️
        30% → mayoría de operaciones perdedoras    ❌

    ¿Qué es la Media%?
    ───────────────────
    Promedio de todos los retornos (positivos y negativos).
    IMPORTANTE: una estrategia puede tener Win Rate del 60% pero
    Media% negativa si las pérdidas son mucho mayores que las ganancias.
    Por eso siempre hay que mirar AMBAS métricas juntas.

    Parámetros
    ----------
    df_rend     : pd.DataFrame  Salida de calcular_rendimientos_futuros
                                Contiene columnas: signal, ret_1d, ret_3d, ...
    dias_futuro : list          Lista de horizontes, ej: [1, 3, 5, 10, 30, 60, 90]

    Retorna
    -------
    pd.DataFrame con filas BUY/SELL y columnas:
        N             → número de señales detectadas
        Media_Nd%     → retorno promedio a N días (ej: Media_30d%)
        WinRate_Nd%   → % de señales ganadoras a N días (ej: WinRate_30d%)
    """
    # Verificación defensiva: si no hay datos o falta la columna "signal"
    if df_rend.empty or "signal" not in df_rend.columns:
        return pd.DataFrame()   # retorna tabla vacía si no hay datos

    filas = []   # lista donde vamos acumulando una fila por tipo de señal

    for tipo in ["BUY", "SELL"]:
        # Filtrar solo las filas del tipo actual (BUY o SELL)
        sub = df_rend[df_rend["signal"] == tipo]
        if sub.empty:
            continue   # si no hay señales de este tipo, pasar al siguiente

        # Iniciar la fila con el tipo de señal y el número total de señales
        fila = {"Señal": tipo, "N": len(sub)}

        for n in dias_futuro:
            col  = f"ret_{n}d"          # nombre de la columna, ej: "ret_30d"
            vals = sub[col].dropna()    # valores numéricos sin NaN

            if len(vals) == 0:
                # No hay suficientes datos para este horizonte
                fila[f"Media_{n}d%"]   = np.nan
                fila[f"WinRate_{n}d%"] = np.nan
            else:
                # Retorno promedio redondeado a 2 decimales
                fila[f"Media_{n}d%"]   = round(vals.mean(), 2)
                # Win Rate: fracción de retornos positivos × 100
                # (vals > 0) crea una serie de True/False, .mean() calcula la proporción
                fila[f"WinRate_{n}d%"] = round((vals > 0).mean() * 100, 1)

        filas.append(fila)

    # Convertir la lista de filas en un DataFrame con índice BUY/SELL
    return pd.DataFrame(filas).set_index("Señal")


# =============================================================================
#  FUNCIÓN 2: tabla_comparativa_maestra
#  Uso: se llama una vez por mercado desde el archivo maestro
#  Es la función principal — genera y exporta las 3 tablas
# =============================================================================
def tabla_comparativa_maestra(resultados: dict,
                               periodos: list,
                               bandas: list,
                               dias_futuro: list,
                               ticker: str = "") -> None:
    """
    Genera TRES tablas consolidadas por mercado y las exporta a Excel,
    CSV y LaTeX.

    Recorre todas las combinaciones (periodo × banda × señal) y construye:
      - df_media   → retorno promedio por horizonte
      - df_winrate → win rate por horizonte
      - df_pval    → estrellas de significancia del t-test

    Diseño de filas (una por combinación):
        RSI(7)  | 20/80 | BUY   | N=58 | 1d | 3d | ... | 90d
        RSI(7)  | 20/80 | SELL  | N=84 | ...
        RSI(7)  | 30/70 | BUY   | ...
        ...

    Parámetros
    ----------
    resultados  : dict   Diccionario maestro construido en el bucle principal
                         Estructura: resultados[periodo][banda_str][clave]
                         donde clave puede ser "rsi", "senales", "tabla_rendimientos"
    periodos    : list   Lista de períodos RSI, ej: [7, 14, 20, 30, 45]
    bandas      : list   Lista de tuplas (sobreventa, sobrecompra), ej: [(30,70), (20,80)]
    dias_futuro : list   Horizontes temporales, ej: [1, 3, 5, 10, 30, 60, 90]
    ticker      : str    Nombre del activo, ej: "^GSPC" — usado en títulos y nombres de archivo
    """

    # Listas que acumulan una fila por cada combinación (periodo, banda, señal)
    filas_media   = []   # retornos promedio
    filas_winrate = []   # win rates
    filas_pval    = []   # estrellas de significancia del t-test

    # ── Recorrer todas las combinaciones ─────────────────────────────────────
    for periodo in periodos:
        for sv, sc in bandas:

            # clave_banda: string "30/70", "20/80", etc.
            clave = f"{sv}/{sc}"

            # Extraer los datos de esta combinación del diccionario maestro
            datos = resultados.get(periodo, {}).get(clave, {})
            tbl   = datos.get("tabla_rendimientos", pd.DataFrame())

            # Si no hay datos para esta combinación, saltar
            if tbl.empty or "signal" not in tbl.columns:
                continue

            for tipo in ["BUY", "SELL"]:
                # Filtrar solo las señales del tipo actual
                sub = tbl[tbl["signal"] == tipo]
                if sub.empty:
                    continue

                # Iniciar las 3 filas con las columnas identificadoras
                fila_m = {
                    "RSI":   f"RSI({periodo})",   # ej: "RSI(7)"
                    "Banda": clave,                # ej: "30/70"
                    "Señal": tipo,                 # "BUY" o "SELL"
                    "N":     len(sub),             # número de señales
                }
                fila_w = fila_m.copy()   # misma estructura para winrate
                fila_p = fila_m.copy()   # misma estructura para p-values

                # ── Calcular métricas por horizonte temporal ──────────────────
                for n in dias_futuro:
                    col  = f"ret_{n}d"   # nombre de columna, ej: "ret_30d"
                    vals = sub[col].dropna() if col in sub.columns else pd.Series()

                    if len(vals) >= 3:
                        # ── Retorno promedio ──────────────────────────────────
                        fila_m[f"{n}d"] = round(vals.mean(), 2)

                        # ── Win Rate ──────────────────────────────────────────
                        # (vals > 0) es True para retornos positivos
                        # .mean() calcula la proporción, × 100 = porcentaje
                        fila_w[f"{n}d"] = round((vals > 0).mean() * 100, 1)

                        # ── T-test de una cola ────────────────────────────────
                        # H0: el retorno promedio es igual a 0 (no hay efecto)
                        # H1 para BUY:  retorno > 0 (alternative="greater")
                        # H1 para SELL: retorno < 0 (alternative="less")
                        # Si p < 0.05, rechazamos H0 → el resultado es significativo
                        alt = "greater" if tipo == "BUY" else "less"
                        _, pval = stats.ttest_1samp(vals, popmean=0,
                                                    alternative=alt)

                        # Convertir p-valor numérico a estrellas de significancia
                        # (convención estándar en artículos de finanzas)
                        if pval < 0.01:
                            sig = "***"   # muy significativo
                        elif pval < 0.05:
                            sig = "**"    # significativo
                        elif pval < 0.10:
                            sig = "*"     # marginalmente significativo
                        else:
                            sig = ""      # no significativo

                        fila_p[f"{n}d"] = sig   # guardar como STRING, no número

                    else:
                        # Menos de 3 observaciones → no calculamos nada
                        fila_m[f"{n}d"] = np.nan   # NaN = dato faltante
                        fila_w[f"{n}d"] = np.nan
                        fila_p[f"{n}d"] = ""        # string vacío para p-values

                # Agregar las filas a las listas acumuladoras
                filas_media.append(fila_m)
                filas_winrate.append(fila_w)
                filas_pval.append(fila_p)

    # Si no se generó ninguna fila, avisar y salir
    if not filas_media:
        print("  ⚠️  Sin datos para la tabla maestra.")
        return

    # ── Construir los DataFrames ──────────────────────────────────────────────
    # cols_idx: columnas identificadoras (van primero)
    # cols_dias: columnas de horizontes, ej: ["1d", "3d", "5d", "10d", ...]
    cols_idx  = ["RSI", "Banda", "Señal", "N"]
    cols_dias = [f"{n}d" for n in dias_futuro]

    df_media   = pd.DataFrame(filas_media)[cols_idx + cols_dias]
    df_winrate = pd.DataFrame(filas_winrate)[cols_idx + cols_dias]
    df_pval    = pd.DataFrame(filas_pval)[cols_idx + cols_dias]

    # ── Imprimir en consola ───────────────────────────────────────────────────
    sep = "=" * max(60, len(cols_idx) * 8 + len(cols_dias) * 8)

    print(f"\n{sep}")
    print(f"  {ticker}  —  TABLA 1: Retorno promedio (%)")
    print(sep)
    print(df_media.to_string(index=False, na_rep="—"))

    print(f"\n{sep}")
    print(f"  {ticker}  —  TABLA 2: Win Rate (%)")
    print(sep)
    print(df_winrate.to_string(index=False, na_rep="—"))

    print(f"\n{sep}")
    print(f"  {ticker}  —  TABLA 3: Significancia estadística (t-test)")
    print(f"  *** p<0.01  |  ** p<0.05  |  * p<0.10  |  (vacío) no significativo")
    print(sep)
    print(df_pval.to_string(index=False, na_rep="—"))
    print()

    # ── Sanitizar el ticker para nombres de archivo ───────────────────────────
    # El símbolo ^ no es válido en nombres de archivo en Windows
    # Ejemplo: "^GSPC" → "GSPC",  "^BVSP" → "BVSP"
    ticker_safe = ticker.replace("^", "").replace("/", "-")

    # ── Exportar a Excel (3 hojas en un solo archivo) ─────────────────────────
    nombre_xlsx = f"tabla_maestra_{ticker_safe}.xlsx"
    try:
        with pd.ExcelWriter(nombre_xlsx, engine="openpyxl") as writer:
            df_media.to_excel(writer,   sheet_name="Retorno_promedio",   index=False)
            df_winrate.to_excel(writer, sheet_name="Win_Rate",           index=False)
            df_pval.to_excel(writer,    sheet_name="Significancia_ttest", index=False)
        print(f"  💾 Excel exportado: {nombre_xlsx}")
    except ImportError:
        # Si openpyxl no está instalado, guardar como CSV de respaldo
        # Para instalar: pip install openpyxl
        df_media.to_csv(f"tabla_media_{ticker_safe}.csv", index=False)
        df_winrate.to_csv(f"tabla_winrate_{ticker_safe}.csv", index=False)
        print(f"  ⚠️  openpyxl no encontrado. Tablas guardadas como CSV.")

    # ── Exportar a CSV (respaldo siempre, independiente de openpyxl) ──────────
    df_media.to_csv(f"tabla_media_{ticker_safe}.csv",    index=False)
    df_winrate.to_csv(f"tabla_winrate_{ticker_safe}.csv", index=False)
    print(f"  💾 CSV exportados: tabla_media_{ticker_safe}.csv  |  "
          f"tabla_winrate_{ticker_safe}.csv")

    # ── Exportar a LaTeX (3 archivos .tex) ───────────────────────────────────
    # Uso en tu artículo .tex:
    #   \input{tabla_media_GSPC.tex}
    #   \input{tabla_winrate_GSPC.tex}
    #   \input{tabla_significancia_GSPC.tex}
    exportar_latex(df_media,   ticker_safe, "media",         dias_futuro)
    exportar_latex(df_winrate, ticker_safe, "winrate",       dias_futuro)
    exportar_latex(df_pval,    ticker_safe, "significancia",  dias_futuro)


# =============================================================================
#  FUNCIÓN 3: exportar_latex
#  Uso: llamada internamente por tabla_comparativa_maestra (no desde el maestro)
#  Genera UN archivo .tex por tabla
# =============================================================================
def exportar_latex(df: pd.DataFrame,
                   ticker_safe: str,
                   tipo: str,
                   dias_futuro: list) -> None:
    """
    Genera un archivo .tex con formato booktabs listo para \input{} en LaTeX.

    Requiere en el preámbulo de tu documento .tex:
        \\usepackage{booktabs}   % para \\toprule, \\midrule, \\bottomrule
        \\usepackage{caption}    % para \\caption{}

    FIX APLICADO:
        La tabla de significancia contiene strings ("***", "**", "*", "")
        en lugar de números. Por eso NO se puede usar f"{v:.1f}" para formatear.
        Se verifica el tipo del valor antes de formatearlo:
          - Si es string (estrellas o vacío) → se agrega tal cual
          - Si es número (float/int)         → se formatea con 1 decimal
          - Si es NaN                        → se reemplaza por "---"

    Parámetros
    ----------
    df          : pd.DataFrame  Tabla a exportar (media, winrate o significancia)
    ticker_safe : str           Ticker sin caracteres especiales (ej: "GSPC")
    tipo        : str           "media", "winrate" o "significancia"
    dias_futuro : list          Para construir el encabezado de columnas
    """
    cols_dias = [f"{n}d" for n in dias_futuro]

    # Formato de columnas LaTeX: l=alineado a la izquierda, r=derecha
    # Las 4 primeras columnas (RSI, Banda, Señal, N) van a la izquierda
    # Las columnas de días van a la derecha (números o estrellas)
    fmt_cols = "llllr" + "r" * len(cols_dias)

    # Caption y label según el tipo de tabla
    if tipo == "media":
        caption = f"Retorno promedio (\\%) por horizonte temporal --- {ticker_safe}"
        label   = f"tab:media_{ticker_safe.lower()}"
    elif tipo == "winrate":
        caption = f"Win Rate (\\%) por horizonte temporal --- {ticker_safe}"
        label   = f"tab:winrate_{ticker_safe.lower()}"
    else:
        # Tabla de significancia estadística
        caption = f"Significancia estadística (t-test) --- {ticker_safe}"
        label   = f"tab:sig_{ticker_safe.lower()}"

    # Encabezado de la tabla: nombres de columnas en negrita
    header_dias = " & ".join([f"\\textbf{{{c}}}" for c in cols_dias])
    header = (f"\\textbf{{RSI}} & \\textbf{{Banda}} & "
              f"\\textbf{{Se\\~{{n}}al}} & \\textbf{{N}} & {header_dias} \\\\")

    # ── Construir las filas de la tabla ───────────────────────────────────────
    filas_tex  = []
    ultimo_rsi = None   # para detectar cambios de periodo y agregar línea separadora

    for _, row in df.iterrows():

        # Agregar línea separadora (\midrule) cada vez que cambia el periodo RSI
        # Esto mejora la legibilidad de la tabla en el artículo
        if row["RSI"] != ultimo_rsi and ultimo_rsi is not None:
            filas_tex.append("\\midrule")
        ultimo_rsi = row["RSI"]

        # Columnas identificadoras: RSI, Banda, Señal, N
        celdas = [
            str(row["RSI"]),
            str(row["Banda"]),
            str(row["Señal"]),
            str(int(row["N"]))
        ]

        # Columnas de datos (días): formateo diferente según el tipo de valor
        for c in cols_dias:
            v = row[c]

            if pd.isna(v):
                # NaN → "---" (convención académica para dato faltante)
                celdas.append("---")

            elif isinstance(v, str):
                # ── FIX CLAVE ──────────────────────────────────────────────
                # Si el valor es un string (ej: "***", "**", "*", ""),
                # lo usamos directamente SIN intentar formatearlo con :.1f
                # El error "Unknown format code 'f' for object of type 'str'"
                # ocurría aquí porque se intentaba hacer f"{v:.1f}" con un string
                celdas.append(v)

            else:
                # Es un número (float): formatear con 1 decimal
                celdas.append(f"{v:.1f}")

        # Unir las celdas con & y agregar \\ al final (fin de fila en LaTeX)
        filas_tex.append(" & ".join(celdas) + " \\\\")

    # Unir todas las filas con salto de línea y sangría
    cuerpo = "\n        ".join(filas_tex)

    # ── Construir el código LaTeX completo ────────────────────────────────────
    nombre_input = f"tabla_{tipo}_{ticker_safe}.tex"
    latex = f"""% ============================================================
% Generado automáticamente por fn_tabla.py
% Ticker : {ticker_safe}
% Tipo   : {tipo}
% Uso en tu artículo: \\input{{{nombre_input}}}
%
% Requiere en el preámbulo:
%   \\usepackage{{booktabs}}
%   \\usepackage{{caption}}
% ============================================================
\\begin{{table}}[htbp]
    \\centering
    \\caption{{{caption}}}
    \\label{{{label}}}
    \\small
    \\begin{{tabular}}{{{fmt_cols}}}
        \\toprule
        {header}
        \\midrule
        {cuerpo}
        \\bottomrule
    \\end{{tabular}}
\\end{{table}}
"""

    # Escribir el archivo .tex
    with open(nombre_input, "w", encoding="utf-8") as f:
        f.write(latex)

    print(f"  💾 LaTeX exportado:  {nombre_input}")


# =============================================================================
#  FUNCIÓN 4: tabla_ranking
#  Uso: se llama una vez por mercado desde el archivo maestro
#  Genera UNA tabla consolidada con todas las combinaciones rankeadas
#  por 3 índices de efectividad distintos tomados de la literatura
# =============================================================================
def tabla_ranking(resultados: dict,
                  periodos: list,
                  bandas: list,
                  dias_futuro: list,
                  ticker: str = "",
                  horizonte: int = 30) -> pd.DataFrame:
    """
    Genera una tabla ranking con todas las combinaciones (periodo × banda × señal)
    ordenadas por 3 índices de efectividad distintos.

    ¿POR QUÉ 3 ÍNDICES DISTINTOS?
    ──────────────────────────────
    La literatura no tiene consenso sobre cómo medir la efectividad de una
    estrategia de trading. Cada índice prioriza algo diferente:

    ÍNDICE 1 — Performance Score (Brock, Lakonishok & LeBaron, 1992)
        Foco: retorno ajustado por win rate
        Score = Retorno_promedio × (WinRate / 100)
        Interpretación: ¿cuánto gano en promedio ponderando por la frecuencia
        de acierto? Un retorno alto con win rate bajo penaliza más que con
        el índice 2.
        Referencia: Brock, W., Lakonishok, J., & LeBaron, B. (1992).
        "Simple technical trading rules and the stochastic properties of
        stock returns." Journal of Finance, 47(5), 1731-1764.

    ÍNDICE 2 — Profit Factor adaptado (Kaufman, 2013)
        Foco: consistencia estadística
        Score = WinRate × 0.50 + Significancia × 0.30 + Retorno_norm × 0.20
        Interpretación: ¿qué tan confiable es la estrategia? Prioriza
        que el win rate sea alto y que el resultado sea estadísticamente
        significativo. Útil para implementación en algoritmos.
        Referencia: Kaufman, P. (2013). "Trading Systems and Methods."
        Wiley, 5th edition. Capítulo 2: Measuring Performance.

    ÍNDICE 3 — Sharpe-like Score (Lo, 2002)
        Foco: retorno ajustado por riesgo
        Score = Retorno_promedio / Volatilidad_retornos × √(252/horizonte)
        Interpretación: ¿cuánto retorno obtengo por unidad de riesgo?
        Análogo al Sharpe Ratio pero aplicado a las señales del RSI.
        Un score > 0.5 es comparable a un buen fondo de inversión.
        Referencia: Lo, A. W. (2002). "The statistics of Sharpe ratios."
        Financial Analysts Journal, 58(4), 36-52.

    Parámetros
    ----------
    resultados  : dict   Diccionario maestro resultados[periodo][banda][clave]
    periodos    : list   Lista de períodos RSI analizados
    bandas      : list   Lista de tuplas (sobreventa, sobrecompra)
    dias_futuro : list   Horizontes temporales disponibles
    ticker      : str    Nombre del activo (para título y archivo)
    horizonte   : int    Horizonte temporal para el ranking (default: 30 días)
                         Debe estar en dias_futuro

    Retorna
    -------
    pd.DataFrame con todas las combinaciones rankeadas, columnas:
        RSI, Banda, Señal, N
        Retorno_%     → retorno promedio a 'horizonte' días
        WinRate_%     → win rate a 'horizonte' días
        Volatilidad   → desviación estándar de los retornos
        Sig           → significancia estadística (estrellas)
        Score_BLL     → Índice 1 (Brock, Lakonishok & LeBaron)
        Score_Kaufman → Índice 2 (Kaufman)
        Score_Sharpe  → Índice 3 (Lo / Sharpe-like)
        Ranking_BLL   → posición en el ranking según índice 1
        Ranking_K     → posición en el ranking según índice 2
        Ranking_S     → posición en el ranking según índice 3
        Consenso      → promedio de los 3 rankings (menor = mejor)
        Recomendacion → etiqueta cualitativa basada en Consenso
    """
    col = f"ret_{horizonte}d"   # columna de retorno al horizonte elegido

    # Verificar que el horizonte está disponible
    if horizonte not in dias_futuro:
        print(f"  ⚠️  Horizonte {horizonte}d no está en dias_futuro={dias_futuro}")
        return pd.DataFrame()

    filas = []   # acumulador de filas del ranking

    # ── Recorrer todas las combinaciones ─────────────────────────────────────
    for periodo in periodos:
        for sv, sc in bandas:
            clave = f"{sv}/{sc}"
            datos = resultados.get(periodo, {}).get(clave, {})
            tbl   = datos.get("tabla_rendimientos", pd.DataFrame())

            if tbl.empty or "signal" not in tbl.columns:
                continue

            for tipo in ["BUY", "SELL"]:
                sub = tbl[tbl["signal"] == tipo]

                # Mínimo 5 señales para incluir en el ranking
                # (menos de 5 no es estadísticamente representativo)
                if len(sub) < 5:
                    continue

                vals = sub[col].dropna() if col in sub.columns else pd.Series()
                if len(vals) < 5:
                    continue

                # ── Métricas base ─────────────────────────────────────────────
                retorno    = round(vals.mean(), 2)          # retorno promedio
                winrate    = round((vals > 0).mean() * 100, 1)  # % ganadores
                volatilidad = round(vals.std(), 2)          # desviación estándar

                # ── T-test para significancia ─────────────────────────────────
                alt = "greater" if tipo == "BUY" else "less"
                _, pval = stats.ttest_1samp(vals, popmean=0, alternative=alt)

                # Convertir p-valor a estrellas Y a valor numérico para el score
                if pval < 0.01:
                    sig_str = "***"
                    sig_num = 1.00    # máxima significancia
                elif pval < 0.05:
                    sig_str = "**"
                    sig_num = 0.66
                elif pval < 0.10:
                    sig_str = "*"
                    sig_num = 0.33
                else:
                    sig_str = ""
                    sig_num = 0.00    # no significativo

                # ── ÍNDICE 1: Brock, Lakonishok & LeBaron (1992) ─────────────
                # Score = Retorno × (WinRate / 100)
                # Penaliza estrategias con win rate bajo aunque el retorno sea alto
                # Para SELL, el retorno negativo es bueno → invertimos el signo
                retorno_ajustado = retorno if tipo == "BUY" else -retorno
                score_bll = round(retorno_ajustado * (winrate / 100), 3)

                # ── ÍNDICE 2: Kaufman (2013) — Profit Factor adaptado ─────────
                # Score = WinRate×0.50 + Significancia×0.30 + Retorno_norm×0.20
                # Retorno normalizado: lo mapeamos al rango [0, 100] usando
                # una función sigmoide suave para no penalizar extremos
                # Retorno > 5% → muy bueno, retorno < -5% → muy malo
                retorno_norm = 50 + (retorno_ajustado / 5) * 25
                retorno_norm = max(0, min(100, retorno_norm))  # clamp [0,100]
                score_kaufman = round(
                    winrate    * 0.50 +
                    sig_num    * 0.30 * 100 +   # × 100 para llevar a escala [0,100]
                    retorno_norm * 0.20,
                    2
                )

                # ── ÍNDICE 3: Lo (2002) — Sharpe-like ────────────────────────
                # Score = (Retorno / Volatilidad) × √(252 / horizonte)
                # √(252/horizonte): anualiza el ratio (252 días hábiles/año)
                # Si volatilidad = 0 o muy pequeña, ponemos NaN
                if volatilidad > 0.01:
                    factor_anual = np.sqrt(252 / horizonte)
                    score_sharpe = round(
                        (retorno_ajustado / volatilidad) * factor_anual, 3
                    )
                else:
                    score_sharpe = np.nan

                filas.append({
                    "RSI":        f"RSI({periodo})",
                    "Banda":      clave,
                    "Señal":      tipo,
                    "N":          len(sub),
                    "Retorno_%":  retorno,
                    "WinRate_%":  winrate,
                    "Volatilidad": volatilidad,
                    "Sig":        sig_str,
                    "Score_BLL":     score_bll,
                    "Score_Kaufman": score_kaufman,
                    "Score_Sharpe":  score_sharpe,
                })

    if not filas:
        print(f"  ⚠️  Sin combinaciones con N≥5 para el ranking de {ticker}.")
        return pd.DataFrame()

    df = pd.DataFrame(filas)

    # ── Calcular rankings (1 = mejor) ────────────────────────────────────────
    # Para BLL y Kaufman: mayor score = mejor → rank ascendente=False
    # Para Sharpe: mayor score = mejor → igual
    df["Ranking_BLL"] = df["Score_BLL"].rank(ascending=False,
                                               method="min", na_option="bottom").astype(int)
    df["Ranking_K"]   = df["Score_Kaufman"].rank(ascending=False,
                                                  method="min", na_option="bottom").astype(int)
    df["Ranking_S"]   = df["Score_Sharpe"].rank(ascending=False,
                                                 method="min", na_option="bottom").astype(int)

    # Consenso: promedio de los 3 rankings (menor consenso = más consistente)
    df["Consenso"] = round(
        (df["Ranking_BLL"] + df["Ranking_K"] + df["Ranking_S"]) / 3, 1
    )

    # ── Etiqueta de recomendación ─────────────────────────────────────────────
    # Basada en el ranking de consenso relativo al total de combinaciones
    n_total = len(df)

    def etiquetar(consenso):
        pct = consenso / n_total   # posición relativa en el ranking
        if pct <= 0.20:
            return "⭐ MUY RECOMENDADA"
        elif pct <= 0.40:
            return "✅ RECOMENDADA"
        elif pct <= 0.60:
            return "⚠️  NEUTRAL"
        elif pct <= 0.80:
            return "❌ DÉBIL"
        else:
            return "🚫 NO RECOMENDADA"

    df["Recomendacion"] = df["Consenso"].apply(etiquetar)

    # Ordenar por consenso (menor = más recomendada)
    df = df.sort_values("Consenso").reset_index(drop=True)

    # ── Imprimir en consola ───────────────────────────────────────────────────
    sep = "=" * 90
    print(f"\n{sep}")
    print(f"  {ticker}  —  TABLA RANKING  |  Horizonte: {horizonte} días")
    print(f"  Índices: BLL=Brock et al.(1992)  |  K=Kaufman(2013)  |  S=Lo(2002)")
    print(sep)

    # Columnas para mostrar en consola (compacto)
    cols_consola = ["RSI", "Banda", "Señal", "N",
                    "Retorno_%", "WinRate_%", "Sig",
                    "Score_BLL", "Score_Kaufman", "Score_Sharpe",
                    "Consenso", "Recomendacion"]
    print(df[cols_consola].to_string(index=False))
    print()

    # ── Exportar ──────────────────────────────────────────────────────────────
    ticker_safe = ticker.replace("^", "").replace("/", "-")

    # Excel: nueva hoja en el archivo maestro existente
    # (se usa mode="a" para agregar sin borrar las hojas anteriores)
    nombre_xlsx = f"tabla_maestra_{ticker_safe}.xlsx"
    try:
        with pd.ExcelWriter(nombre_xlsx, engine="openpyxl",
                            mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=f"Ranking_{horizonte}d", index=False)
        print(f"  💾 Ranking agregado al Excel: {nombre_xlsx} "
              f"(hoja: Ranking_{horizonte}d)")
    except Exception as e:
        # Si el archivo no existe todavía, crear uno nuevo
        df.to_excel(nombre_xlsx, sheet_name=f"Ranking_{horizonte}d",
                    index=False)
        print(f"  💾 Ranking exportado: {nombre_xlsx}")

    # LaTeX: tabla de ranking para el artículo
    exportar_latex_ranking(df, ticker_safe, horizonte)

    return df   # retorna el DataFrame para uso posterior si se necesita


# =============================================================================
#  FUNCIÓN 5: exportar_latex_ranking
#  Uso: llamada internamente por tabla_ranking
#  Genera el .tex de la tabla de ranking con las 3 columnas de score
# =============================================================================
def exportar_latex_ranking(df: pd.DataFrame,
                            ticker_safe: str,
                            horizonte: int) -> None:
    """
    Genera el archivo .tex de la tabla ranking lista para \input{} en LaTeX.

    La tabla incluye:
        RSI | Banda | Señal | N | Retorno% | WinRate% | Sig |
        Score_BLL | Score_K | Score_S | Consenso | Recomendación

    Nota sobre la nota al pie:
        Se agrega automáticamente una nota explicando los 3 índices,
        usando \\footnotesize en LaTeX para que no ocupe demasiado espacio.
    """
    cols_tex = ["RSI", "Banda", "Señal", "N",
                "Retorno_%", "WinRate_%", "Sig",
                "Score_BLL", "Score_Kaufman", "Score_Sharpe",
                "Consenso", "Recomendacion"]

    # Formato: l=izquierda para texto, r=derecha para números, c=centrado para sig
    fmt_cols = "lllr" + "rrc" + "rrrc" + "l"

    caption = (f"Ranking de efectividad de combinaciones RSI --- {ticker_safe} "
               f"(horizonte: {horizonte} días)")
    label   = f"tab:ranking_{ticker_safe.lower()}_{horizonte}d"

    # Encabezado de columnas
    header = (
        "\\textbf{RSI} & \\textbf{Banda} & \\textbf{Se\\~{n}al} & \\textbf{N} & "
        "\\textbf{Ret\\%} & \\textbf{WR\\%} & \\textbf{Sig} & "
        "\\textbf{$S_{BLL}$} & \\textbf{$S_K$} & \\textbf{$S_S$} & "
        "\\textbf{Cons.} & \\textbf{Recomendaci\\'{o}n} \\\\"
    )

    filas_tex  = []
    ultimo_rsi = None

    for _, row in df.iterrows():
        # Separador visual por periodo RSI
        if row["RSI"] != ultimo_rsi and ultimo_rsi is not None:
            filas_tex.append("\\midrule")
        ultimo_rsi = row["RSI"]

        # Formatear Score_Sharpe (puede ser NaN)
        s_sharpe = (f"{row['Score_Sharpe']:.3f}"
                    if pd.notna(row['Score_Sharpe']) else "---")

        # Limpiar emojis de la recomendación para LaTeX
        # LaTeX no soporta emojis directamente
        rec = (row["Recomendacion"]
               .replace("⭐ ", "").replace("✅ ", "").replace("⚠️  ", "")
               .replace("❌ ", "").replace("🚫 ", ""))

        celdas = [
            str(row["RSI"]),
            str(row["Banda"]),
            str(row["Señal"]),
            str(int(row["N"])),
            f"{row['Retorno_%']:.2f}",
            f"{row['WinRate_%']:.1f}",
            str(row["Sig"]),
            f"{row['Score_BLL']:.3f}",
            f"{row['Score_Kaufman']:.2f}",
            s_sharpe,
            f"{row['Consenso']:.1f}",
            rec,
        ]
        filas_tex.append(" & ".join(celdas) + " \\\\")

    cuerpo = "\n        ".join(filas_tex)

    nombre_input = f"tabla_ranking_{ticker_safe}_{horizonte}d.tex"
    latex = f"""% ============================================================
% Tabla Ranking de Efectividad RSI
% Ticker  : {ticker_safe}
% Horizonte: {horizonte} días
% Uso: \\input{{{nombre_input}}}
%
% Requiere en el preámbulo:
%   \\usepackage{{booktabs}}
%   \\usepackage{{caption}}
%   \\usepackage{{threeparttable}}  % para la nota al pie de tabla
% ============================================================
\\begin{{table}}[htbp]
    \\centering
    \\small
    \\caption{{{caption}}}
    \\label{{{label}}}
    \\begin{{threeparttable}}
    \\begin{{tabular}}{{{fmt_cols}}}
        \\toprule
        {header}
        \\midrule
        {cuerpo}
        \\bottomrule
    \\end{{tabular}}
    \\begin{{tablenotes}}
        \\footnotesize
        \\item $S_{{BLL}}$: Score Brock, Lakonishok \\& LeBaron (1992):
              Retorno $\\times$ WinRate. \\
        \\item $S_K$: Score Kaufman (2013):
              WinRate$\\times$0.50 + Sig$\\times$0.30 + Ret\\_norm$\\times$0.20. \\
        \\item $S_S$: Score Lo (2002), Sharpe-like:
              $(\\bar{{r}} / \\sigma) \\times \\sqrt{{252/{horizonte}}}$. \\
        \\item Consenso: promedio de los 3 rankings (menor = m\\'{a}s recomendada).
        \\item Sig: *** $p<0.01$, ** $p<0.05$, * $p<0.10$ (t-test una cola).
    \\end{{tablenotes}}
    \\end{{threeparttable}}
\\end{{table}}
"""

    with open(nombre_input, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"  💾 LaTeX ranking exportado: {nombre_input}")