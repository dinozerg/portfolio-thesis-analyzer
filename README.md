# Portfolio Thesis Analyzer

**FIN 471 — Project: Investment Portfolio Risk Analyzer**

![Working Portfolio Thesis Analyzer: holdings, allocations, and historical performance](screenshots/chart-first.png)

A local, interactive finance prototype that shows how securities and allocations
change portfolio performance and risk. It addresses the financial problem of
underestimating individual-security risk and portfolio concentration. Users can
compare allocations and evaluate historical returns, volatility, risk-adjusted
performance, and losses against SPY before forming their own investment thesis.
The screenshot above shows the working application using **real historical data**.
Below the main chart, the result shows what a hypothetical **$10,000 starting investment** became,
the dollar gain or loss, the total percentage return, and the same investment in
SPY. Values update whenever the holdings, weights, or dates change. This is a
historical illustration before fees and taxes, not a forecast. Dollar amounts in
the headline are rounded to whole dollars.

## Run it

Install Python 3.12 and Git. In a terminal, clone the repository and enter its folder:

```powershell
git clone https://github.com/dinozerg/portfolio-thesis-analyzer.git
cd portfolio-thesis-analyzer
```

Python 3.12 is tested. From that folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8501**. On the original development computer, the environment
is already installed: double-click **Start Portfolio.bat**. It opens the browser
after the server starts, or reopens the app if it is already running. Keep the terminal open;
Ctrl+C stops the server. On macOS/Linux use `.venv/bin/python` in place of
`.venv\Scripts\python.exe`. Recreate .venv rather than copying it between computers.

The redesign uses a small custom HTML/CSS/JavaScript interface and Python's built-in
HTTP server. **Streamlit is no longer required, and `streamlit run app.py` is no
longer the launch command.** No Node install/build, account, database, API key, or
paid AI API is required. Plotly JavaScript is served locally from the installed
Python package. Internet access is needed to search and download market data.

## The intended interaction

1. Type a company name (such as Tesla) or ticker in **Add a stock or ETF**.
   Search queries Yahoo Finance; results show company name, ticker, and exchange.
   Click **+ Add** on a result to add exactly that security. A confirmation names
   its starting allocation, its holdings row is marked NEW, and its chart line is
   automatically highlighted. It is not limited to the random
   selection universe. Search supports US-listed equities and ETFs only.
2. The new holding receives 1/(new holding count) of starting capital. Existing
   weights scale proportionally into the remaining allocation. For example,
   40/35/25 becomes 30/26.25/18.75/25 after adding a fourth stock.
3. Starting allocation percentages are always visible in the holdings table.
   Edit them directly. Changes are **drafts** until their sum is exactly 100% and
   you click **Apply weights**. The chart and risk measures retain the last applied
   portfolio in the meantime; the interface labels this explicitly. Other portfolio
   actions are disabled during a draft. Cancel discards edits.
4. For the assignment example, set AAPL to 40, MSFT to 35, and SPY to 25, then Apply.
   No automatic normalization changes those requested percentages.
5. **Equal weight** resets all starting allocations. The x beside a holding removes
   it and redistributes the allocation proportionally to the remaining holdings.
   At least one holding must remain; a prompt reminds you to use at least three
   for the assignment. Zero allocations are allowed, but the total must be 100%.
6. The **Number of holdings** slider follows the actual portfolio count after
   loading, adding, removing, or generating holdings. To size a new random mix,
   move the slider, then click **Generate random mix**.
   This replaces the portfolio with 1–30 unique US equities and equal allocations.
   One stock receives 100%; correlation is N/A until at least two holdings have
   positive allocations. The assignment reminder to use at least three remains.
   Moving the slider alone does not change the current holdings. While its value
   differs from the portfolio, the hint explicitly shows both the actual count
   and the next random-mix size. The holdings panel always shows the actual count.
