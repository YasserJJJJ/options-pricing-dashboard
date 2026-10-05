# Options Pricing Dashboard

An interactive dashboard for European option pricing and risk analysis. A responsive HTML/CSS/JavaScript frontend calls the original Python pricing engine through a Vercel Function. The frontend and API deploy together from this repository.

[![Tests](https://github.com/YasserJJJJ/options-pricing-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/YasserJJJJ/options-pricing-dashboard/actions/workflows/tests.yml)

## Features

- Black–Scholes prices for European calls and puts
- Delta, Gamma, Theta, Vega, and Rho
- Implied volatility with adaptive bisection and theoretical-price validation
- Reproducible Monte Carlo pricing, standard error, and 95% confidence intervals
- Payoff, Greek, and volatility sensitivity charts with hover values and data tables
- CSV export including the calculated scenario, risk metrics, simulation results, and selected chart
- Responsive mobile layout, keyboard-accessible chart tabs, and explicit loading/error states

## Architecture

| File | Purpose |
| --- | --- |
| `black_scholes.py` | Original pricing formulas and numerical algorithms |
| `dashboard.py` | Input validation and scenario/chart response preparation |
| `api/calculate.py` | Vercel Python function, `POST /api/calculate` |
| `public/index.html` | Dashboard interface |
| `public/styles.css` | Responsive styling |
| `public/dashboard.js` | API requests, charts, tabs, and CSV export |
| `app.py` | Local server for the same frontend and API |
| `vercel.json` | Static output, Python function settings, and response headers |
| `tests/` | Numerical and HTTP/API regression tests |

The production runtime uses the Python standard library only. No API keys, database, JavaScript build step, or separately hosted backend are needed. Streamlit and its dependencies have been removed.

## Run locally

Requires Python 3.12 or later:

```bash
git clone https://github.com/YasserJJJJ/options-pricing-dashboard.git
cd options-pricing-dashboard
python3 app.py
```

Open <http://localhost:3000>. Results update when you click **Calculate scenario**. Changing inputs marks previous results as stale until you recalculate. Exports always use the calculated scenario.

## Deploy on Vercel

Import `YasserJJJJ/options-pricing-dashboard` into Vercel:

- Framework preset: **Other**
- Root directory: repository root
- Output directory: **public** (configured in `vercel.json`)
- No build command or environment variables required

Vercel serves the interface as static files and runs `api/calculate.py` on demand. The project does not rely on a long-running UI server. Deployment protection, plan limits, and platform availability still apply.

Alternatively, from a linked local checkout:

```bash
npx vercel --prod
```

## API

`GET /api/calculate` returns a health response. `POST /api/calculate` accepts JSON:

```json
{
  "option_type": "call",
  "stock_price": 100,
  "strike_price": 100,
  "days": 30,
  "rate_percent": 5,
  "volatility_percent": 20,
  "market_price": 2.5,
  "simulations": 20000,
  "seed": 42
}
```

Missing fields use the example defaults. Rates and volatility are percentages. The response includes the validated inputs, analytical price, five Greeks, Monte Carlo statistics, implied volatility (or a warning), break-even price, and sensitivity arrays. Invalid model inputs return HTTP 400; an invalid observed price returns a successful pricing response with `implied_volatility: null` and `iv_error`, so the remaining dashboard stays usable.

Requests are limited to 8 KB and at most 50,000 simulations. Prices must be positive and at most $1,000,000; expiry is 1–3,650 whole days; volatility is 0.01–300%; interest rate is −20–100%; the seed is a whole number between 0 and 1,000,000.

## Testing

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest --cov=black_scholes --cov-branch --cov-report=term-missing --cov-fail-under=95
```

The suite covers model values, Greeks, put–call parity, implied-volatility edge cases, seeded simulations, input validation, JSON/HTTP errors, and consistency between API/chart outputs and the original engine. GitHub Actions runs the suite on pushes and pull requests.

## Model assumptions

European exercise, no dividends, constant volatility and risk-free rate, lognormal stock prices, and no transaction costs. Time uses a 365-day year. Prices are per share in USD; multiply by the applicable contract size separately. Payoff charts show long-option profit/loss at expiry after subtracting the theoretical premium. Monte Carlo intervals measure simulation uncertainty, not market-price prediction uncertainty.

Educational and portfolio project only; not financial advice.
