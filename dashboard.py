"""Validated dashboard response built from the original Python pricing engine."""
import math
from black_scholes import (
    black_scholes_price, calculate_greeks, implied_volatility,
    monte_carlo_price, payoff_at_expiration, theoretical_price_bounds,
)


def number(data, key, default, minimum, maximum, integer=False):
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}.")
    if integer and value != int(value):
        raise ValueError(f"{key} must be a whole number.")
    return int(value) if integer else float(value)


def calculate_dashboard(data):
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    option_type = data.get("option_type", "call")
    if option_type not in ("call", "put"):
        raise ValueError("Option type must be call or put.")
    inputs = {
        "option_type": option_type,
        "stock_price": number(data, "stock_price", 100, 0.01, 1_000_000),
        "strike_price": number(data, "strike_price", 100, 0.01, 1_000_000),
        "days": number(data, "days", 30, 1, 3650, integer=True),
        "rate_percent": number(data, "rate_percent", 5, -20, 100),
        "volatility_percent": number(data, "volatility_percent", 20, 0.01, 300),
        "market_price": number(data, "market_price", 2.5, 0, 1_000_000),
        "simulations": number(data, "simulations", 20000, 1000, 50000, integer=True),
        "seed": number(data, "seed", 42, 0, 1_000_000, integer=True),
    }
    params = dict(S=inputs["stock_price"], K=inputs["strike_price"],
                  T=inputs["days"] / 365, r=inputs["rate_percent"] / 100,
                  sigma=inputs["volatility_percent"] / 100, option_type=option_type)
    price = black_scholes_price(**params)
    iv_params = {k: v for k, v in params.items() if k != "sigma"}
    bounds = theoretical_price_bounds(**iv_params)
    try:
        iv = implied_volatility(market_price=inputs["market_price"], **iv_params)
        iv_error = None
    except ValueError as error:
        iv, iv_error = None, str(error)
    stock_rows = []
    for i in range(51):
        stock = inputs["stock_price"] * (0.5 + i / 50)
        scenario = {**params, "S": stock}
        stock_rows.append({
            "stock_price": stock,
            "option_price": black_scholes_price(**scenario),
            "profit_loss": payoff_at_expiration(stock, params["K"], price, option_type),
            **calculate_greeks(**scenario),
        })
    volatility_rows = [
        {"volatility": vol, "option_price": black_scholes_price(**{**params, "sigma": vol / 100})}
        for vol in range(5, 101, 5)
    ]
    return {
        "inputs": inputs, "price": price, "greeks": calculate_greeks(**params),
        "implied_volatility": iv, "iv_error": iv_error, "price_bounds": bounds,
        "monte_carlo": monte_carlo_price(**params, simulations=inputs["simulations"], seed=inputs["seed"]),
        "stock_sensitivity": stock_rows, "volatility_sensitivity": volatility_rows,
        "break_even": params["K"] + price if option_type == "call" else params["K"] - price,
    }
