# Equity Research Tool 📈

Data-driven tool for stock analysis, visualization, and AI insights via LangChain-powered chatbots. Features real-time data, web scraping Q&A, and support.

## Features
- **Stock Viz**: Interactive charts (candlestick, volume) via yfinance + Plotly.
- **Equity Chat**: LangChain AI analysis on stock metrics.
- **Web Scrape Q&A**: Paste URL (e.g., CNBC), scrape, ask questions.
- **Support Chat**: Tool assistance.

## Local Setup
1. Install deps: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, add `OPENAI_API_KEY=sk-...`
   Or for Streamlit: Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
3. Run: `streamlit run app.py`

## Usage
- Sidebar: Enter ticker (e.g., AAPL), dates → See metrics/charts.
- **Equity Tab**: Ask "Is AAPL undervalued?"
- **Web Tab**: Paste news URL, scrape, ask "What's the sentiment?"
- **Support Tab**: Help queries.

## Deploy to Streamlit Cloud 🚀
1. Push to GitHub repo (DO NOT commit secrets.toml or .env).
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → GitHub repo → Select `app.py` → Deploy.
4. In app settings: Add `OPENAI_API_KEY` in Secrets.

**Note**: Requires OpenAI API key. Free tier works.

## TODO
See [TODO.md](TODO.md)

Built with Streamlit, yfinance, LangChain, Plotly.

