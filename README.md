# portfolio-thesis-analyzer

Portfolio Thesis Analyzer is a finance and FinTech application prototype designed to help investors explore how individual stock selections and portfolio weights influence overall investment performance and risk.

<img width="2000" height="1143" alt="image" src="https://github.com/user-attachments/assets/c2b202af-a36e-42d4-a4f0-fa1cfba80970" />

The central visualization will plot cumulative returns over time: thin colored lines for individual securities and a thick red line for the combined portfolio. Users will be able to compare portfolios, inspect diversification, and generate a concise investment thesis grounded in the calculated metrics.

Course assignment: Building a Finance or FinTech Application Using AI Coding Agents
Selected topic: Project 2 — Investment Portfolio Risk Analyzer, extended with an investment thesis summary.

Financial Problem

Investors can focus too heavily on the returns of individual stocks while overlooking concentration, correlations, volatility, and portfolio-level drawdowns. This application will make those relationships easier to see and interpret.

Planned Features

• Select at least three stocks or exchange-traded funds (ETFs) by ticker symbol.
• Assign investment amounts or portfolio weights; start with equal weighting by default.
• Visualize historical cumulative returns of individual securities alongside the combined portfolio.
• Adjust portfolio composition and weights and observe changes in the results.
• Calculate annualized return, annualized volatility, Sharpe ratio, and maximum drawdown.
• Analyze correlations between securities and show a correlation heatmap.
• Compare portfolio performance against a benchmark such as SPY.
• Generate a concise, data-supported investment thesis describing potential strengths, diversification benefits, and risks.
• Handle invalid tickers, incomplete data, and unavailable API responses gracefully.

Proposed Dashboard Layout

1. Controls: Ticker selection, portfolio weights, and historical period.
2. Main chart: Individual cumulative-return lines and a prominent portfolio-return line.
3. Risk dashboard: Return, volatility, Sharpe ratio, and maximum drawdown.
4. Supporting charts: Allocation breakdown and correlation heatmap.
5. Investment thesis: A readable summary supported by the displayed metrics.

The reference visualization uses a five-year cumulative-return chart with individual securities in thin lines and the aggregate portfolio in a thick red line. The actual application will calculate correlations from historical return data. Any adjustable-correlation experiment will be clearly labeled as a simulation, not as observed market data.

Planned Financial Methodology

Let (r_{i,t}) denote the return of security (i) in period (t), and (w_i) its portfolio weight.

• Portfolio return: (r_{p,t} = \sum_i w_i r_{i,t}), assuming specified rebalancing rules.
• Cumulative return: Compound periodic portfolio returns to obtain a growth-of-$1 series.
• Annualized volatility: Standard deviation of daily portfolio returns multiplied by (\sqrt{252}).
• Annualized return: Compound returns over the observed period and annualize based on the observation horizon.
• Sharpe ratio: Annualized excess return divided by annualized volatility, using a documented risk-free-rate assumption.
• Maximum drawdown: Largest percentage decline from a previous portfolio-value peak.
• Correlation: Pairwise correlation of aligned periodic security returns.

The implementation will document assumptions about dividends, adjusted prices, missing observations, rebalancing frequency, trading calendars, and transaction costs.

Technology Stack (Planned)

|Component                |Planned Technology                                         |
|-------------------------|-----------------------------------------------------------|
|Application              |Python + Streamlit                                         |
|Data processing          |pandas + NumPy                                             |
|Visualization            |Plotly                                                     |
|Market data              |Finnhub API and/or a permitted free historical-price source|
|Risk-free rate (optional)|FRED                                                       |
|AI coding agent          |OpenAI Codex                                               |
|Version control          |GitHub                                                     |

Data sources and free-tier endpoint availability will be verified before implementation. API credentials will be stored in environment variables or local secrets, never committed to this repository.

Installation and Running the Application

Not available yet. Once the first runnable prototype is committed, this section will provide verified steps for cloning the repository, installing dependencies from requirements.txt, configuring API access, and launching the Streamlit application.

The anticipated launch command is:

streamlit run app.py

This command will work after app.py and the required dependencies are added.

AI-Assisted Development

The project is intended to be developed iteratively using OpenAI Codex to help scaffold the application, implement financial calculations, integrate data APIs, debug issues, and improve the user interface. AI-generated code and analysis will be reviewed and tested rather than assumed correct. This section will be updated to describe the actual development process.

Validation Plan

• Compare portfolio return calculations against independently computed examples.
• Confirm that portfolio weights sum to 100% or are normalized transparently.
• Check the annualization convention and benchmark alignment.
• Test invalid ticker symbols, missing historical prices, and API errors.
• Confirm that charts and thesis statements reflect the selected securities and data period.
• Distinguish historical observations from hypothetical scenarios and forward-looking interpretations.

Limitations

Historical returns do not guarantee future performance. Correlation relationships can change over time, and diversification does not eliminate market risk. Financial data may be delayed, incomplete, or subject to provider restrictions. An automatically generated investment thesis is an analytical aid, not personalized financial advice.

Development Roadmap

☑ Define the financial problem and application concept.
☑ Create the GitHub repository and initial README.
☐ Verify accessible historical market-data endpoints.
☐ Implement ticker selection and portfolio weights.
☐ Build the interactive cumulative-return chart.
☐ Implement portfolio risk metrics and benchmark comparison.
☐ Add allocation and correlation visualizations.
☐ Add the data-supported investment thesis summary.
☐ Add tests, error handling, and reproducible setup instructions.
☐ Include at least two screenshots of the working application.
☐ Demonstrate the working prototype.

Repository Deliverables (Upon Completion)

The completed repository will contain application source code, requirements.txt, setup and run instructions, API documentation, descriptions of financial calculations, at least two screenshots, notes on AI-agent usage, and known limitations.

Disclaimer

For educational purposes only. Not investment advice.
