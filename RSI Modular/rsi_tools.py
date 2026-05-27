# =============================================================================
#  rsi_tools.py  —  Caja de herramientas RSI
# =============================================================================
#
#  Este archivo contiene SOLO funciones — no hace nada por sí solo.
#  Lo importas desde cualquier notebook o script con:
#
#      from rsi_tools import descargar_datos, calcular_rsi, detectar_senales
#
#  Así no tienes que copiar el código cada vez; solo llamas la función.
#
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
from matplotlib.lines import Line2D


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 1: descargar_datos
# ─────────────────────────────────────────────────────────────────────────────
def descargar_datos(ticker: str, años: int = 2) -> pd.DataFrame:
    """
    Descarga precios históricos de Yahoo Finance.

    Parámetros
    ----------
    ticker : str   Símbolo del activo, ej. "^GSPC", "SPY", "AAPL"
    años   : int   Cuántos años hacia atrás descargar (por defecto 2)

    Retorna
    -------
    pd.DataFrame con columnas Open, High, Low, Close, Volume
    El índice es la fecha (DatetimeIndex).
    """
    try:
        import yfinance as yf
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "yfinance", "-q"])
        import yfinance as yf

    fecha_fin    = pd.Timestamp.today()
    fecha_inicio = fecha_fin - pd.DateOffset(years=años)

    print(f"📥 Descargando {ticker}  ({fecha_inicio.date()} → {fecha_fin.date()})...")
    datos = yf.download(ticker, start=fecha_inicio, end=fecha_fin, progress=False)

    # Aplanar MultiIndex si yfinance lo genera (ocurre en algunas versiones)
    if isinstance(datos.columns, pd.MultiIndex):
        datos.columns = datos.columns.get_level_values(0)

    df = datos[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    print(f"✅ {len(df)} días descargados.\n")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 2: calcular_rsi
# ─────────────────────────────────────────────────────────────────────────────
def calcular_rsi(serie_precios: pd.Series, periodo: int) -> pd.Series:
    """
    Calcula el RSI (Relative Strength Index) con suavizado de Wilder.

    Fórmula:
        RSI = 100 - 100 / (1 + RS)
        RS  = promedio_ganancias / promedio_pérdidas

    El "suavizado de Wilder" usa una media móvil exponencial con
    com = periodo - 1, que es equivalente al método original de Wilder.

    Parámetros
    ----------
    serie_precios : pd.Series  Precios de cierre
    periodo       : int        Número de períodos (14 es el estándar)

    Retorna
    -------
    pd.Series con valores RSI entre 0 y 100.
    Los primeros `periodo` valores serán NaN (sin suficiente historia).
    """
    delta     = serie_precios.diff()                          # cambio diario
    ganancias = delta.clip(lower=0)                           # solo positivos
    perdidas  = (-delta).clip(lower=0)                        # solo negativos → positivos

    # ewm = Exponential Weighted Mean  |  com = center of mass = periodo - 1
    prom_gan = ganancias.ewm(com=periodo - 1, min_periods=periodo).mean()
    prom_per = perdidas.ewm(com=periodo - 1, min_periods=periodo).mean()

    rs  = prom_gan / prom_per.replace(0, np.nan)   # evita división por cero
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 3: detectar_senales
# ─────────────────────────────────────────────────────────────────────────────
def detectar_senales(rsi: pd.Series,
                     sobreventa: float,
                     sobrecompra: float) -> pd.Series:
    """
    Detecta señales BUY/SELL usando CRUCES del RSI (no niveles).

    ¿Por qué cruces y no niveles?
        Si usamos "RSI < 30 → BUY", obtenemos señal cada día que el RSI
        esté bajo 30, generando decenas de señales seguidas.
        Con cruces, solo se activa el día exacto en que el RSI SALE
        de la zona extrema → una sola señal limpia por episodio.

    Señal BUY  (+1): ayer RSI <= sobreventa  Y  hoy RSI > sobreventa
    Señal SELL (-1): ayer RSI >= sobrecompra Y  hoy RSI < sobrecompra
    Sin señal  ( 0): ningún cruce

    Parámetros
    ----------
    rsi         : pd.Series  Valores del RSI
    sobreventa  : float      Umbral inferior (ej. 30)
    sobrecompra : float      Umbral superior (ej. 70)

    Retorna
    -------
    pd.Series de enteros {-1, 0, +1} con el mismo índice que rsi.
    """
    senales  = pd.Series(0, index=rsi.index, dtype=int)
    rsi_ayer = rsi.shift(1)   # desplaza 1 día → compara hoy con ayer

    # BUY: salida de zona de sobreventa (RSI cruza hacia arriba)
    mask_buy = (
        rsi_ayer.notna() & rsi.notna() &
        (rsi_ayer <= sobreventa) & (rsi > sobreventa)
    )
    # SELL: salida de zona de sobrecompra (RSI cruza hacia abajo)
    mask_sell = (
        rsi_ayer.notna() & rsi.notna() &
        (rsi_ayer >= sobrecompra) & (rsi < sobrecompra)
    )

    senales[mask_buy]  =  1
    senales[mask_sell] = -1
    return senales


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 4: calcular_rendimientos_futuros
# ─────────────────────────────────────────────────────────────────────────────
def calcular_rendimientos_futuros(cierre: pd.Series,
                                   senales: pd.Series,
                                   dias_futuro: list) -> pd.DataFrame:
    """
    Para cada señal, calcula el rendimiento % a N días después.

    Convención de retornos:
        BUY : retorno positivo = precio subió  ✅
        SELL: retorno positivo = precio bajó   ✅ (signo invertido)
        → En ambos casos, positivo = operación ganadora.

    Usa índices numéricos (posición en el array) para contar días de
    TRADING, no días calendario. Así +10 días = 10 sesiones bursátiles.

    Parámetros
    ----------
    cierre      : pd.Series  Precios de cierre
    senales     : pd.Series  Serie {-1, 0, +1} de señales
    dias_futuro : list       Horizontes a evaluar, ej. [1, 3, 5, 10, 30]

    Retorna
    -------
    pd.DataFrame con columnas: fecha, signal, ret_1d, ret_3d, ...
    Siempre tiene las columnas correctas aunque no haya señales.
    """
    registros = []
    precios   = cierre.values
    fechas    = cierre.index.tolist()
    mapa_idx  = {f: i for i, f in enumerate(fechas)}  # fecha → posición

    for fecha, senal in senales.items():
        if senal == 0:
            continue

        i0 = mapa_idx.get(fecha)
        if i0 is None:
            continue

        p0       = precios[i0]
        registro = {"fecha": fecha, "signal": "BUY" if senal == 1 else "SELL"}

        for n in dias_futuro:
            i1 = i0 + n
            if i1 < len(precios):
                ret_bruto = (precios[i1] - p0) / p0 * 100
                # BUY → positivo si sube | SELL → positivo si baja
                registro[f"ret_{n}d"] = ret_bruto if senal == 1 else -ret_bruto
            else:
                registro[f"ret_{n}d"] = np.nan   # señal muy reciente, sin datos

        registros.append(registro)

    # Esquema de columnas garantizado aunque no haya registros
    cols = ["fecha", "signal"] + [f"ret_{n}d" for n in dias_futuro]
    if not registros:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(registros, columns=cols)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 5: tabla_estadisticas
# ─────────────────────────────────────────────────────────────────────────────
def tabla_estadisticas(df_rend: pd.DataFrame,
                        dias_futuro: list) -> pd.DataFrame:
    """
    Calcula retorno promedio y Win Rate para BUY y SELL.

    Win Rate = porcentaje de señales con retorno positivo.
    Media%   = promedio de todos los retornos.

    Parámetros
    ----------
    df_rend     : pd.DataFrame  Salida de calcular_rendimientos_futuros
    dias_futuro : list          Misma lista usada al calcular retornos

    Retorna
    -------
    pd.DataFrame con filas BUY/SELL y columnas Media_Nd / WinRate_Nd
    """
    if df_rend.empty or "signal" not in df_rend.columns:
        return pd.DataFrame()

    filas = []
    for tipo in ["BUY", "SELL"]:
        sub = df_rend[df_rend["signal"] == tipo]
        if sub.empty:
            continue
        fila = {"Señal": tipo, "N": len(sub)}
        for n in dias_futuro:
            col = f"ret_{n}d"
            vals = sub[col].dropna()
            fila[f"Media_{n}d%"]   = round(vals.mean(), 2)   if len(vals) else np.nan
            fila[f"WinRate_{n}d%"] = round((vals > 0).mean() * 100, 1) if len(vals) else np.nan
        filas.append(fila)

    return pd.DataFrame(filas).set_index("Señal")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN 6: graficar_rsi
# ─────────────────────────────────────────────────────────────────────────────
def graficar_rsi(df: pd.DataFrame,
                 rsi: pd.Series,
                 senales: pd.Series,
                 periodo: int,
                 sobreventa: float,
                 sobrecompra: float,
                 guardar: bool = True) -> None:
    """
    Gráfico de 2 paneles: precio arriba, RSI abajo, señales marcadas.

    Los triángulos ▲ (BUY) y ▼ (SELL) aparecen en el día exacto del
    cruce, tanto en el panel de precio como en el del RSI.

    Parámetros
    ----------
    df          : pd.DataFrame  Datos OHLCV (necesita columna 'Close')
    rsi         : pd.Series     Valores del RSI
    senales     : pd.Series     Serie {-1, 0, +1}
    periodo     : int           Período del RSI (para el título)
    sobreventa  : float         Umbral inferior
    sobrecompra : float         Umbral superior
    guardar     : bool          Si True, guarda la imagen como .png
    """
    # Paleta de colores
    C_BUY   = "#00C853"   # verde
    C_SELL  = "#D50000"   # rojo
    C_PX    = "#1565C0"   # azul → precio
    C_RSI   = "#6A1B9A"   # púrpura → RSI
    C_OB    = "#FF6F00"   # naranja → sobrecompra
    C_OS    = "#00838F"   # teal → sobreventa
    C_BG    = "#F8F9FA"   # fondo
    C_GRID  = "#DEE2E6"   # grilla

    fechas_buy  = senales[senales ==  1].index
    fechas_sell = senales[senales == -1].index

    fig = plt.figure(figsize=(16, 9), facecolor=C_BG)
    fig.suptitle(
        f"S&P 500  |  RSI({periodo})  |  "
        f"Sobreventa ≤{sobreventa}  |  Sobrecompra ≥{sobrecompra}",
        fontsize=14, fontweight="bold", y=0.98, color="#212529"
    )

    # GridSpec: 2 filas, altura 2.5:1 (precio más grande que RSI)
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.06)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)  # mismo eje X que ax1

    # ── Panel 1: PRECIO ───────────────────────────────────────────────────────
    ax1.set_facecolor(C_BG)
    ax1.plot(df.index, df["Close"], color=C_PX, linewidth=1.3,
             label="Precio Cierre", zorder=2)

    for f in fechas_buy:
        if f in df.index:
            ax1.axvline(f, color=C_BUY, alpha=0.18, linewidth=0.8, zorder=1)
            ax1.scatter(f, df.loc[f, "Close"], color=C_BUY, marker="^",
                        s=70, zorder=5, edgecolors="white", linewidths=0.5)

    for f in fechas_sell:
        if f in df.index:
            ax1.axvline(f, color=C_SELL, alpha=0.18, linewidth=0.8, zorder=1)
            ax1.scatter(f, df.loc[f, "Close"], color=C_SELL, marker="v",
                        s=70, zorder=5, edgecolors="white", linewidths=0.5)

    leyenda = [
        Line2D([0],[0], color=C_PX, lw=1.8, label="Precio Cierre"),
        Line2D([0],[0], marker="^", color="w", markerfacecolor=C_BUY,
               ms=10, label=f"BUY — {len(fechas_buy)} señales"),
        Line2D([0],[0], marker="v", color="w", markerfacecolor=C_SELL,
               ms=10, label=f"SELL — {len(fechas_sell)} señales"),
    ]
    ax1.legend(handles=leyenda, loc="upper left", fontsize=9,
               framealpha=0.88, edgecolor=C_GRID)
    ax1.set_ylabel("Precio (USD)", fontsize=10)
    ax1.tick_params(labelbottom=False)
    ax1.grid(True, color=C_GRID, linewidth=0.6, linestyle="--", zorder=0)
    ax1.spines[["top","right"]].set_visible(False)

    # ── Panel 2: RSI ──────────────────────────────────────────────────────────
    ax2.set_facecolor(C_BG)
    ax2.plot(rsi.index, rsi.values, color=C_RSI, linewidth=1.0,
             label=f"RSI({periodo})", zorder=3)

    ax2.axhspan(sobrecompra, 100,       alpha=0.10, color=C_OB,
                label=f"Sobrecompra ≥{sobrecompra}")
    ax2.axhspan(0,           sobreventa, alpha=0.10, color=C_OS,
                label=f"Sobreventa ≤{sobreventa}")
    ax2.axhline(sobrecompra, color=C_OB, lw=1.1, linestyle="--", alpha=0.85)
    ax2.axhline(sobreventa,  color=C_OS, lw=1.1, linestyle="--", alpha=0.85)
    ax2.axhline(50, color="#ADB5BD", lw=0.7, linestyle=":")

    for f in fechas_buy:
        if f in rsi.index and pd.notna(rsi.loc[f]):
            ax2.scatter(f, rsi.loc[f], color=C_BUY, marker="^",
                        s=55, zorder=5, edgecolors="white", linewidths=0.5)

    for f in fechas_sell:
        if f in rsi.index and pd.notna(rsi.loc[f]):
            ax2.scatter(f, rsi.loc[f], color=C_SELL, marker="v",
                        s=55, zorder=5, edgecolors="white", linewidths=0.5)

    ax2.set_ylim(0, 100)
    ax2.set_ylabel(f"RSI({periodo})", fontsize=10)
    ax2.set_xlabel("Fecha", fontsize=10)
    ax2.grid(True, color=C_GRID, linewidth=0.6, linestyle="--", zorder=0)
    ax2.spines[["top","right"]].set_visible(False)
    ax2.legend(loc="upper left", fontsize=8, framealpha=0.88, edgecolor=C_GRID)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    if guardar:
        nombre = f"RSI{periodo}_{int(sobreventa)}-{int(sobrecompra)}_SP500.png"
        plt.savefig(nombre, dpi=150, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Gráfica guardada: {nombre}")

    plt.show()
