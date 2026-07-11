"""Automated tests for the Black-Scholes pricing engine."""

import math

import pytest

from black_scholes import (
    black_scholes_price,
    calculate_d1,
    calculate_d2,
    calculate_greeks,
    normal_cdf,
    normal_pdf,
    payoff_at_expiration,
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
