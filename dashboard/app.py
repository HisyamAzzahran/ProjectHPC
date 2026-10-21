"""Streamlit entry point. Importing/rendering never launches an HPC calculation."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from core.execution_manager import get_manager
from dashboard import views
from dashboard.components import job_panel, mpi_available
from dashboard.styles import apply_style

st.set_page_config(page_title="HPC Parallel Computing & Performance Lab", page_icon="◈", layout="wide")
apply_style()

PAGES = {
    "Overview": ("Your local research workspace", views.overview),
    "Simulation Lab": ("Configure and run real numerical computations", views.simulation),
    "Algorithm Visualization": ("Explore sampling geometry and numerical integration", views.visualization),
    "Parallel Architecture": ("Inspect the single-node execution workflow", views.architecture),
    "Performance Benchmarking": ("Measure, compare, and export reproducible experiments", views.benchmarking),
    "Algorithm Comparison": ("Separate numerical accuracy from parallel performance", views.comparison),
    "System Monitoring": ("Observe real system and application resource usage", views.monitoring),
    "Experiment History": ("Review persistent runs, results, and execution logs", views.history),
}

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">H</span>HPC Lab</div><div class="muted">Parallel Computing & Performance</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Workspace", list(PAGES), key="navigation", label_visibility="collapsed")
    st.divider()
    st.caption("LOCAL EXECUTION")
    st.write("MPI ready" if mpi_available() else "MPI unavailable")
    st.caption("One computational job at a time. Your data stays in this workspace.")
    if st.button("Refresh view", key="refresh_view"):
        st.rerun()
    st.markdown('<div class="footer">SCALABLE PARALLEL PROGRAM<br>Monte Carlo · Midpoint Integration</div>', unsafe_allow_html=True)

subtitle, render = PAGES[page]
if page != "Overview":
    st.markdown('<div class="eyebrow">HPC PARALLEL COMPUTING & PERFORMANCE LAB</div>', unsafe_allow_html=True)
    st.title(page)
    st.caption(subtitle)
render()
job_panel()
