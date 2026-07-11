import math


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def validate_inputs(S: float, K: float, T: float, r: float, sigma: float) -> None:
    if S <= 0:
        raise ValueError("Stock price must be greater than 0.")
    if K <= 0:
        raise ValueError("Strike price must be greater than 0.")
    if T <= 0:
        raise ValueError("Time to expiration must be greater than 0.")
    if sigma <= 0:
        raise ValueError("Volatility must be greater than 0.")


def calculate_d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


def calculate_d2(d1: float, sigma: float, T: float) -> float:
    return d1 - sigma * math.sqrt(T)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str
) -> float:
    """
    Calculate the Black-Scholes price of a European call or put option.

    S: Current stock price
    K: Strike price
    T: Time to expiration in years
    r: Risk-free interest rate as decimal
    sigma: Volatility as decimal
    option_type: "call" or "put"
    """

    validate_inputs(S, K, T, r, sigma)

    option_type = option_type.lower()

    d1 = calculate_d1(S, K, T, r, sigma)
    d2 = calculate_d2(d1, sigma, T)

    if option_type == "call":
        return S * normal_cdf(d1) - K * math.exp(-r * T) * normal_cdf(d2)

    if option_type == "put":
        return K * math.exp(-r * T) * normal_cdf(-d2) - S * normal_cdf(-d1)

    raise ValueError("option_type must be 'call' or 'put'.")


def calculate_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str
) -> dict:
    """
    Calculate the main Greeks: Delta, Gamma, Theta, Vega, and Rho.
    """

    validate_inputs(S, K, T, r, sigma)

    option_type = option_type.lower()

    d1 = calculate_d1(S, K, T, r, sigma)
    d2 = calculate_d2(d1, sigma, T)

    pdf_d1 = normal_pdf(d1)

    gamma = pdf_d1 / (S * sigma * math.sqrt(T))
    vega = S * pdf_d1 * math.sqrt(T) / 100

    if option_type == "call":
        delta = normal_cdf(d1)

        theta = (
            -S * pdf_d1 * sigma / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * normal_cdf(d2)
        ) / 365

        rho = K * T * math.exp(-r * T) * normal_cdf(d2) / 100

    elif option_type == "put":
        delta = normal_cdf(d1) - 1

        theta = (
            -S * pdf_d1 * sigma / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * normal_cdf(-d2)
        ) / 365

        rho = -K * T * math.exp(-r * T) * normal_cdf(-d2) / 100

    else:
        raise ValueError("option_type must be 'call' or 'put'.")

    return {
        "Delta": delta,
        "Gamma": gamma,
        "Theta": theta,
        "Vega": vega,
        "Rho": rho,
    }


def payoff_at_expiration(
    stock_price_at_expiration: float,
    strike_price: float,
    premium: float,
    option_type: str
) -> float:
    """
    Calculate option profit/loss at expiration after subtracting the premium paid.
    """

    option_type = option_type.lower()

    if option_type == "call":
        intrinsic_value = max(stock_price_at_expiration - strike_price, 0)

    elif option_type == "put":
        intrinsic_value = max(strike_price - stock_price_at_expiration, 0)

    else:
        raise ValueError("option_type must be 'call' or 'put'.")

    return intrinsic_value - premium