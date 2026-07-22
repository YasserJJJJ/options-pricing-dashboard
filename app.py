import pandas as pd
import streamlit as st

from black_scholes import (
    black_scholes_price,
    calculate_greeks,
    implied_volatility,
    monte_carlo_price,
    payoff_at_expiration,
    theoretical_price_bounds,
)


st.set_page_config(
    page_title="Options Pricing Dashboard",
    page_icon="📈",
    layout="wide"
)


st.markdown(
    """
    <style>
    .main-title {
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .section-card {
        padding: 24px;
        border-radius: 16px;
        background-color: rgba(250, 250, 250, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 20px;
    }

    .small-text {
        color: #777;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown('<div class="main-title">Options Pricing Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Black-Scholes option pricing, Greeks, payoff analysis, and sensitivity charts.</div>',
    unsafe_allow_html=True
)


with st.sidebar:
    st.header("Option Inputs")

    option_type = st.selectbox(
        "Option Type",
        ["call", "put"]
    )

    S = st.number_input(
        "Current Stock Price",
        min_value=0.01,
        value=100.00,
        step=1.00
    )

    K = st.number_input(
        "Strike Price",
        min_value=0.01,
        value=100.00,
        step=1.00
    )

    days_to_expiration = st.number_input(
        "Days to Expiration",
        min_value=1,
        value=30,
        step=1
    )

    risk_free_rate_percent = st.number_input(
        "Risk-Free Rate (%)",
        min_value=0.00,
        value=5.00,
        step=0.25
    )

    volatility_percent = st.number_input(
        "Volatility (%)",
        min_value=0.01,
        value=20.00,
        step=1.00
    )

    st.subheader("Advanced Inputs")

    observed_market_price = st.number_input(
        "Observed Option Price",
        min_value=0.00,
        value=2.50,
        step=0.10,
        help=(
            "The current option price used to calculate "
            "implied volatility."
        ),
    )

    simulations = st.select_slider(
        "Monte Carlo Simulations",
        options=[
            1_000,
            5_000,
            10_000,
            20_000,
            50_000,
        ],
        value=20_000,
        help=(
            "More simulations generally improve precision "
            "but take longer."
        ),
    )

    random_seed = st.number_input(
        "Simulation Seed",
        min_value=0,
        max_value=1_000_000,
        value=42,
        step=1,
        help=(
            "Using the same seed makes the simulation "
            "reproducible."
        ),
    )
    st.divider()

    st.caption(
        "This dashboard prices European options using the Black-Scholes model."
    )


T = days_to_expiration / 365
r = risk_free_rate_percent / 100
sigma = volatility_percent / 100


price = black_scholes_price(
    S=S,
    K=K,
    T=T,
    r=r,
    sigma=sigma,
    option_type=option_type
)

greeks = calculate_greeks(
    S=S,
    K=K,
    T=T,
    r=r,
    sigma=sigma,
    option_type=option_type
)


left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("Theoretical Option Price")

    st.metric(
        label=f"{option_type.capitalize()} Option Price",
        value=f"${price:.2f}"
    )

    st.markdown(
        """
        <div class="small-text">
        The option price is calculated using the Black-Scholes model.
        This is a theoretical estimate, not a guaranteed market price.
        </div>
        """,
        unsafe_allow_html=True
    )

with right_col:
    st.subheader("Model Inputs")

    input_data = pd.DataFrame(
        {
            "Input": [
                "Stock Price",
                "Strike Price",
                "Days to Expiration",
                "Risk-Free Rate",
                "Volatility",
                "Option Type"
            ],
            "Value": [
                f"${S:.2f}",
                f"${K:.2f}",
                f"{days_to_expiration} days",
                f"{risk_free_rate_percent:.2f}%",
                f"{volatility_percent:.2f}%",
                option_type.capitalize()
            ]
        }
    )

    st.dataframe(input_data, hide_index=True, use_container_width=True)


st.divider()


st.subheader("Greeks")

greek_col1, greek_col2, greek_col3, greek_col4, greek_col5 = st.columns(5)

greek_col1.metric("Delta", f"{greeks['Delta']:.4f}")
greek_col2.metric("Gamma", f"{greeks['Gamma']:.4f}")
greek_col3.metric("Theta", f"{greeks['Theta']:.4f}")
greek_col4.metric("Vega", f"{greeks['Vega']:.4f}")
greek_col5.metric("Rho", f"{greeks['Rho']:.4f}")

with st.expander("What do these Greeks mean?"):
    st.write(
        """
        - **Delta**: How much the option price changes when the stock price changes by $1.
        - **Gamma**: How quickly Delta changes when the stock price moves.
        - **Theta**: Estimated daily time decay.
        - **Vega**: How much the option price changes when volatility changes by 1 percentage point.
        - **Rho**: How much the option price changes when interest rates change by 1 percentage point.
        """
    )


st.divider()


st.subheader("Charts")


def create_stock_price_range(current_price: float) -> list:
    lower_bound = max(current_price * 0.5, 1)
    upper_bound = current_price * 1.5
    step = (upper_bound - lower_bound) / 50

    return [lower_bound + i * step for i in range(51)]


stock_prices = create_stock_price_range(S)


payoff_rows = []

for stock_price in stock_prices:
    theoretical_price = black_scholes_price(
        S=stock_price,
        K=K,
        T=T,
        r=r,
        sigma=sigma,
        option_type=option_type
    )

    profit_loss = payoff_at_expiration(
        stock_price_at_expiration=stock_price,
        strike_price=K,
        premium=price,
        option_type=option_type
    )

    payoff_rows.append(
        {
            "Stock Price": round(stock_price, 2),
            "Theoretical Option Price": theoretical_price,
            "Profit/Loss at Expiration": profit_loss
        }
    )

payoff_df = pd.DataFrame(payoff_rows)


greek_rows = []

for stock_price in stock_prices:
    greek_values = calculate_greeks(
        S=stock_price,
        K=K,
        T=T,
        r=r,
        sigma=sigma,
        option_type=option_type
    )

    greek_rows.append(
        {
            "Stock Price": round(stock_price, 2),
            "Delta": greek_values["Delta"],
            "Gamma": greek_values["Gamma"],
            "Theta": greek_values["Theta"],
            "Vega": greek_values["Vega"]
        }
    )

greeks_df = pd.DataFrame(greek_rows)


volatility_rows = []

for vol in range(5, 101, 5):
    vol_decimal = vol / 100

    option_price_at_volatility = black_scholes_price(
        S=S,
        K=K,
        T=T,
        r=r,
        sigma=vol_decimal,
        option_type=option_type
    )

    volatility_rows.append(
        {
            "Volatility (%)": vol,
            "Option Price": option_price_at_volatility
        }
    )

volatility_df = pd.DataFrame(volatility_rows)


chart_tab1, chart_tab2, chart_tab3 = st.tabs(
    [
        "Payoff & Price",
        "Greeks Sensitivity",
        "Volatility Sensitivity"
    ]
)


with chart_tab1:
    st.write("This chart compares the theoretical option price with the profit/loss at expiration.")

    st.line_chart(
        payoff_df,
        x="Stock Price",
        y=["Theoretical Option Price", "Profit/Loss at Expiration"],
        use_container_width=True
    )

with chart_tab2:
    selected_greek = st.selectbox(
        "Select Greek",
        ["Delta", "Gamma", "Theta", "Vega"]
    )

    st.write(f"This chart shows how **{selected_greek}** changes as the stock price changes.")

    st.line_chart(
        greeks_df,
        x="Stock Price",
        y=selected_greek,
        use_container_width=True
    )

with chart_tab3:
    st.write("This chart shows how the option price changes when volatility changes.")

    st.line_chart(
        volatility_df,
        x="Volatility (%)",
        y="Option Price",
        use_container_width=True
    )


st.divider()


st.subheader("Model Notes")

st.write(
    """
    This dashboard uses the Black-Scholes model, which assumes:
    
    - European-style options
    - No early exercise
    - Constant volatility
    - Constant risk-free interest rate
    - Efficient markets
    - No transaction costs
    """
)

st.caption(
    "Educational project only. This is not financial advice."
)