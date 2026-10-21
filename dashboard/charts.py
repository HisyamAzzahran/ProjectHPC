"""Plotly figures use only measured performance values or labeled educational domains."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

COLORS = {"sequential": "#B9A7FF", "multiprocessing": "#48B8EA", "mpi": "#7CDEC2"}


def polish(fig, title=None, height=390):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="#101C2D", font=dict(family="Segoe UI", color="#DDE7F5", size=12),
                      margin=dict(l=18, r=18, t=50 if title else 20, b=30), height=height,
                      legend=dict(orientation="h", y=-0.22), title=title,
                      hovermode="closest", colorway=list(COLORS.values()))
    fig.update_xaxes(gridcolor="#22354E", zeroline=False)
    fig.update_yaxes(gridcolor="#22354E", zeroline=False)
    return fig


def scaling_chart(summary, metric, title):
    fig = px.line(summary.sort_values("processes"), x="processes", y=metric, color="method",
                  line_dash="samples", markers=True, color_discrete_map=COLORS,
                  hover_data=["algorithm", "samples", "runs", "median_compute_seconds"],
                  labels={"processes": "Processes", "samples": "N", "method": "Method",
                          "median_end_to_end_seconds": "Median E2E (s)", "speedup": "Speedup",
                          "parallel_efficiency": "Parallel efficiency"})
    if metric == "speedup" and not summary.empty:
        p = sorted(summary.processes.unique())
        fig.add_trace(go.Scatter(x=p, y=p, name="Ideal S(p)=p", mode="lines",
                                 line=dict(color="#E7EDF5", dash="dot")))
    fig.update_xaxes(dtick=1)
    return polish(fig, title)


def monte_carlo_figure(workload, seed, chunk_size, maximum=4000):
    """Generate a prefix of the actual global chunk streams; never allocate the full run."""
    parts, remaining = [], min(workload, maximum)
    for index in range((remaining + chunk_size - 1) // chunk_size):
        count = min(chunk_size, remaining)
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, index])))
        parts.append(rng.random((count, 2)))
        remaining -= count
        if remaining == 0:
            break
    xy = np.vstack(parts)
    inside = np.sum(xy**2, axis=1) <= 1
    fig = go.Figure()
    for label, mask, color in (("Inside quarter circle", inside, "#7CDEC2"),
                               ("Outside quarter circle", ~inside, "#B9A7FF")):
        fig.add_trace(go.Scattergl(x=xy[mask, 0], y=xy[mask, 1], mode="markers", name=label,
                                  marker=dict(color=color, size=4, opacity=0.65)))
    x = np.linspace(0, 1, 250)
    fig.add_trace(go.Scatter(x=x, y=np.sqrt(1-x*x), mode="lines", name="x²+y²=1",
                             line=dict(color="#F4F8FF", width=2)))
    fig.update_xaxes(range=[0, 1], title="x")
    fig.update_yaxes(range=[0, 1], title="y", scaleanchor="x", scaleratio=1)
    return polish(fig, "Actual sample-stream prefix", 530), len(xy), int(inside.sum())


def midpoint_figure(rectangles):
    x = np.linspace(0, 1, 500)
    midpoints = (np.arange(rectangles) + 0.5) / rectangles
    heights = 4 / (1 + midpoints**2)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=midpoints, y=heights, width=1/rectangles, name=f"{rectangles} midpoint rectangles",
                         marker=dict(color="rgba(72,184,234,.32)", line=dict(color="#48B8EA", width=1))))
    fig.add_trace(go.Scatter(x=x, y=4/(1+x*x), name="f(x)=4/(1+x²)", mode="lines", line=dict(color="#7CDEC2", width=3)))
    fig.add_trace(go.Scatter(x=midpoints, y=heights, mode="markers", name="Midpoint evaluations",
                             marker=dict(color="#B9A7FF", size=5)))
    fig.update_xaxes(title="Integration domain x", range=[0, 1])
    fig.update_yaxes(title="f(x)", range=[0, 4.3])
    return polish(fig, "Midpoint rule: area as a sum of rectangles", 500), float(heights.sum() / rectangles)
