"""Plotly-Abbildungen: Karte mit Bewerbern/Kliniken (Kliniken als Quadrate, Füllstand in der Beschriftung), Verlauf,
Kapazitäts-/Reichweiten-Sweep, Aufwand gegen Größe. Achsen gesperrt (fixedrange) für Touch-Geräte."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import hr_constants as C
import hr_admission as A


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _collinear(sc):
    pts = list(sc.residents) + list(sc.hospitals)
    (x0, y0), (x1, y1) = pts[0], next((p for p in pts if p != pts[0]), pts[0])
    return all((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0) == 0 for x, y in pts)


def _edge_path(sc, i, j, curved, steps=14):
    (rx, ry), (hx, hy) = sc.residents[i], sc.hospitals[j]
    if not curved:
        return [rx, hx], [ry, hy]
    dx, dy = hx - rx, hy - ry
    side = 1 if (i + j) % 2 == 0 else -1
    cx, cy = (rx + hx) / 2 - side * 0.35 * dy, (ry + hy) / 2 + side * 0.35 * dx
    ts = [k / steps for k in range(steps + 1)]
    return ([(1 - t) ** 2 * rx + 2 * (1 - t) * t * cx + t * t * hx for t in ts], [(1 - t) ** 2 * ry + 2 * (1 - t) * t * cy + t * t * hy for t in ts])


def _segments(sc, pairs, curved=False):
    x, y = [], []
    for i, j in pairs:
        px, py = _edge_path(sc, i, j, curved)
        x += px + [None]
        y += py + [None]
    return x, y


def _map_layout(fig, sc, height):
    xs = [p[0] for p in list(sc.residents) + list(sc.hospitals)]
    ys = [p[1] for p in list(sc.residents) + list(sc.hospitals)]
    pad = 8
    if _collinear(sc):
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        if max(xs) - min(xs) >= max(ys) - min(ys):
            fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad])
            fig.update_yaxes(visible=False, range=[cy - span * 0.22, cy + span * 0.22])
        else:
            fig.update_xaxes(visible=False, range=[cx - span * 0.22, cx + span * 0.22])
            fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
        return _base(fig, min(height, 320))
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1, constrain="domain")
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad], constrain="domain")
    return _base(fig, height)


def build_map(sc, pairs_now, fill, event=None, height=430):
    """Karte: moegliche Paare schwach grau, aktuell gehaltene Paare blau, das letzte Ereignis hervorgehoben; Kliniken
    als Quadrate beschriftet mit Fuellstand/Kapazitaet (voll = lila, teilweise = orange, leer = rot)."""
    curved = _collinear(sc)
    fig = go.Figure()
    all_pairs = [(i, j) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]]
    ex, ey = _segments(sc, all_pairs, curved)
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.25)", width=1), hoverinfo="skip", name="mögliche Paare"))
    px, py = _segments(sc, list(pairs_now), curved)
    fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=C.COLORS["held"], width=3), hoverinfo="skip", name="gehalten"))

    if event is not None and event.h >= 0 and event.r >= 0:
        color = {A.EV_ACCEPT: C.COLORS["propose"], A.EV_DISPLACE: C.COLORS["displace"], A.EV_PROPOSE: "#888", A.EV_REJECT: "#aaaaaa"}.get(event.kind, "#333")
        lx, ly = _segments(sc, [(event.r, event.h)], curved)
        fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color=color, width=5, dash="dash" if event.kind in (A.EV_REJECT,) else None), hoverinfo="skip", name=event.kind))

    matched_r = {i for i, _ in pairs_now}
    small = sc.n <= 30
    for idx, name, on in (([k for k in range(sc.n) if k in matched_r], "Bewerber zugelassen", True), ([k for k in range(sc.n) if k not in matched_r], "Bewerber frei", False)):
        if idx:
            fig.add_trace(go.Scatter(x=[sc.residents[k][0] for k in idx], y=[sc.residents[k][1] for k in idx], mode="markers+text" if small else "markers", name=name,
                                     text=[str(k) for k in idx] if small else None, textposition="top center", hovertext=[f"Bewerber {k}" for k in idx], hoverinfo="text",
                                     marker=dict(symbol="circle" if on else "circle-open", size=11, color=C.COLORS["resident"], line=dict(width=2, color=C.COLORS["resident"]))))

    fx, fy, ftext, fcolor = [], [], [], []
    for j in range(sc.m):
        fx.append(sc.hospitals[j][0])
        fy.append(sc.hospitals[j][1])
        ftext.append(f"{j}: {fill[j]}/{sc.cap[j]}")
        fcolor.append(C.COLORS["full"] if fill[j] >= sc.cap[j] else (C.COLORS["under"] if fill[j] > 0 else C.COLORS["empty"]))
    fig.add_trace(go.Scatter(x=fx, y=fy, mode="markers+text", name="Kliniken", text=ftext, textposition="bottom center",
                             hovertext=[f"Klinik {j}: {fill[j]} von {sc.cap[j]} Plätzen belegt" for j in range(sc.m)], hoverinfo="text",
                             marker=dict(symbol="square", size=14, color=fcolor, line=dict(width=2, color=C.COLORS["hospital"]))))
    fig = _map_layout(fig, sc, height)
    fig.update_layout(showlegend=False)
    return fig


def build_progress(res, k, height=240):
    xs = list(range(res.n_events + 1))
    matched = [sum(len(h) for h in s.held) for s in res.snapshots]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=matched, mode="lines", name="belegte Plätze", line=dict(color=C.COLORS["held"], shape="hv")))
    fig.add_vline(x=k, line=dict(color="#333", width=2))
    fig.update_xaxes(title="Ereignis")
    fig.update_yaxes(title="belegte Plätze", rangemode="tozero")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.45))
    return fig


def build_quote_sweep(rows, height=320):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    qs = [r["quote"] for r in rows]
    fig.add_trace(go.Scatter(x=qs, y=[100 * r["any_under_share"] for r in rows], mode="lines+markers", name="mind. eine Klinik unbesetzt [%]", line=dict(color=C.COLORS["under"])), secondary_y=False)
    fig.add_trace(go.Scatter(x=qs, y=[r["unmatched_mean"] for r in rows], mode="lines+markers", name="unversorgte Bewerber (Mittel)", line=dict(color=C.COLORS["resident"])), secondary_y=True)
    fig.update_xaxes(title="Kapazitätsquote [%]")
    fig.update_yaxes(title="Karten [%]", secondary_y=False, rangemode="tozero", range=[0, 105])
    fig.update_yaxes(title="Unversorgte Bewerber", secondary_y=True, rangemode="tozero", showgrid=False)
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 40)
    return fig


def build_reach_sweep(rows, height=300):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    reaches = [r["reach"] for r in rows]
    fig.add_trace(go.Scatter(x=reaches, y=[100 * r["any_under_share"] for r in rows], mode="lines+markers", name="mind. eine Klinik unbesetzt [%]", line=dict(color=C.COLORS["under"])), secondary_y=False)
    fig.add_trace(go.Scatter(x=reaches, y=[r["degree"] for r in rows], mode="lines+markers", name="mittlerer Grad", line=dict(color="#555", dash="dot")), secondary_y=True)
    fig.update_xaxes(title="Reichweite [min]")
    fig.update_yaxes(title="Karten [%]", secondary_y=False, rangemode="tozero", range=[0, 105])
    fig.update_yaxes(title="Mittlerer Grad", secondary_y=True, rangemode="tozero", showgrid=False)
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 40)
    return fig


def build_scale(rows, height=320):
    fig = go.Figure()
    ns = [r["n"] for r in rows]
    fig.add_trace(go.Scatter(x=ns, y=[r["proposals"] for r in rows], mode="lines+markers", name="Bewerbungen", line=dict(color=C.COLORS["held"])))
    fig.update_xaxes(title="Bewerber", type="log")
    fig.update_yaxes(title="Bewerbungen", type="log")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 40)
    return fig