7. Choose **1 year**, **2 years**, or **5 years**. Start/end dates are always visible
   and automatically show the actual common trading dates used by that preset.
   They update if adding or removing a holding changes the available common history.
   For a different range, use the separate **Custom dates** button, enter a start
   and end date, and click **Apply range**. Both dates are inclusive. Weekends and
   holidays use only available trading dates within the chosen range. The chart,
   returns, risk measures, and SPY comparison all use the same common dates and
   restart at $1 on the first common observation. At least three common prices
   are needed. Future dates and reversed ranges are rejected. Date edits leave
   the last applied chart intact until Apply; Cancel restores the applied range.
   Adding holdings or editing weights preserves the applied date range.
   See risk, allocation, and benchmark comparison
   immediately below the main chart. Average correlation is a read-only number
   card with a short explanation of −1, 0, and +1; it has no slider or editable control.
8. Hover a performance line to make it stand out and show its ticker, date, growth,
   and return. Click a line or ticker in the holdings table to keep it highlighted.
   Click it again, choose **Clear selection** above the chart, or press Escape to clear the selection.
   Highlighting only changes the display, never the allocations or calculations.

Allocation percentages have two-decimal precision and sum to exactly 100.00%.
Equal weights use largest-remainder rounding (e.g. 33.34/33.33/33.33) so displayed
percentages match the calculations. A failed search/add/download leaves the last
successful portfolio intact. Nothing is traded or sent to a brokerage.

## Requirement coverage

| Project feature | Implementation |
|---|---|
| Select at least three stocks or ETFs | Live company/ticker search, defaults to AAPL/MSFT/SPY, supports up to 30 |
| Investment amounts or portfolio weights | Always-visible editable starting weights and explicit Apply |
| Portfolio returns | Buy-and-hold growth series, total period return, growth of $10,000 |
| Annualized volatility | Sample daily return standard deviation × sqrt(252) |
| Sharpe ratio | Mean daily excess return / sample daily volatility × sqrt(252) |
| Maximum drawdown | Worst decline from a running peak, including initial capital |
| Allocation and performance charts | Starting allocation donut; individual/portfolio performance lines |
| Market benchmark | SPY dashed line and same-period risk/return comparison |

The selected FIN 471 topic is **Investment Portfolio Risk Analyzer**. The app
also addresses the assignment-wide requirements:

| Class requirement | Evidence in this repository |
|---|---|
| Executable, interactive prototype | Python HTTP server and browser UI; installation and launch commands above |
| External financial API without a paid subscription | Yahoo Finance search and adjusted daily prices through `yfinance`; no API key required |
| At least three financial calculations | Total return, annualized volatility, Sharpe ratio, and maximum drawdown in `portfolio.py` |
| At least two relevant visualizations | Historical performance line chart and starting-allocation donut chart |
| Invalid inputs, missing data, and API failures | Validation, common-date alignment, visible errors, and explicitly labeled matching-cache fallback |
| Reproducibility and documentation | Pinned dependencies, setup instructions, formulas, data assumptions, limitations, and tests |
| AI coding agent | OpenAI Codex; development and validation described below |
| At least two working-app screenshots | Opening performance screenshot plus the risk/allocation screenshot below |
| GitHub submission and demonstration | Repository URL below; demonstration walkthrough below for the student to present |

## Class demonstration walkthrough

1. Launch the app and show AAPL, MSFT, and SPY. Keep at least three holdings
   during the class demonstration, even though the app also permits smaller
   portfolios for comparison.
2. Set starting weights to **40%, 35%, and 25%**, then click **Apply weights**.
   Show the historical dates and explain the buy-and-hold assumption.
3. Show the performance chart and the $10,000 outcome alongside SPY. Explain
   that the displayed return is for the full period, not an annualized return.
4. Scroll to the allocation donut and risk measures. Explain volatility,
   Sharpe ratio, maximum drawdown, and the editable risk-free assumption.
5. Change the weights or date range and describe how the results change.
   Search for another company and add it to demonstrate external API interaction.
6. Enter weights that do not total 100% to show validation. Explain how missing
   prices and provider outages are handled and why past performance is not a forecast.

