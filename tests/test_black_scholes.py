"""Automated tests for the Black-Scholes pricing engine."""

import math

import pytest

from black_scholes import (
    black_scholes_price,
    calculate_d1,
    calculate_d2,
    calculate_greeks,
    implied_volatility,
    monte_carlo_price,
    normal_cdf,
    normal_pdf,
    payoff_at_expiration,
    theoretical_price_bounds,
    validate_inputs,
)


STANDARD_INPUTS = {
    "S": 100.0,
    "K": 100.0,
    "T": 1.0,
    "r": 0.05,
    "sigma": 0.20,
}


def test_normal_distribution_helpers_at_zero() -> None:
    """The standard normal CDF and PDF should match their known values at zero."""
    assert normal_cdf(0.0) == pytest.approx(0.5)
    assert normal_pdf(0.0) == pytest.approx(1.0 / math.sqrt(2.0 * math.pi))


def test_d1_and_d2_relationship() -> None:
    d1 = calculate_d1(**STANDARD_INPUTS)
    d2 = calculate_d2(d1, STANDARD_INPUTS["sigma"], STANDARD_INPUTS["T"])

    assert d1 == pytest.approx(0.35)
    assert d2 == pytest.approx(0.15)
    assert d1 - d2 == pytest.approx(
        STANDARD_INPUTS["sigma"] * math.sqrt(STANDARD_INPUTS["T"])
    )


def test_standard_call_price() -> None:
    price = black_scholes_price(**STANDARD_INPUTS, option_type="call")
    assert price == pytest.approx(10.4505835722, abs=1e-10)


def test_standard_put_price() -> None:
    price = black_scholes_price(**STANDARD_INPUTS, option_type="put")
    assert price == pytest.approx(5.5735260223, abs=1e-10)


def test_option_type_is_case_insensitive() -> None:
    lowercase = black_scholes_price(**STANDARD_INPUTS, option_type="call")
    uppercase = black_scholes_price(**STANDARD_INPUTS, option_type="CALL")
    assert uppercase == pytest.approx(lowercase)


def test_put_call_parity() -> None:
    call = black_scholes_price(**STANDARD_INPUTS, option_type="call")
    put = black_scholes_price(**STANDARD_INPUTS, option_type="put")

    expected_difference = STANDARD_INPUTS["S"] - (
        STANDARD_INPUTS["K"]
        * math.exp(-STANDARD_INPUTS["r"] * STANDARD_INPUTS["T"])
    )

    assert call - put == pytest.approx(expected_difference, abs=1e-10)


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected_message"),
    [
        ("S", 0.0, "Stock price must be greater than 0."),
        ("S", -1.0, "Stock price must be greater than 0."),
        ("K", 0.0, "Strike price must be greater than 0."),
        ("K", -1.0, "Strike price must be greater than 0."),
        ("T", 0.0, "Time to expiration must be greater than 0."),
        ("T", -1.0, "Time to expiration must be greater than 0."),
        ("sigma", 0.0, "Volatility must be greater than 0."),
        ("sigma", -0.1, "Volatility must be greater than 0."),
    ],
)
def test_validate_inputs_rejects_invalid_values(
    field: str,
    invalid_value: float,
    expected_message: str,
) -> None:
    inputs = STANDARD_INPUTS.copy()
    inputs[field] = invalid_value

    with pytest.raises(ValueError, match=expected_message):
        validate_inputs(**inputs)


def test_negative_interest_rate_is_allowed() -> None:
    """Negative interest rates are possible and should not be rejected."""
    validate_inputs(S=100.0, K=100.0, T=1.0, r=-0.01, sigma=0.20)


@pytest.mark.parametrize("function", [black_scholes_price, calculate_greeks])
def test_invalid_option_type_is_rejected(function) -> None:
    with pytest.raises(ValueError, match="option_type must be 'call' or 'put'."):
        function(**STANDARD_INPUTS, option_type="invalid")


def test_standard_call_greeks() -> None:
    greeks = calculate_greeks(**STANDARD_INPUTS, option_type="call")

    assert greeks["Delta"] == pytest.approx(0.6368306512, abs=1e-10)
    assert greeks["Gamma"] == pytest.approx(0.01876201735, abs=1e-10)
    assert greeks["Theta"] == pytest.approx(-0.01757267821, abs=1e-10)
    assert greeks["Vega"] == pytest.approx(0.3752403469, abs=1e-10)
    assert greeks["Rho"] == pytest.approx(0.5323248155, abs=1e-10)


