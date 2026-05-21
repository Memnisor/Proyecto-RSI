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
import numpy as np


def graficar_rsi(df: pd.DataFrame,
                 rsi: pd.Series,
                 senales: pd.Series,
                 periodo: int,
                 sobreventa: float,
                 sobrecompra: float,
                 guardar: bool = True,
                 ma_rsi: pd.Series=None,
                 ticker= "") -> None:
    # ma_rsi es OPCIONAL (None por defecto).
    # Si se pasa, se dibuja como linea azul punteada sobre el RSI.
    # Si no se pasa, la grafica funciona exactamente igual que antes.
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
 guardar     : bool          Si True, guarda imagen como .png"""

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
    # fig = plt.figure(figsize=(16, 9), facecolor=C_BG)
    # plt.close("all")  # cierra figuras anteriores para liberar memoria
    fig = plt.figure(figsize=(16, 9), facecolor=C_BG)
    manager = plt.get_current_fig_manager()
    manager.window.showNormal()        # abre en ventana normal, no maximizada
    manager.window.resize(850, 500)    # ancho x alto en píxeles — ajusta a tu gusto
    fig.suptitle(
        f"{ticker} |  RSI({periodo})  |  "
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

    # Media Móvil del RSI — se dibuja solo si se proporcionó
    # Es una línea azul punteada más suave que la línea del RSI
    if ma_rsi is not None:
        ax2.plot(ma_rsi.index, ma_rsi.values,
                 color="#1565C0", linewidth=1.2, linestyle="--",
                 alpha=0.75, label=f"MA RSI", zorder=2)
        
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

    # Guardar imagen
    if guardar:
        nombre = f"RSI{periodo}_{int(sobreventa)}-{int(sobrecompra)}_{ticker}.png"
        plt.savefig(nombre, dpi=150, bbox_inches="tight", facecolor=C_BG)
        print(f"  💾 Gráfica guardada: {nombre}")

    plt.show(block = False)
    
def graficar_heatmap(resultados: dict,
                     periodos: list,
                     bandas: list,
                     dias_futuro: list,
                     horizonte: int = 30,
                     guardar: bool = True,
                     ticker = "") -> None:
    """
    Genera un mapa de calor (heatmap) del Win Rate.
 
    ¿Qué es un heatmap?
    ────────────────────
    Una tabla donde cada celda tiene un COLOR según su valor:
      Verde  → Win Rate alto  (>60%) — señal acertó frecuentemente
      Amarillo → neutro       (~50%) — similar al azar
      Rojo   → Win Rate bajo  (<40%) — señal erró frecuentemente
 
    Filas    = períodos del RSI (7, 14, 20...)
    Columnas = bandas (30/70, 20/80...)
    Valor    = % de señales ganadoras a N días
    """
 
    # ── Verificar que el horizonte pedido existe en los datos ─────────────────
    # Si pedimos Win Rate a 30 días pero no calculamos 30 días, usamos el último
    if horizonte not in dias_futuro:
        print(f"  Horizonte {horizonte}d no disponible. Usando {dias_futuro[-1]}d.")
        horizonte = dias_futuro[-1]   # dias_futuro[-1] = último elemento de la lista
 
    # ── Nombres de bandas para el eje X ───────────────────────────────────────
    # Convierte lista de tuplas [(30,70),(20,80)] en ["30/70","20/80"]
    # f"{sv}/{sc}" es un f-string que formatea los números como texto
    nombres_bandas = [f"{sv}/{sc}" for sv, sc in bandas]
 
    # ── Colores ───────────────────────────────────────────────────────────────
    C_BG   = "#F8F9FA"   # fondo gris claro
    C_BUY  = "#00C853"   # verde para título BUY
    C_SELL = "#D50000"   # rojo para título SELL
 
    # ── Crear figura con 2 paneles lado a lado ────────────────────────────────
    # plt.subplots(1, 2) → 1 fila, 2 columnas de subgráficos
    # figsize=(14, 6)    → ancho 14 pulgadas, alto 6 pulgadas
    fig, ejes = plt.subplots(1, 2, figsize=(14, 6), facecolor=C_BG)
 
    # fig.suptitle → título general de toda la figura (no de un panel)
    fig.suptitle(
        f"Mapa de Calor — Win Rate (%) a {horizonte} días\n"
        f"{ticker} — Estrategia RSI",
        fontsize=13, fontweight="bold", color="#212529"
    )
 
    # ── Bucle: un panel para BUY y otro para SELL ─────────────────────────────
    # enumerate(["BUY","SELL"]) → genera (0,"BUY") y (1,"SELL")
    # idx_ax = 0 → ejes[0] = panel izquierdo
    # idx_ax = 1 → ejes[1] = panel derecho
    for idx_ax, tipo_senal in enumerate(["BUY", "SELL"]):
        ax = ejes[idx_ax]          # seleccionamos el panel correspondiente
        ax.set_facecolor(C_BG)     # color de fondo del panel
 
        # ── Construir la matriz de Win Rates ──────────────────────────────────
        # matriz es una lista de listas: matriz[fila][columna]
        # fila    = índice del período RSI
        # columna = índice de la banda
        matriz = []
 
        for periodo in periodos:           # recorremos cada período RSI
            fila_valores = []              # lista de valores para esta fila
 
            for sv, sc in bandas:          # sv=sobreventa, sc=sobrecompra
                clave_banda = f"{sv}/{sc}" # construimos la clave "30/70" etc.
 
                try:
                    # Accedemos al DataFrame de rendimientos para esta combinación
                    tabla_rend = resultados[periodo][clave_banda]["tabla_rendimientos"]
 
                    # Si está vacío o no tiene columna "signal" → NaN (sin dato)
                    if tabla_rend.empty or "signal" not in tabla_rend.columns:
                        win_rate = np.nan
                    else:
                        col_ret = f"ret_{horizonte}d"   # columna de retorno, ej. "ret_30d"
 
                        # Filtramos solo las filas de BUY o SELL
                        sub = tabla_rend[tabla_rend["signal"] == tipo_senal]
 
                        if col_ret not in sub.columns or sub.empty:
                            win_rate = np.nan
                        else:
                            vals = sub[col_ret].dropna()   # quitamos NaN
                            # Win Rate = fracción de retornos positivos × 100
                            win_rate = (vals > 0).mean() * 100 if len(vals) > 0 else np.nan
 
                except KeyError:
                    # Si la clave no existe en el diccionario → NaN
                    win_rate = np.nan
 
                fila_valores.append(win_rate)   # agregamos el valor a la fila
            matriz.append(fila_valores)          # agregamos la fila a la matriz
 
        # ── Convertir a array numpy ───────────────────────────────────────────
        # np.array convierte la lista de listas en una matriz numérica
        # dtype=float → aseguramos que los valores sean decimales
        mat = np.array(matriz, dtype=float)
 
        # ── Dibujar el heatmap ────────────────────────────────────────────────
        # ax.imshow muestra la matriz como imagen con colores
        # cmap="RdYlGn" → paleta Rojo-Amarillo-Verde
        # vmin=30, vmax=70 → rojo en 30%, verde en 70%, amarillo en 50%
        # aspect="auto" → ajusta el tamaño de las celdas automáticamente
        im = ax.imshow(mat, cmap="RdYlGn", vmin=30, vmax=70, aspect="auto")
 
        # ── Etiquetas de los ejes ─────────────────────────────────────────────
        # set_xticks → posición de las marcas en eje X (0, 1, 2...)
        # set_xticklabels → texto de esas marcas ("30/70", "20/80"...)
        ax.set_xticks(range(len(bandas)))
        ax.set_xticklabels(nombres_bandas, fontsize=11)
        ax.set_yticks(range(len(periodos)))
        ax.set_yticklabels([f"RSI({p})" for p in periodos], fontsize=11)
 
        # Título del panel con color según tipo de señal
        color_titulo = C_BUY if tipo_senal == "BUY" else C_SELL
        ax.set_title(f"Señales {tipo_senal}",
                     fontsize=12, fontweight="bold",
                     color=color_titulo, pad=12)
 
        # ── Anotar valor numérico en cada celda ───────────────────────────────
        # enumerate anidado → recorre todas las combinaciones fila/columna
        for i in range(len(periodos)):
            for j in range(len(bandas)):
                val = mat[i, j]   # mat[fila, columna] → valor de esa celda
 
                # Si el valor existe lo formateamos, si no ponemos "N/A"
                texto = f"{val:.1f}%" if not np.isnan(val) else "N/A"
 
                # Color del texto: negro en zona media, blanco en extremos
                # para que sea legible sobre cualquier color de fondo
                color_texto = "black" if 38 < val < 65 else "white"
 
                # ax.text → escribe texto en coordenadas (j, i) del gráfico
                # ha="center" → centrado horizontal
                # va="center" → centrado vertical
                ax.text(j, i, texto,
                        ha="center", va="center",
                        fontsize=12, fontweight="bold",
                        color=color_texto)
 
        # Barra de color lateral que muestra la escala de colores
        # shrink=0.85 → la barra ocupa el 85% del alto del panel
        plt.colorbar(im, ax=ax, label="Win Rate (%)", shrink=0.85)
 
    plt.tight_layout()   # ajusta automáticamente los márgenes
 
    if guardar:
        nombre = f"RSI_Heatmap_WinRate{horizonte}d_{ticker}.png"
        # dpi=150 → resolución de la imagen (puntos por pulgada)
        # bbox_inches="tight" → recorta los bordes en blanco
        plt.savefig(nombre, dpi=150, bbox_inches="tight", facecolor=C_BG)
        print(f"  Heatmap guardado: {nombre}")
 
    plt.show(block=False)   # block=False → no bloquea el programa mientras se muestra
 
 
def graficar_retorno_horizonte(resultados: dict,
                                periodos: list,
                                bandas: list,
                                dias_futuro: list,
                                guardar: bool = True,
                                ticker="") -> None:
    """
    Gráfico de líneas: retorno promedio vs días después de la señal.
 
    ¿Cómo leerlo?
    ──────────────
    Eje X = días después de la señal (1, 3, 5, 10, 30, 60, 90)
    Eje Y = retorno promedio de todas las señales de ese período
    Cada línea = un período del RSI
 
    Si la línea SUBE de izquierda a derecha → mantener más tiempo es mejor
    Si la línea es PLANA o BAJA → no hay ventaja en esperar más
    """
 
    # ── Colores y estilos de línea ────────────────────────────────────────────
    # Un color y estilo diferente para cada período RSI
    C_BG   = "#F8F9FA"
    C_GRID = "#DEE2E6"
    C_BUY  = "#00C853"
    C_SELL = "#D50000"
 
    # Lista de colores — uno por período RSI
    colores = ["#1565C0", "#2E7D32", "#6A1B9A", "#E65100", "#B71C1C",
               "#00838F", "#FF6F00", "#4A148C"]
 
    # Lista de estilos de línea — uno por período RSI
    # "-" línea sólida | "--" guiones | "-." punto-guión | ":" punteada
    estilos = ["-", "--", "-.", ":", (0, (3, 1, 1, 1)), "-", "--", "-."]
 
    # ── Crear figura con 2 paneles: BUY y SELL ────────────────────────────────
    # sharey=False → cada panel tiene su propio eje Y (escala independiente)
    fig, ejes = plt.subplots(1, 2, figsize=(16, 6),
                              facecolor=C_BG, sharey=False)
    fig.suptitle(
        f"Retorno Promedio (%) por Horizonte Temporal\n"
        f"{ticker} — promedio de todas las bandas por período RSI",
        fontsize=13, fontweight="bold", color="#212529"
    )
 
    for idx_ax, tipo_senal in enumerate(["BUY", "SELL"]):
        ax = ejes[idx_ax]
        ax.set_facecolor(C_BG)
 
        # Línea horizontal en 0 = punto de equilibrio (ni gana ni pierde)
        # alpha=0.7 → 70% opaco (ligeramente transparente)
        ax.axhline(0, color="#868E96", linewidth=1.0,
                   linestyle="--", alpha=0.7, label="Punto de equilibrio")
 
        for idx_p, periodo in enumerate(periodos):
 
            # ── Acumular retornos de TODAS las bandas para este período ────────
            # Promediamos las 3 bandas → visión más robusta del comportamiento
            # {n: []} → diccionario donde cada horizonte tiene una lista vacía
            retornos_por_dia = {n: [] for n in dias_futuro}
 
            for sv, sc in bandas:
                clave_banda = f"{sv}/{sc}"
 
                try:
                    tabla_rend = resultados[periodo][clave_banda]["tabla_rendimientos"]
 
                    if tabla_rend.empty or "signal" not in tabla_rend.columns:
                        continue   # saltar esta banda si no hay datos
 
                    # Filtrar solo las señales del tipo actual (BUY o SELL)
                    sub = tabla_rend[tabla_rend["signal"] == tipo_senal]
 
                    for n in dias_futuro:
                        col = f"ret_{n}d"
                        if col in sub.columns:
                            # .dropna() elimina valores NaN
                            # .tolist() convierte la Serie a lista de Python
                            vals = sub[col].dropna().tolist()
                            # extend agrega todos los valores a la lista
                            retornos_por_dia[n].extend(vals)
                except KeyError:
                    continue
 
            # ── Calcular promedio para cada horizonte ─────────────────────────
            # Para cada N días, promediamos todos los retornos acumulados
            # Si la lista está vacía → NaN (no hay datos suficientes)
            retornos_promedio = [
                np.mean(retornos_por_dia[n]) if retornos_por_dia[n] else np.nan
                for n in dias_futuro
            ]
 
            # ── Dibujar la línea de este período ──────────────────────────────
            # idx_p % len(colores) → evita IndexError si hay más períodos que colores
            color  = colores[idx_p % len(colores)]
            estilo = estilos[idx_p % len(estilos)]
 
            ax.plot(dias_futuro,        # valores del eje X (días)
                    retornos_promedio,  # valores del eje Y (retorno %)
                    color=color,
                    linestyle=estilo,
                    linewidth=2.0,
                    marker="o",         # círculo en cada punto de dato
                    markersize=6,
                    label=f"RSI({periodo})")   # texto de la leyenda
 
        # ── Formato del panel ─────────────────────────────────────────────────
        color_titulo = C_BUY if tipo_senal == "BUY" else C_SELL
        ax.set_title(f"Señales {tipo_senal}",
                     fontsize=12, fontweight="bold", color=color_titulo)
        ax.set_xlabel("Días después de la señal", fontsize=10)
        ax.set_ylabel("Retorno promedio (%)", fontsize=10)
        ax.set_xticks(dias_futuro)   # marcas en el eje X exactamente en los días
        ax.grid(True, color=C_GRID, linewidth=0.6, linestyle="--")
        ax.spines[["top", "right"]].set_visible(False)   # ocultar bordes
        ax.legend(fontsize=9, framealpha=0.88, edgecolor=C_GRID)
 
    plt.tight_layout()
 
    if guardar:
        nombre = f"RSI_RetornoPromedio_Horizonte_{ticker}.png"
        plt.savefig(nombre, dpi=150, bbox_inches="tight", facecolor=C_BG)
        print(f"  Grafico guardado: {nombre}")
 
    plt.show(block=False)
    