Submit https://github.com/dinozerg/portfolio-thesis-analyzer and demonstrate
the running app as required by the instructor. Public hosting is not specified
in the supplied assignment; a local demonstration requires the app to be running
on the presenting computer. Fixed custom dates and identical weights make a
comparison repeatable, subject to provider revisions to historical prices.

## Working application screenshots

![Risk and allocation](screenshots/risk-allocation.png)

## Files

- `app.py`: HTTP entry point, static assets and JSON routes; defaults to loopback only.
- `web/index.html`, `web/styles.css`, `web/main.js`: browser interface.
- `service.py`: validates state, changes allocations, assembles financial results.
- `portfolio.py`: price alignment, buy-and-hold calculations, and risk metrics.
- `market_data.py`: historical download, live search, and caching.
- `test_app.py`, `test_portfolio.py`: deterministic application/calculation tests.
- `requirements.txt`: pinned Python dependencies.

Local routes: `GET /api/search?q=company`, `POST /api/analyze`, and `GET /health`.
`/api/analyze` takes holdings, integer allocation basis points totaling 10,000,
period (`1y`, `2y`, `5y`, or `custom`), annual risk-free assumption, and an optional action.
Custom ranges also require `start_date` and `end_date` in YYYY-MM-DD form. Invalid requests
return a descriptive error; changes are committed to the UI only on success.
The built-in server is appropriate for this local prototype, not a production
multi-user hosting configuration. Public deployment remains a separate step.

## Data APIs

