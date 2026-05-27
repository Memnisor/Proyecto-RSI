# =============================================================================
#  fn_grafica.py
#  FUNCIONES: graficar_rsi, graficar_heatmap, graficar_retorno_horizonte
# =============================================================================
#
#  FIXES aplicados en esta versión:
#
#  1. plt.close(fig) al final de cada función
#     → evita acumulación de figuras en memoria (warning "more than 20 figures")
#     → Spyder ya no acumula ventanas abiertas entre mercados
#
#  2. constrained_layout=True en graficar_rsi (reemplaza plt.tight_layout)
#     → compatible con GridSpecFromSubplotSpec anidado
#     → elimina el UserWarning "Axes not compatible with tight_layout"
#
#  3. graficar_retorno_horizonte: leyenda solo si hay líneas
#     → elimina el UserWarning "No artists with labels found"
#     → ocurre cuando un mercado solo tiene señales de un tipo (BUY o SELL)
#
#  4. graficar_retorno_horizonte: subplot vacío muestra aviso en lugar de
#     ejes en blanco con línea de referencia sola
#
# =============================================================================

import itertools

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates  as mdates
from matplotlib.lines import Line2D


# ── Paleta compartida ─────────────────────────────────────────────────────────
C_BUY  = "#00C853"
C_SELL = "#D50000"
C_PX   = "#1565C0"
C_RSI  = "#6A1B9A"
C_OB   = "#FF6F00"
C_OS   = "#00838F"
C_BG   = "#F8F9FA"
C_GRID = "#DEE2E6"
C_MA   = "#F57F17"   # color de la media móvil del RSI


