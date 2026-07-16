import math
import random


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (
        1.0 / math.sqrt(2.0 * math.pi)
    ) * math.exp(-0.5 * x * x)


def validate_inputs(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> None:
    """Validate the main model inputs."""

    if S <= 0:
        raise ValueError("Stock price must be greater than 0.")

    if K <= 0:
        raise ValueError("Strike price must be greater than 0.")

    if T <= 0:
        raise ValueError(
            "Time to expiration must be greater than 0."
        )

    if sigma <= 0:
        raise ValueError("Volatility must be greater than 0.")


def calculate_d1(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> float:
    """Calculate the Black-Scholes d1 value."""

    return (
        math.log(S / K)
        + (r + 0.5 * sigma**2) * T
    ) / (sigma * math.sqrt(T))


def calculate_d2(
    d1: float,
    sigma: float,
    T: float,
) -> float:
    """Calculate the Black-Scholes d2 value."""

    return d1 - sigma * math.sqrt(T)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
) -> float:
    """Calculate the price of a European call or put option."""

    validate_inputs(S, K, T, r, sigma)

    option_type = option_type.lower()

    d1 = calculate_d1(S, K, T, r, sigma)
    d2 = calculate_d2(d1, sigma, T)

    if option_type == "call":
        return (
            S * normal_cdf(d1)
            - K
            * math.exp(-r * T)
            * normal_cdf(d2)
        )

    if option_type == "put":
        return (
            K
            * math.exp(-r * T)
            * normal_cdf(-d2)
            - S * normal_cdf(-d1)
        )

    raise ValueError(
        "option_type must be 'call' or 'put'."
    )


def calculate_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
) -> dict:
    """Calculate Delta, Gamma, Theta, Vega, and Rho."""

    validate_inputs(S, K, T, r, sigma)

    option_type = option_type.lower()

    d1 = calculate_d1(S, K, T, r, sigma)
    d2 = calculate_d2(d1, sigma, T)

    pdf_d1 = normal_pdf(d1)

    gamma = pdf_d1 / (
        S * sigma * math.sqrt(T)
    )

    vega = (
        S
        * pdf_d1
        * math.sqrt(T)
        / 100
    )

    if option_type == "call":
        delta = normal_cdf(d1)

        theta = (
            -S
            * pdf_d1
            * sigma
            / (2 * math.sqrt(T))
            - r
            * K
            * math.exp(-r * T)
            * normal_cdf(d2)
        ) / 365

        rho = (
            K
            * T
            * math.exp(-r * T)
            * normal_cdf(d2)
            / 100
        )

    elif option_type == "put":
        delta = normal_cdf(d1) - 1

        theta = (
            -S
            * pdf_d1
            * sigma
            / (2 * math.sqrt(T))
            + r
            * K
            * math.exp(-r * T)
            * normal_cdf(-d2)
        ) / 365

        rho = (
            -K
            * T
            * math.exp(-r * T)
            * normal_cdf(-d2)
            / 100
        )

    else:
        raise ValueError(
            "option_type must be 'call' or 'put'."
        )

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
    option_type: str,
) -> float:
    """Calculate profit or loss at expiration."""

    option_type = option_type.lower()

    if option_type == "call":
        intrinsic_value = max(
            stock_price_at_expiration - strike_price,
            0,
        )

    elif option_type == "put":
        intrinsic_value = max(
            strike_price - stock_price_at_expiration,
            0,
        )

    else:
        raise ValueError(
            "option_type must be 'call' or 'put'."
        )

    return intrinsic_value - premium


def theoretical_price_bounds(
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
) -> tuple[float, float]:
    """Return the theoretical lower and upper price bounds."""

    if S <= 0:
        raise ValueError(
            "Stock price must be greater than 0."
        )

    if K <= 0:
        raise ValueError(
            "Strike price must be greater than 0."
        )

    if T <= 0:
        raise ValueError(
            "Time to expiration must be greater than 0."
        )

    option_type = option_type.lower()
    discounted_strike = K * math.exp(-r * T)

    if option_type == "call":
        lower_bound = max(
            0.0,
            S - discounted_strike,
        )
        upper_bound = S

        return lower_bound, upper_bound

    if option_type == "put":
        lower_bound = max(
            0.0,
            discounted_strike - S,
        )
        upper_bound = discounted_strike

        return lower_bound, upper_bound

    raise ValueError(
        "option_type must be 'call' or 'put'."
    )


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
    tolerance: float = 1e-7,
    max_iterations: int = 200,
) -> float:
    """Estimate implied volatility using bisection."""

    lower_bound, upper_bound = theoretical_price_bounds(
        S=S,
        K=K,
        T=T,
        r=r,
        option_type=option_type,
    )

    if not lower_bound <= market_price <= upper_bound:
        raise ValueError(
            "Market price must be between "
            f"{lower_bound:.4f} and "
            f"{upper_bound:.4f}."
        )

    low_volatility = 0.000001
    high_volatility = 5.0

    for _ in range(max_iterations):
        midpoint = (
            low_volatility + high_volatility
        ) / 2

        estimated_price = black_scholes_price(
            S=S,
            K=K,
            T=T,
            r=r,
            sigma=midpoint,
            option_type=option_type,
        )

        price_difference = (
            estimated_price - market_price
        )

        if abs(price_difference) <= tolerance:
            return midpoint

        if estimated_price < market_price:
            low_volatility = midpoint
        else:
            high_volatility = midpoint

    return (
        low_volatility + high_volatility
    ) / 2


def monte_carlo_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
    simulations: int = 20_000,
    seed: int = 42,
) -> dict:
    """Price a European option using Monte Carlo simulation."""

    validate_inputs(S, K, T, r, sigma)

    if simulations < 2:
        raise ValueError(
            "Simulations must be at least 2."
        )

    option_type = option_type.lower()

    if option_type not in {"call", "put"}:
        raise ValueError(
            "option_type must be 'call' or 'put'."
        )

    random_generator = random.Random(seed)

    drift = (
        r - 0.5 * sigma**2
    ) * T

    diffusion = sigma * math.sqrt(T)

    payoff_sum = 0.0
    payoff_squared_sum = 0.0

    for _ in range(simulations):
        random_value = random_generator.gauss(
            0.0,
            1.0,
        )

        terminal_stock_price = S * math.exp(
            drift + diffusion * random_value
        )

        if option_type == "call":
            payoff = max(
                terminal_stock_price - K,
                0.0,
            )
        else:
            payoff = max(
                K - terminal_stock_price,
                0.0,
            )

        payoff_sum += payoff
        payoff_squared_sum += payoff**2

    average_payoff = payoff_sum / simulations

    sample_variance = (
        payoff_squared_sum
        - simulations * average_payoff**2
    ) / (simulations - 1)

    discount_factor = math.exp(-r * T)

    price = discount_factor * average_payoff

    standard_error = (
        discount_factor
        * math.sqrt(
            max(sample_variance, 0.0)
            / simulations
        )
    )

    confidence_margin = 1.96 * standard_error

    return {
        "price": price,
        "standard_error": standard_error,
        "confidence_low": max(
            0.0,
            price - confidence_margin,
        ),
        "confidence_high": (
            price + confidence_margin
        ),
        "simulations": simulations,
        "seed": seed,
    }