The app uses [yfinance](https://github.com/ranaroussi/yfinance), an unofficial client
for Yahoo Finance's market-data APIs:

The assignment allows an alternative historical-price source; Finnhub is suggested,
not mandatory. Live downloads and company search were successfully checked on
October 29, 2026, without an API key or paid subscription. The
[yfinance documentation](https://ranaroussi.github.io/yfinance/) identifies the
tool as intended for research and education and the Yahoo Finance API as intended
for personal use. This is a local educational prototype; that access should not
be read as permission to redistribute a market-data service.

- [`Search`](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Search.html)
  searches company names/tickers and returns listings. Results are filtered to
  supported US stock/ETF exchanges; news and unrelated assets are omitted.
- [`download`](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
  retrieves daily historical prices, `auto_adjust=True`, for 1-, 2-, or 5-year
  periods or explicit start/end dates. The UI's inclusive end date is translated
  to yfinance's exclusive end date by adding one calendar day. The same source supplies SPY.

Search and successful price responses are cached in memory for one hour. Successful
price downloads are also saved locally in ignored `.cache/` files. During outages,
only the identical requested symbol set and period (including both custom dates)
can use that snapshot; a warning
and original retrieval timestamp identify it. There is no synthetic substitution.
Refresh prices bypasses memory caching. Changed provider adjustments or retrieval
dates can change results; no guarantee of bit-for-bit future data reproducibility.

**Data rights:** yfinance's documentation describes personal research/educational
use and warns that Yahoo Finance data is intended for personal use. Availability
without a key is not a redistribution license. Public display rights are not yet
established; confirm terms or replace the adapter with a permitted source before
publishing. Code licensing and market-data rights are separate.

## Financial concepts and formulas

For aligned adjusted price P(i,t), growth G(i,t) = P(i,t)/P(i,0).
Portfolio growth V(t) = sum(w(i) × G(i,t)), where w are the applied starting
weights summing to one. This is fractional-share **buy and hold**, not daily
rebalancing. Actual holdings' weights drift as prices change; the editor and donut
show starting allocations only. Adjusted close incorporates provider-reported
split and dividend adjustments, approximating reinvested distributions.

- Daily portfolio return: r(t) = V(t)/V(t-1) - 1.
- Total return: V(T)/V(0) - 1. This is the total over the displayed dates, not an
  annual return. The chart shows the dollar value of a $1 starting investment:
  $1.50 means a 50-cent gain, or a 50% total return. The headline scales the same
  portfolio series to a $10,000 starting investment and shows the dollar profit/loss.
- Annualized volatility: sample std(r), ddof=1, × sqrt(252).
- Daily risk-free rate: (1 + annual rate)^(1/252) - 1.
- Sharpe: mean(r − daily risk-free rate) / sample std(r) × sqrt(252).
  The default annual rate is an explicitly editable 0% simplifying assumption,
  not a live Treasury yield. Zero volatility gives N/A.
- Maximum drawdown: min(V(t)/running_max(V through t) − 1), including V(0).
  It is displayed as a negative loss.
- Correlation: unweighted mean of finite pairwise daily-return correlations among
  positive-weight holdings. It is historical, not user-specified or a forecast.
  Fewer than two eligible holdings yields N/A. Not a weighted covariance measure.
- SPY: identical calculations on exactly the same common dates. It may also be a
  holding; the benchmark series does not add an extra portfolio allocation.

No forward filling. Only dates with valid positive prices for every selected
holding and SPY are retained. Short-history stocks shorten the common window.
Missing interior dates can cause returns to span more than one trading day, so
252-observation annualization is then approximate. Actual dates, excluded counts,
and source timestamp are displayed. Latest bars may be provisional during trading.

The random equity universe is AAPL, MSFT, NVDA, AMZN, GOOGL, META, JPM, V, JNJ, UNH,
PG, KO, PEP, WMT, COST, XOM, CVX, CAT, HD, DIS, NFLX, ADBE, CRM, CSCO, INTC, AMD,
TXN, MCD, NKE, IBM. It is a convenience sample, not an optimized recommendation.
Company search is broader than this list. No currency conversion is implemented.

## Verification and AI-agent use

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Tests cover independent hand-worked returns, buy and hold versus rebalancing,
volatility and Sharpe, drawdown including initial capital, zero volatility,
risk-free assumptions, missing prices, cache fallback, exact 40/35/25 allocations,
add/remove redistribution, weight rounding, failed-request state preservation,
random uniqueness, one-stock portfolios, inclusive custom-date boundaries,
invalid/insufficient date ranges, rebasing to the selected window, date-specific
cache isolation, and filtering company-search results.

Validation on October 29, 2026: **26 automated tests passed**. A separate live
API check retrieved 251 aligned daily observations for the one-year AAPL/MSFT/SPY
40/35/25 example, calculated all four required return/risk measures, and confirmed
company search returned results. The price response was fresh, not an outage-cache
fallback. The local server, interface, and Plotly asset returned successful HTTP
responses, and the running browser displayed both charts and the FIN 471 footer.
The two screenshots displayed in this README were refreshed from that running app.
These checks do not replace the student's working application demonstration.

OpenAI Codex implemented and iterated on the app from the user's README, assignment,
and screenshot. The first version used Streamlit; user feedback prompted a custom
interface for closer visual fidelity, real company search, and a clearer weight
editor. Code was executed, calculation tests run, and browser flows checked against
real downloaded data. AI output was validated rather than accepted on trust.

## Limitations and submission status

All source, dependency instructions, methodology, API notes, AI-use explanation,
and working-app screenshots are committed to GitHub. The student still needs to
submit the repository URL and present the working demonstration. No public hosted
demo is provided. Never upload .venv, .cache, logs, or credentials.

This is historical educational analysis: no fees, taxes, slippage, cash flows,
transaction execution, persistent user accounts, or guaranteed data availability.
Survivorship and selection bias apply. API limits/outages and data revisions can
affect results. Optional AI-written investment theses and synthetic correlation
simulation are not implemented; the selected project does not require them.
Screenshots illustrate the running prototype; displayed values can differ when
the selected dates or provider data change.

Historical performance is not a prediction or personalized investment advice.

The story below the chart identifies the first close above starting capital, the last recovery above starting capital, the worst peak-to-trough decline and its recovery date. These are observed milestones, not an inferred cause of growth. An optional personal thesis note and loss-tolerance input provide context; they stay in the tab and reset on reload. The tolerance comparison is historical only, not a suitability assessment. Random selections are explicitly labeled as experiments without an investor-specific thesis.
