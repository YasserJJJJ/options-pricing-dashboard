"""API contract, numerical consistency, and HTTP validation regression tests."""
import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from api.calculate import handler
from black_scholes import black_scholes_price
from dashboard import calculate_dashboard


@pytest.fixture(scope="module")
def api_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address
    server.shutdown()
    server.server_close()
    thread.join()


def request(server, body, content_type="application/json", method="POST"):
    connection = HTTPConnection(*server, timeout=5)
    connection.request(method, "/api/calculate", body=body, headers={"Content-Type": content_type})
    response = connection.getresponse()
    status, data = response.status, json.loads(response.read())
    connection.close()
    return status, data


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_api_prices_and_chart_agree_with_original_engine(api_server, option_type):
    status, result = request(api_server, json.dumps({"option_type": option_type}))
    assert status == 200
    expected = black_scholes_price(100, 100, 30 / 365, 0.05, 0.2, option_type)
    assert result["price"] == pytest.approx(expected)
    assert result["stock_sensitivity"][25]["option_price"] == pytest.approx(expected)
    assert result["stock_sensitivity"][25]["profit_loss"] == pytest.approx(-expected)
    assert len(result["stock_sensitivity"]) == 51
    assert len(result["volatility_sensitivity"]) == 20
    assert set(result["greeks"]) == {"Delta", "Gamma", "Theta", "Vega", "Rho"}


def test_put_call_parity_in_api_response():
    import math
    call, put = calculate_dashboard({}), calculate_dashboard({"option_type": "put"})
    assert call["price"] - put["price"] == pytest.approx(100 - 100 * math.exp(-0.05 * 30 / 365))


def test_iv_warning_does_not_break_other_outputs(api_server):
    status, result = request(api_server, '{"market_price":200}')
    assert status == 200
    assert result["implied_volatility"] is None
    assert "Market price must be between" in result["iv_error"]
    assert result["price"] > 0
    assert result["monte_carlo"]["price"] > 0


def test_simulation_inputs_and_reproducibility():
    inputs = {"simulations": 5000, "seed": 8}
    a, b = calculate_dashboard(inputs), calculate_dashboard(inputs)
    assert a["monte_carlo"] == b["monte_carlo"]
    assert a["monte_carlo"]["seed"] == 8
    assert a["monte_carlo"]["simulations"] == 5000
    assert calculate_dashboard({**inputs, "seed": 9})["monte_carlo"]["price"] != a["monte_carlo"]["price"]


@pytest.mark.parametrize("inputs", [
    {"stock_price": 0}, {"strike_price": -1}, {"days": 0}, {"days": 1.5},
    {"volatility_percent": 0}, {"simulations": 50001}, {"simulations": 2000.5},
    {"seed": -1}, {"stock_price": True}, {"stock_price": "100"},
    {"stock_price": None}, {"stock_price": float("nan")}, {"rate_percent": float("inf")},
    {"option_type": "invalid"}, {"option_type": []}, [], None,
])
def test_invalid_inputs_are_rejected(api_server, inputs):
    status, result = request(api_server, json.dumps(inputs))
    assert status == 400
    assert result["error"]


@pytest.mark.parametrize("body", ["{bad json", "", "x" * 8193])
def test_invalid_body(api_server, body):
    assert request(api_server, body)[0] == 400


def test_wrong_content_type(api_server):
    assert request(api_server, "{}", "text/plain")[0] == 415


def test_health_endpoint(api_server):
    assert request(api_server, None, method="GET") == (200, {"status": "ok", "service": "options-pricing"})