def test_standard_put_greeks() -> None:
    greeks = calculate_greeks(**STANDARD_INPUTS, option_type="put")

    assert greeks["Delta"] == pytest.approx(-0.3631693488, abs=1e-10)
    assert greeks["Gamma"] == pytest.approx(0.01876201735, abs=1e-10)
    assert greeks["Theta"] == pytest.approx(-0.004542138148, abs=1e-10)
    assert greeks["Vega"] == pytest.approx(0.3752403469, abs=1e-10)
    assert greeks["Rho"] == pytest.approx(-0.4189046090, abs=1e-10)


def test_call_and_put_greek_relationships() -> None:
    call = calculate_greeks(**STANDARD_INPUTS, option_type="call")
    put = calculate_greeks(**STANDARD_INPUTS, option_type="put")

    assert call["Delta"] - put["Delta"] == pytest.approx(1.0)
    assert call["Gamma"] == pytest.approx(put["Gamma"])
    assert call["Vega"] == pytest.approx(put["Vega"])


def test_option_prices_respect_theoretical_bounds() -> None:
    call = black_scholes_price(**STANDARD_INPUTS, option_type="call")
    put = black_scholes_price(**STANDARD_INPUTS, option_type="put")

    discounted_strike = STANDARD_INPUTS["K"] * math.exp(
        -STANDARD_INPUTS["r"] * STANDARD_INPUTS["T"]
    )

    assert max(0.0, STANDARD_INPUTS["S"] - discounted_strike) <= call <= STANDARD_INPUTS["S"]
    assert max(0.0, discounted_strike - STANDARD_INPUTS["S"]) <= put <= discounted_strike


def test_call_price_increases_with_stock_price() -> None:
    low = black_scholes_price(**{**STANDARD_INPUTS, "S": 90.0}, option_type="call")
    high = black_scholes_price(**{**STANDARD_INPUTS, "S": 110.0}, option_type="call")
    assert high > low


def test_put_price_decreases_with_stock_price() -> None:
    low = black_scholes_price(**{**STANDARD_INPUTS, "S": 90.0}, option_type="put")
    high = black_scholes_price(**{**STANDARD_INPUTS, "S": 110.0}, option_type="put")
    assert high < low


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_option_price_increases_with_volatility(option_type: str) -> None:
    low_volatility = black_scholes_price(
        **{**STANDARD_INPUTS, "sigma": 0.10}, option_type=option_type
    )
    high_volatility = black_scholes_price(
        **{**STANDARD_INPUTS, "sigma": 0.40}, option_type=option_type
    )
    assert high_volatility > low_volatility


@pytest.mark.parametrize(
    ("stock_price", "expected_profit"),
    [
        (80.0, -5.0),
        (100.0, -5.0),
        (120.0, 15.0),
    ],
)
def test_call_payoff_at_expiration(stock_price: float, expected_profit: float) -> None:
    assert payoff_at_expiration(stock_price, 100.0, 5.0, "call") == expected_profit


@pytest.mark.parametrize(
    ("stock_price", "expected_profit"),
    [
        (80.0, 15.0),
        (100.0, -5.0),
        (120.0, -5.0),
    ],
)
def test_put_payoff_at_expiration(stock_price: float, expected_profit: float) -> None:
    assert payoff_at_expiration(stock_price, 100.0, 5.0, "put") == expected_profit


def test_payoff_option_type_is_case_insensitive() -> None:
    assert payoff_at_expiration(120.0, 100.0, 5.0, "CALL") == 15.0


def test_payoff_rejects_invalid_option_type() -> None:
    with pytest.raises(ValueError, match="option_type must be 'call' or 'put'."):
        payoff_at_expiration(100.0, 100.0, 5.0, "invalid")

@pytest.mark.parametrize("option_type", ["call", "put"])
def test_implied_volatility_recovers_original_volatility(
    option_type: str,
) -> None:
    market_price = black_scholes_price(
        **STANDARD_INPUTS,
        option_type=option_type,
    )

    result = implied_volatility(
        market_price=market_price,
        S=STANDARD_INPUTS["S"],
        K=STANDARD_INPUTS["K"],
        T=STANDARD_INPUTS["T"],
        r=STANDARD_INPUTS["r"],
        option_type=option_type,
    )

    assert result == pytest.approx(
        STANDARD_INPUTS["sigma"],
        abs=1e-6,
    )


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_theoretical_price_bounds_are_valid(
    option_type: str,
) -> None:
    lower, upper = theoretical_price_bounds(
        S=100.0,
        K=100.0,
        T=1.0,
        r=0.05,
        option_type=option_type,
    )

    assert lower >= 0
    assert upper > lower


