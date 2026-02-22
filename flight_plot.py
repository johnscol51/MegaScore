# flight_plot.py

import matplotlib.pyplot as plt

def make_flight_plot(fixes, points, outpath):
    """
    Optimised plotting function with balanced quality/performance.
    """

    # Extract track lat/lon
    lats = [lat for (_, lat, lon) in fixes]
    lons = [lon for (_, lat, lon) in fixes]

    # High DPI for crisp PDF, anti-aliasing selectively applied
    fig, ax = plt.subplots(figsize=(8.5, 6.8), dpi=120)

    # ---------------------------------------------------------
    # Flight trace (anti-aliasing ON for quality)
    # ---------------------------------------------------------
    ax.plot(lons, lats, color="blue", linewidth=1.2,
            antialiased=True, label="Flight Path")

    # ---------------------------------------------------------
    # Categorise task points
    # ---------------------------------------------------------
    sp_tp_fp_lons, sp_tp_fp_lats = [], []
    hg_lons, hg_lats = [], []
    photo_lons, photo_lats = [], []

    for p in points:
        name = p["name"].upper()
        lat = p["lat"]
        lon = p["lon"]

        if name.startswith("SP") or "TP" in name or name.startswith("FP"):
            sp_tp_fp_lons.append(lon)
            sp_tp_fp_lats.append(lat)

        elif "HG" in name:
            hg_lons.append(lon)
            hg_lats.append(lat)

        elif "PHOTO" in name:
            photo_lons.append(lon)
            photo_lats.append(lat)

    # ---------------------------------------------------------
    # Plot point categories (anti-aliasing OFF for speed)
    # ---------------------------------------------------------
    if sp_tp_fp_lons:
        ax.scatter(sp_tp_fp_lons, sp_tp_fp_lats,
                   color="#66ccff", s=30,
                   edgecolors="black", linewidths=0.2,
                   antialiased=False, label="SP/TP/FP")

    if hg_lons:
        ax.scatter(hg_lons, hg_lats,
                   color="green", s=35,
                   edgecolors="black", linewidths=0.2,
                   antialiased=False, label="HG")

    if photo_lons:
        ax.scatter(photo_lons, photo_lats,
                   color="yellow", s=15,
                   edgecolors="black", linewidths=0.2,
                   antialiased=False, label="Photo")

    # ---------------------------------------------------------
    # Add labels next to each point
    # ---------------------------------------------------------
    labels = []
    for p in points:
        name = p["name"]
        lat = p["lat"]
        lon = p["lon"]

        dx = 0.00015
        dy = 0.00015

        txt = ax.text(
            lon + dx,
            lat + dy,
            name,
            fontsize=7,
            color="black",
            ha="left",
            va="bottom",
        )
        labels.append(txt)

    # ---------------------------------------------------------
    # Fast collision avoidance
    # ---------------------------------------------------------
    renderer = fig.canvas.get_renderer()

    def labels_overlap(a, b):
        return a.get_window_extent(renderer).overlaps(
               b.get_window_extent(renderer))

    max_iterations = 8
    moved = True
    iterations = 0

    while moved and iterations < max_iterations:
        moved = False
        iterations += 1

        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        ax_dx = (xmax - xmin) * 0.0004
        ax_dy = (ymax - ymin) * 0.0004

        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                a = labels[i]
                b = labels[j]

                if labels_overlap(a, b):
                    ax_pos = a.get_position()
                    bx_pos = b.get_position()

                    a.set_position((ax_pos[0] + ax_dx, ax_pos[1] + ax_dy))
                    b.set_position((bx_pos[0] - ax_dx, bx_pos[1] - ax_dy))

                    moved = True

    # ---------------------------------------------------------
    # Axes formatting
    # ---------------------------------------------------------
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Flight Trace")
    ax.set_aspect('equal', adjustable='box')

    # ---------------------------------------------------------
    # Legend BELOW the plot
    # ---------------------------------------------------------
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=4,
        fontsize=8,
        frameon=True,
        framealpha=0.6,
    )

    fig.tight_layout()
    fig.savefig(outpath, format="png")
    plt.close(fig)

