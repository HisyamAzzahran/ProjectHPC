"""Streamlit AppTest renders pages and submits actual background simulations."""
import time

import pytest
from streamlit.testing.v1 import AppTest

from core.execution_manager import ExecutionManager
from environment import ROOT


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    import core.execution_manager as module
    manager = ExecutionManager(tmp_path)
    monkeypatch.setattr(module, "_manager", manager)
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=40).run()
    yield app, manager
    if manager.busy():
        manager.cancel()
        manager.wait(30)


def test_all_eight_pages_render_without_launching_jobs(dashboard):
    app, manager = dashboard
    assert not app.exception
    pages = app.radio(key="navigation").options
    assert len(pages) == 8
    for page in pages:
        app.radio(key="navigation").set_value(page).run()
        assert not app.exception, (page, [x.message for x in app.exception])
    assert manager.store.history() == []


def test_both_algorithm_visualizations(dashboard):
    app, _ = dashboard
    app.radio(key="navigation").set_value("Algorithm Visualization").run()
    assert not app.exception
    app.selectbox(key="viz_algorithm").set_value("midpoint").run()
    assert not app.exception
    assert any("Illustrated area" in m.label for m in app.metric)


def test_submit_real_midpoint_from_ui_and_survive_reruns(dashboard):
    app, manager = dashboard
    app.radio(key="navigation").set_value("Simulation Lab").run()
    app.selectbox(key="sim_algorithm").set_value("midpoint").run()
    app.selectbox(key="sim_method").set_value("multiprocessing").run()
    app.number_input(key="sim_workload").set_value(10003)
    app.number_input(key="sim_chunk").set_value(997)
    next(b for b in app.button if b.label == "Run Simulation").click().run()
    assert not app.exception, [x.message for x in app.exception]
    record = manager.wait(30)
    assert record and record["status"] == "COMPLETED", record
    app.radio(key="navigation").set_value("Experiment History").run()
    assert not app.exception
    app.run()
    assert len(manager.store.history()) == 1
    assert manager.store.history()[0]["result"]["algorithm"] == "midpoint"


def test_mpi_unavailable_still_renders(dashboard, monkeypatch):
    import dashboard.components as components
    monkeypatch.setattr(components, "mpi_available", lambda: False)
    # views imported the function directly, so patch that binding as well.
    import dashboard.views as views
    monkeypatch.setattr(views, "mpi_available", lambda: False)
    app, _ = dashboard
    app.radio(key="navigation").set_value("Simulation Lab").run()
    assert not app.exception
    assert app.selectbox(key="sim_method").options == ["Sequential", "Multiprocessing"]


def test_cancel_and_reset_buttons(dashboard):
    app, manager = dashboard
    app.radio(key="navigation").set_value("Simulation Lab").run()
    app.selectbox(key="sim_method").set_value("multiprocessing").run()
    app.number_input(key="sim_workload").set_value(1_000_000_000)
    next(b for b in app.button if b.label == "Run Simulation").click().run()
    assert manager.busy()
    app.button(key="global_cancel").click().run()
    assert manager.wait(20)["status"] == "CANCELLED"
    next(b for b in app.button if b.label == "Reset Configuration").click().run()
    assert app.number_input(key="sim_workload").value == 1_000_000
    assert not app.exception


def test_compare_all_configurations_button_creates_real_benchmark(dashboard):
    app, manager = dashboard
    app.radio(key="navigation").set_value("Performance Benchmarking").run()
    next(w for w in app.multiselect if w.label == "Workload sizes").set_value([100_000])
    next(w for w in app.multiselect if w.label == "Parallel process counts").set_value([1, 2])
    action = next(b for b in app.button if b.label in ("Compare All Six Configurations", "Compare available configurations"))
    action.click().run()
    assert not app.exception
    record = manager.wait(120)
    assert record["status"] == "COMPLETED", record
    assert record["config"]["algorithms"] == ["monte_carlo", "midpoint"]
    app.radio(key="navigation").set_value("Experiment History").run()
    assert not app.exception