@pytest.mark.parametrize(
    ("field", "invalid_value", "message"),
    [
        ("S", 0.0, "Stock price"),
        ("K", 0.0, "Strike price"),
        ("T", 0.0, "Time to expiration"),
        ("option_type", "invalid", "option_type"),
    ],
)
def test_theoretical_bounds_reject_invalid_inputs(
    field: str,
    invalid_value,
    message: str,
) -> None:
    inputs = {
        "S": 100.0,
        "K": 100.0,
        "T": 1.0,
        "r": 0.05,
        "option_type": "call",
    }

    inputs[field] = invalid_value

    with pytest.raises(ValueError, match=message):
        theoretical_price_bounds(**inputs)


def test_implied_volatility_rejects_impossible_price() -> None:
    with pytest.raises(
        ValueError,
        match="Market price must be between",
    ):
        implied_volatility(
            market_price=200.0,
            S=100.0,
            K=100.0,
            T=1.0,
            r=0.05,
            option_type="call",
        )


def test_implied_volatility_respects_iteration_limit() -> None:
    result = implied_volatility(
        market_price=10.0,
        S=100.0,
        K=100.0,
        T=1.0,
        r=0.05,
        option_type="call",
        max_iterations=1,
    )

    assert 0.0 < result < 5.0


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_monte_carlo_is_close_to_black_scholes(
    option_type: str,
) -> None:
    analytical_price = black_scholes_price(
        **STANDARD_INPUTS,
        option_type=option_type,
    )

    simulation = monte_carlo_price(
        **STANDARD_INPUTS,
        option_type=option_type,
        simulations=50_000,
        seed=7,
    )

    difference = abs(
        simulation["price"] - analytical_price
    )

    assert (
        difference
        < 4 * simulation["standard_error"]
    )

    assert (
        simulation["confidence_low"]
        <= simulation["price"]
        <= simulation["confidence_high"]
    )


def test_monte_carlo_is_reproducible() -> None:
    first = monte_carlo_price(
        **STANDARD_INPUTS,
        option_type="call",
        simulations=1_000,
        seed=123,
    )

    second = monte_carlo_price(
        **STANDARD_INPUTS,
        option_type="call",
        simulations=1_000,
        seed=123,
    )

    assert first == second


def test_monte_carlo_rejects_too_few_simulations() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        monte_carlo_price(
            **STANDARD_INPUTS,
            option_type="call",
            simulations=1,
        )


def test_monte_carlo_rejects_invalid_option_type() -> None:
    with pytest.raises(ValueError, match="option_type"):
        monte_carlo_price(
            **STANDARD_INPUTS,
            option_type="invalid",
        )

def test_implied_volatility_expands_search_range() -> None:
    market_price = black_scholes_price(
        **{**STANDARD_INPUTS, "sigma": 6.0},
        option_type="call",
    )

    result = implied_volatility(
        market_price=market_price,
        S=STANDARD_INPUTS["S"],
        K=STANDARD_INPUTS["K"],
        T=STANDARD_INPUTS["T"],
        r=STANDARD_INPUTS["r"],
        option_type="call",
    )

    assert result == pytest.approx(6.0, abs=1e-6)


def test_implied_volatility_returns_zero_at_lower_bound() -> None:
    lower_bound, _ = theoretical_price_bounds(
        S=100.0,
        K=100.0,
        T=1.0,
        r=0.05,
        option_type="call",
    )

    result = implied_volatility(
        market_price=lower_bound,
        S=100.0,
        K=100.0,
        T=1.0,
        r=0.05,
        option_type="call",
    )

    assert result == 0.0


def test_implied_volatility_rejects_upper_bound() -> None:
    _, upper_bound = theoretical_price_bounds(
        S=100.0,
        K=100.0,
        T=1.0,
        r=0.05,
        option_type="call",
    )

    with pytest.raises(ValueError, match="finite implied volatility"):
        implied_volatility(
            market_price=upper_bound,
            S=100.0,
            K=100.0,
            T=1.0,
            r=0.05,
            option_type="call",
        )


@pytest.mark.parametrize(
    ("argument", "value", "message"),
    [
        ("tolerance", 0.0, "Tolerance"),
        ("max_iterations", 0, "Maximum iterations"),
    ],
)
def test_implied_volatility_rejects_invalid_solver_settings(
    argument: str,
    value,
    message: str,
) -> None:
    arguments = {
        "market_price": 10.0,
        "S": 100.0,
        "K": 100.0,
        "T": 1.0,
        "r": 0.05,
        "option_type": "call",
    }
    arguments[argument] = value

    with pytest.raises(ValueError, match=message):
        implied_volatility(**arguments)