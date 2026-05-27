# =============================================================================
#  fn_grafica.py
#  FUNCIÓN: graficar_rsi
# =============================================================================
#
#  QUÉ HACE:
#    Genera un gráfico de 2 paneles:
#      • Panel superior: precio de cierre con triángulos de señal
#      • Panel inferior: línea del RSI con zonas sombreadas
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - Colores, tamaños, estilos de línea
#    - Agregar un tercer panel (ej. volumen)
#    - Agregar anotaciones de texto en cada señal
#    - Cambiar el formato de fecha del eje X
#    - Agregar media móvil al panel de precio
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: graficar_rsi
#    - Los parámetros obligatorios: (df, rsi, senales, periodo,
#                                    sobreventa, sobrecompra)
#    - La lógica de los triángulos (deben coincidir con los cruces)
#
# =============================================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
from matplotlib.lines import Line2D


def graficar_rsi(df: pd.DataFrame,
                 rsi: pd.Series,
                 senales: pd.Series,
                 periodo: int,
                 sobreventa: float,
                 sobrecompra: float,
                 guardar: bool = True) -> None:
    """
    Gráfico de 2 paneles: precio arriba, RSI abajo, señales marcadas.

    Los triángulos ▲ (BUY) y ▼ (SELL) aparecen exactamente en el día
    del cruce, tanto en el panel de precio como en el del RSI.

    ¿Por qué los triángulos deben coincidir visualmente?
    ─────────────────────────────────────────────────────
    BUY  → triángulo verde ▲ justo cuando el RSI sale de sobreventa
           (el día que cruza el umbral inferior hacia arriba)
    SELL → triángulo rojo  ▼ justo cuando el RSI sale de sobrecompra
           (el día que cruza el umbral superior hacia abajo)

    Si los triángulos aparecen DENTRO de las zonas sombreadas,
    significa que la lógica de señales tiene un bug.
    Si aparecen en el BORDE de las zonas, es correcto.

    Parámetros
    ----------
    df          : pd.DataFrame  Datos OHLCV (necesita columna 'Close')
    rsi         : pd.Series     Valores del RSI
    senales     : pd.Series     Serie {-1, 0, +1}
    periodo     : int           Período del RSI (para el título)
    sobreventa  : float         Umbral inferior de la banda
    sobrecompra : float         Umbral superior de la banda
    guardar     : bool          Si True, guarda imagen como .png
    """

    # ── Paleta de colores ─────────────────────────────────────────────────────
    # Puedes cambiar estos valores para personalizar la gráfica
    C_BUY   = "#00C853"   # verde brillante  → señales de compra
    C_SELL  = "#D50000"   # rojo             → señales de venta
    C_PX    = "#1565C0"   # azul oscuro      → línea de precio
    C_RSI   = "#6A1B9A"   # púrpura          → línea del RSI
    C_OB    = "#FF6F00"   # naranja          → zona sobrecompra
    C_OS    = "#00838F"   # teal             → zona sobreventa
    C_BG    = "#F8F9FA"   # gris muy claro   → fondo de la figura
    C_GRID  = "#DEE2E6"   # gris suave       → líneas de grilla

    # Fechas de cada tipo de señal
    fechas_buy  = senales[senales ==  1].index
    fechas_sell = senales[senales == -1].index

    # ── Crear figura ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 9), facecolor=C_BG)
    fig.suptitle(
        f"S&P 500  |  RSI({periodo})  |  "
        f"Sobreventa ≤{sobreventa}  |  Sobrecompra ≥{sobrecompra}",
        fontsize=14, fontweight="bold", y=0.98, color="#212529"
    )

    # GridSpec define el tamaño relativo de cada panel
    # [2.5, 1] → el panel de precio ocupa el 71% del alto total
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.06)
    ax1 = fig.add_subplot(gs[0])              # panel superior: precio
    ax2 = fig.add_subplot(gs[1], sharex=ax1)  # panel inferior: RSI
    # sharex=ax1 → ambos paneles comparten el mismo eje de fechas

    # ── PANEL SUPERIOR: PRECIO ────────────────────────────────────────────────
    ax1.set_facecolor(C_BG)

    # Línea de precio
    ax1.plot(df.index, df["Close"],
             color=C_PX, linewidth=1.3,
             label="Precio Cierre", zorder=2)

    # Triángulos y líneas verticales de señales BUY
    for f in fechas_buy:
        if f in df.index:
            # Línea vertical semitransparente (ayuda visual)
            ax1.axvline(f, color=C_BUY, alpha=0.18, linewidth=0.8, zorder=1)
            # Triángulo ▲ en el precio de ese día
            ax1.scatter(f, df.loc[f, "Close"],
                        color=C_BUY, marker="^", s=70, zorder=5,
                        edgecolors="white", linewidths=0.5)

    # Triángulos y líneas verticales de señales SELL
    for f in fechas_sell:
        if f in df.index:
            ax1.axvline(f, color=C_SELL, alpha=0.18, linewidth=0.8, zorder=1)
            ax1.scatter(f, df.loc[f, "Close"],
                        color=C_SELL, marker="v", s=70, zorder=5,
                        edgecolors="white", linewidths=0.5)

    # Leyenda personalizada
    leyenda = [
        Line2D([0],[0], color=C_PX, lw=1.8,
               label="Precio Cierre"),
        Line2D([0],[0], marker="^", color="w", markerfacecolor=C_BUY,
               ms=10, label=f"BUY  — {len(fechas_buy)} señales"),
        Line2D([0],[0], marker="v", color="w", markerfacecolor=C_SELL,
               ms=10, label=f"SELL — {len(fechas_sell)} señales"),
    ]
    ax1.legend(handles=leyenda, loc="upper left",
               fontsize=9, framealpha=0.88, edgecolor=C_GRID)
    ax1.set_ylabel("Precio (USD)", fontsize=10)
    ax1.tick_params(labelbottom=False)  # ocultar fechas (las muestra ax2)
    ax1.grid(True, color=C_GRID, linewidth=0.6, linestyle="--", zorder=0)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── PANEL INFERIOR: RSI ───────────────────────────────────────────────────
    ax2.set_facecolor(C_BG)

    # Línea del RSI
    ax2.plot(rsi.index, rsi.values,
             color=C_RSI, linewidth=1.0,
             label=f"RSI({periodo})", zorder=3)

    # Zonas sombreadas
    ax2.axhspan(sobrecompra, 100,        alpha=0.10, color=C_OB,
                label=f"Sobrecompra ≥{sobrecompra}")
    ax2.axhspan(0,           sobreventa, alpha=0.10, color=C_OS,
                label=f"Sobreventa ≤{sobreventa}")

    # Líneas de umbral punteadas
    ax2.axhline(sobrecompra, color=C_OB, lw=1.1, linestyle="--", alpha=0.85)
    ax2.axhline(sobreventa,  color=C_OS, lw=1.1, linestyle="--", alpha=0.85)
    ax2.axhline(50, color="#ADB5BD", lw=0.7, linestyle=":")  # zona neutra

    # Triángulos de señal en el RSI
    for f in fechas_buy:
        if f in rsi.index and pd.notna(rsi.loc[f]):
            ax2.scatter(f, rsi.loc[f],
                        color=C_BUY, marker="^", s=55, zorder=5,
                        edgecolors="white", linewidths=0.5)

    for f in fechas_sell:
        if f in rsi.index and pd.notna(rsi.loc[f]):
            ax2.scatter(f, rsi.loc[f],
                        color=C_SELL, marker="v", s=55, zorder=5,
                        edgecolors="white", linewidths=0.5)

    ax2.set_ylim(0, 100)
    ax2.set_ylabel(f"RSI({periodo})", fontsize=10)
    ax2.set_xlabel("Fecha", fontsize=10)
    ax2.grid(True, color=C_GRID, linewidth=0.6, linestyle="--", zorder=0)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.legend(loc="upper left", fontsize=8, framealpha=0.88, edgecolor=C_GRID)

    # Formato del eje de fechas
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(),
             rotation=30, ha="right", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    #plt.subplots_adjust(top=0.93, bottom=0.10, left=0.10, right=0.95, hspace=0.3)  Recomendacion de gemini para tener en cuenta.

    # Guardar imagen
    if guardar:
        nombre = f"RSI{periodo}_{int(sobreventa)}-{int(sobrecompra)}_SP500.png"
        plt.savefig(nombre, dpi=150, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Gráfica guardada: {nombre}")

    plt.show()
