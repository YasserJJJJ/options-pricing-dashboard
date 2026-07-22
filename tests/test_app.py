"""Interface tests for the Streamlit dashboard."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = (
    Path(__file__).resolve().parents[1]
    / "app.py"
)


def load_app() -> AppTest:
    """Load and execute the Streamlit application."""
    app = AppTest.from_file(str(APP_FILE))
    app.run(timeout=10)

    assert not app.exception

    return app


def find_by_label(elements, label: str):
    """Find a Streamlit element using its visible label."""
    for element in elements:
        if element.label == label:
            return element

    raise AssertionError(
        f"Unable to find an element labelled {label!r}."
    )


def test_dashboard_loads_successfully() -> None:
    app = load_app()

    metric_labels = [
        metric.label
        for metric in app.metric
    ]

    subheaders = [
        subheader.value
        for subheader in app.subheader
    ]

    assert "Call Option Price" in metric_labels
    assert "Implied Volatility" in metric_labels
    assert "Simulated Option Price" in metric_labels
    assert "Greeks" in subheaders
    assert "Advanced Pricing" in subheaders
    assert "Charts" in subheaders


def test_option_type_can_be_changed_to_put() -> None:
    app = load_app()

    option_type = find_by_label(
        app.selectbox,
        "Option Type",
    )

    option_type.set_value("put")
    app.run(timeout=10)

    assert not app.exception
    assert app.metric[0].label == "Put Option Price"


def test_invalid_observed_price_displays_warning() -> None:
    app = load_app()

    observed_price = find_by_label(
        app.number_input,
        "Observed Option Price",
    )

    observed_price.set_value(200.0)
    app.run(timeout=10)

    assert not app.exception
    assert len(app.warning) == 1
    assert (
        "Market price must be between"
        in app.warning[0].value
    )