def graficar_rsi(df: pd.DataFrame,
                 combinaciones: list,
                 guardar: bool = True,
                 ticker: str = "") -> None:
    """
    Genera UNA figura con subplots para TODAS las combinaciones del mercado.

    Diseño de la grilla:
      • Cada celda tiene 2 mini-paneles apilados: precio arriba, RSI abajo.
      • Filas = periodos RSI, Columnas = bandas.
      • La figura crece automáticamente con más periodos o bandas.

    Fix tight_layout:
      Se usa constrained_layout=True en lugar de plt.tight_layout().
      tight_layout no es compatible con GridSpecFromSubplotSpec anidado
      y lanza UserWarning. constrained_layout sí lo es.

    Parámetros
    ----------
    df            : pd.DataFrame  Datos OHLCV con columna 'Close'
    combinaciones : list          Lista de tuplas:
                                  (rsi, senales, ma_rsi, periodo, sv, sc)
    guardar       : bool          Si True guarda como .png
    ticker        : str           Nombre del activo para el título y el archivo
    """
    if not combinaciones:
        print("  Sin combinaciones para graficar.")
        return

    # ── Detectar periodos y bandas únicos (orden de inserción) ───────────────
    periodos_vistos = []
    bandas_vistas   = []
    for _, _, _, periodo, sv, sc in combinaciones:
        if periodo not in periodos_vistos:
            periodos_vistos.append(periodo)
        banda = (sv, sc)
        if banda not in bandas_vistas:
            bandas_vistas.append(banda)

    n_filas = len(periodos_vistos)
    n_cols  = len(bandas_vistas)

    alto_fig  = n_filas * 4.5
    ancho_fig = n_cols  * 5.5

    # constrained_layout=True: compatible con GridSpecFromSubplotSpec anidado
    # Reemplaza plt.tight_layout() que generaba UserWarning
    fig = plt.figure(figsize=(ancho_fig, alto_fig),
                     facecolor=C_BG,
                     constrained_layout=True)
    fig.suptitle(
        f"{ticker}  —  Señales RSI por periodo y banda",
        fontsize=13, fontweight="bold", color="#212529"
    )

    outer = gridspec.GridSpec(
        n_filas, n_cols,
        figure=fig,
        hspace=0.55,
        wspace=0.35
    )

    # Índice rápido: (periodo, banda) → tupla
    idx = {}
    for combo in combinaciones:
        rsi, senales, ma_rsi, periodo, sv, sc = combo
        idx[(periodo, (sv, sc))] = combo

    for i, periodo in enumerate(periodos_vistos):
        for j, banda in enumerate(bandas_vistas):
            sv, sc = banda
            clave  = (periodo, banda)

            inner = gridspec.GridSpecFromSubplotSpec(
                2, 1,
                subplot_spec=outer[i, j],
                height_ratios=[2.5, 1],
                hspace=0.05
            )
            ax_px  = fig.add_subplot(inner[0])
            ax_rsi = fig.add_subplot(inner[1], sharex=ax_px)

            ax_px.set_title(
                f"RSI({periodo})  |  {sv}/{sc}",
                fontsize=8, pad=3, color="#343A40"
            )

            if clave not in idx:
                ax_px.text(0.5, 0.5, "sin señales",
                           ha="center", va="center",
                           transform=ax_px.transAxes,
                           fontsize=8, color="gray")
                ax_rsi.set_visible(False)
                continue

            rsi, senales, ma_rsi, _, _, _ = idx[clave]
            fechas_buy  = senales[senales ==  1].index
            fechas_sell = senales[senales == -1].index

            # ── Mini-panel: precio ────────────────────────────────────────────
            ax_px.set_facecolor(C_BG)
            ax_px.plot(df.index, df["Close"],
                       color=C_PX, linewidth=0.8, zorder=2)

            for f in fechas_buy:
                if f in df.index:
                    ax_px.scatter(f, df.loc[f, "Close"],
                                  color=C_BUY, marker="^", s=25, zorder=5,
                                  edgecolors="white", linewidths=0.3)
            for f in fechas_sell:
                if f in df.index:
                    ax_px.scatter(f, df.loc[f, "Close"],
                                  color=C_SELL, marker="v", s=25, zorder=5,
                                  edgecolors="white", linewidths=0.3)

            ax_px.tick_params(labelbottom=False, labelsize=6)
            ax_px.set_ylabel("Precio", fontsize=6)
            ax_px.grid(True, color=C_GRID, linewidth=0.4, linestyle="--")
            ax_px.spines[["top","right"]].set_visible(False)

            ax_px.legend(
                handles=[
                    Line2D([0],[0], marker="^", color="w",
                           markerfacecolor=C_BUY, ms=6,
                           label=f"B:{len(fechas_buy)}"),
                    Line2D([0],[0], marker="v", color="w",
                           markerfacecolor=C_SELL, ms=6,
                           label=f"S:{len(fechas_sell)}"),
                ],
                loc="upper left", fontsize=6,
                framealpha=0.7, edgecolor=C_GRID,
                handletextpad=0.2, borderpad=0.3
            )

            # ── Mini-panel: RSI ───────────────────────────────────────────────
            ax_rsi.set_facecolor(C_BG)
            ax_rsi.plot(rsi.index, rsi.values,
                        color=C_RSI, linewidth=0.7, zorder=3)

            if ma_rsi is not None and not ma_rsi.dropna().empty:
                ax_rsi.plot(ma_rsi.index, ma_rsi.values,
                            color=C_MA, linewidth=0.7,
                            linestyle="--", alpha=0.8, zorder=3)

            ax_rsi.axhspan(sc,  100, alpha=0.10, color=C_OB)
            ax_rsi.axhspan(0,   sv,  alpha=0.10, color=C_OS)
            ax_rsi.axhline(sc, color=C_OB, lw=0.7, linestyle="--", alpha=0.7)
            ax_rsi.axhline(sv, color=C_OS, lw=0.7, linestyle="--", alpha=0.7)
            ax_rsi.axhline(50, color="#ADB5BD", lw=0.5, linestyle=":")

            for f in fechas_buy:
                if f in rsi.index and pd.notna(rsi.loc[f]):
                    ax_rsi.scatter(f, rsi.loc[f],
                                   color=C_BUY, marker="^", s=18, zorder=5,
                                   edgecolors="white", linewidths=0.3)
            for f in fechas_sell:
                if f in rsi.index and pd.notna(rsi.loc[f]):
                    ax_rsi.scatter(f, rsi.loc[f],
                                   color=C_SELL, marker="v", s=18, zorder=5,
                                   edgecolors="white", linewidths=0.3)

            ax_rsi.set_ylim(0, 100)
            ax_rsi.set_ylabel("RSI", fontsize=6)
            ax_rsi.tick_params(labelsize=6)
            ax_rsi.grid(True, color=C_GRID, linewidth=0.4, linestyle="--")
            ax_rsi.spines[["top","right"]].set_visible(False)

            if i == n_filas - 1:
                ax_rsi.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))
                ax_rsi.xaxis.set_major_locator(
                    mdates.MonthLocator(interval=max(1, n_cols * 2))
                )
                plt.setp(ax_rsi.xaxis.get_majorticklabels(),
                         rotation=30, ha="right", fontsize=6)
            else:
                ax_rsi.tick_params(labelbottom=False)

    # NO se llama plt.tight_layout() — constrained_layout ya lo maneja
    if guardar:
        # Sanitizar ticker: ^ y otros caracteres especiales no son válidos
        # en nombres de archivo en Windows (ej: ^GSPC → GSPC)
        ticker_safe = ticker.replace("^", "").replace("/", "-")
        nombre = f"RSI_senales_{ticker_safe}.png"
        plt.savefig(nombre, dpi=130, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Figura conjunta guardada: {nombre}")

    plt.show()
    plt.close(fig)   # libera memoria: evita el warning "more than 20 figures"


def graficar_heatmap(resultados: dict,
                     periodos: list,
                     bandas: list,
                     dias_futuro: list,
                     horizonte: int = 30,
                     ticker: str = "") -> None:
    """
    Mapa de calor: Win Rate a 'horizonte' días para cada combinación.
    Verde = bueno (≥60%), Rojo = malo (≤40%), Amarillo = neutro (≈50%).

    Filas = periodos RSI, Columnas = bandas.
    BUY y SELL en subplots separados lado a lado.
    """
    col = f"ret_{horizonte}d"

    fig, axes = plt.subplots(
        1, 2,
        figsize=(max(8, len(bandas) * 2.5), max(4, len(periodos) * 1.2)),
        facecolor=C_BG
    )
    fig.suptitle(
        f"{ticker}  —  Win Rate a {horizonte} días (%)\n"
        f"Verde ≥ 60%  |  Rojo ≤ 40%  |  Amarillo ≈ 50%",
        fontsize=11, fontweight="bold"
    )

    etiq_bandas   = [f"{sv}/{sc}" for sv, sc in bandas]
    etiq_periodos = [f"RSI({p})" for p in periodos]

    for ax, tipo in zip(axes, ["BUY", "SELL"]):
        matriz = np.full((len(periodos), len(bandas)), np.nan)

        for i, periodo in enumerate(periodos):
            for j, (sv, sc) in enumerate(bandas):
                clave = f"{sv}/{sc}"
                datos = resultados.get(periodo, {}).get(clave, {})
                tbl   = datos.get("tabla_rendimientos", pd.DataFrame())
                if tbl.empty or "signal" not in tbl.columns:
                    continue
                sub  = tbl[tbl["signal"] == tipo]
                vals = sub[col].dropna() if col in sub.columns else pd.Series()
                if len(vals) >= 3:
                    matriz[i, j] = round((vals > 0).mean() * 100, 1)

        im = ax.imshow(matriz, cmap="RdYlGn", vmin=30, vmax=70, aspect="auto")
        ax.set_xticks(range(len(bandas)))
        ax.set_yticks(range(len(periodos)))
        ax.set_xticklabels(etiq_bandas, fontsize=8)
        ax.set_yticklabels(etiq_periodos, fontsize=8)
        ax.set_title(f"Señal {tipo}", fontsize=10)

        for i in range(len(periodos)):
            for j in range(len(bandas)):
                v = matriz[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v:.0f}%",
                            ha="center", va="center",
                            fontsize=8, fontweight="bold",
                            color="black" if 35 < v < 65 else "white")
                else:
                    ax.text(j, i, "—", ha="center", va="center",
                            fontsize=8, color="gray")

        plt.colorbar(im, ax=ax, fraction=0.035, pad=0.04)

    plt.tight_layout()

    if ticker:
        ticker_safe = ticker.replace("^", "").replace("/", "-")
        nombre = f"heatmap_winrate_{ticker_safe}.png"
        plt.savefig(nombre, dpi=130, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Heatmap guardado: {nombre}")

    plt.show()
    plt.close(fig)   # libera memoria


def graficar_retorno_horizonte(resultados: dict,
                                periodos: list,
                                bandas: list,
                                dias_futuro: list,
                                ticker: str = "") -> None:
    """
    Retorno promedio (%) vs horizonte temporal para cada combinación.
    Permite ver si la estrategia mejora manteniéndola más días.

    Fix leyenda vacía:
      Se verifica si el subplot tiene líneas antes de llamar ax.legend().
      Cuando un mercado solo produce señales SELL (ej. GXG, EPU), el panel
      BUY queda vacío y legend() lanzaba UserWarning "No artists with labels".
      Ahora en ese caso se muestra un texto "sin señales suficientes".

    BUY y SELL en subplots separados.
    Cada línea = una combinación (periodo, banda).
    """
    fig, axes = plt.subplots(
        1, 2,
        figsize=(13, 5),
        facecolor=C_BG,
        sharey=False
    )
    fig.suptitle(
        f"{ticker}  —  Retorno promedio (%) por horizonte temporal",
        fontsize=11, fontweight="bold"
    )

    cmap   = plt.get_cmap("tab20")
    combos = list(itertools.product(periodos, bandas))

    for ax, tipo in zip(axes, ["BUY", "SELL"]):
        ax.set_facecolor(C_BG)
        ax.axhline(0, color="#ADB5BD", lw=0.9, linestyle="--")

        lineas_graficadas = 0   # contador para saber si el panel tiene datos

        for k, (periodo, (sv, sc)) in enumerate(combos):
            clave = f"{sv}/{sc}"
            datos = resultados.get(periodo, {}).get(clave, {})
            tbl   = datos.get("tabla_rendimientos", pd.DataFrame())
            if tbl.empty or "signal" not in tbl.columns:
                continue
            sub = tbl[tbl["signal"] == tipo]
            if len(sub) < 3:
                continue

            medias = []
            for n in dias_futuro:
                col  = f"ret_{n}d"
                vals = sub[col].dropna() if col in sub.columns else pd.Series()
                medias.append(vals.mean() if len(vals) >= 3 else np.nan)

            color = cmap(k % 20)
            ax.plot(dias_futuro, medias,
                    marker="o", markersize=4, linewidth=1.2,
                    color=color,
                    label=f"RSI({periodo}) {sv}/{sc}")
            lineas_graficadas += 1

        ax.set_title(f"Señal {tipo}", fontsize=10)
        ax.set_xlabel("Días hacia el futuro", fontsize=9)
        ax.set_ylabel("Retorno promedio (%)", fontsize=9)
        ax.grid(True, color=C_GRID, linewidth=0.5, linestyle="--")
        ax.spines[["top","right"]].set_visible(False)

        # Solo llamar legend() si hay líneas; si no, mostrar aviso de texto
        if lineas_graficadas > 0:
            ax.legend(fontsize=6, loc="best", framealpha=0.8, ncol=2)
        else:
            ax.text(0.5, 0.5, "sin señales suficientes\n(N < 3)",
                    ha="center", va="center",
                    transform=ax.transAxes,
                    fontsize=9, color="gray", style="italic")

    plt.tight_layout()

    if ticker:
        ticker_safe = ticker.replace("^", "").replace("/", "-")
        nombre = f"retorno_horizonte_{ticker_safe}.png"
        plt.savefig(nombre, dpi=130, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Gráfico horizonte guardado: {nombre}")

    plt.show()
    plt.close(fig)   # libera memoria