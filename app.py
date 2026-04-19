import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import plotly.express as px

# Load env
load_dotenv()

# Config
st.set_page_config(page_title="Equity Research Tool", page_icon="📈", layout="wide")

# HuggingFace API key from secrets or env
api_key = st.secrets.get("HUGGINGFACEHUB_API_TOKEN")
if not api_key:
    st.error("No HUGGINGFACEHUB_API_TOKEN in secrets. Add in Streamlit Cloud settings.")
    st.stop()


# Use a better model than GPT-2 (Mistral-7B or similar)
# GPT-2 causes StopIteration errors - use a larger, more capable model
try:
    llm = HuggingFaceEndpoint(
        repo_id="mistralai/Mistral-7B-Instruct-v0.1",  # Better than GPT-2 for analysis
        huggingfacehub_api_token=api_key,
        temperature=0.3,
        max_new_tokens=512,  # Increased from 256
        repetition_penalty=1.1,  # Prevent looping
        top_p=0.95,
        top_k=50
    )
except Exception as e:
    st.error(f"Failed to initialize LLM: {e}")
    st.info("Fallback: Using a simpler model configuration")
    llm = HuggingFaceEndpoint(
        repo_id="gpt2",
        huggingfacehub_api_token=api_key,
        temperature=0.2,
        max_new_tokens=256
    )

# Sidebar
st.sidebar.header("Stock Analysis")
ticker = st.sidebar.text_input("Stock Ticker", value="AAPL").upper()
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date")

if ticker:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        info = stock.info
        
        if hist.empty:
            st.error("No data found for this ticker.")
            st.stop()
    except Exception as e:
        st.error(f"Invalid ticker or data error: {e}")
        st.stop()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Price", f"${info.get('currentPrice', 'N/A'):.2f}" if isinstance(info.get('currentPrice'), (int, float)) else "N/A")
    with col2:
        mcap = info.get('marketCap')
        st.metric("Market Cap", f"${mcap/1e9:.2f}B" if mcap else "N/A")
    with col3:
        pe = info.get('trailingPE')
        st.metric("P/E Ratio", f"{pe:.2f}" if pe else "N/A")
    with col4:
        eps = info.get('trailingEps')
        st.metric("EPS", f"{eps:.2f}" if eps else "N/A")

    # Charts
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        subplot_titles=('Price & Volume', 'Financial Metrics'),
                        row_width=[0.2, 0.7])
    fig.add_trace(go.Candlestick(x=hist.index, open=hist.Open, high=hist.High, 
                                 low=hist.Low, close=hist.Close, name='Price'), row=1, col=1)
    fig.add_trace(go.Bar(x=hist.index, y=hist.Volume, name='Volume'), row=2, col=1)
    fig.update_layout(height=600)
    st.plotly_chart(fig, width='stretch')

# Tabs for Chatbots
tab1, tab2, tab3 = st.tabs(["💹 Equity Analysis Chat", "🕷️ Web Scrape Q&A", "🆘 Support Assistant"])

with tab1:
    st.header("AI Equity Insights")
    
    if "equity_messages" not in st.session_state:
        st.session_state.equity_messages = []
    
    # Create prompt with better context
    prompt_template = """You are an expert equity analyst. Analyze this stock data and provide insightful commentary.

Stock: {ticker}
Current Price: ${price}
Market Cap: ${mcap}B
P/E Ratio: {pe}
EPS: {eps}

User Question: {input}

Provide a concise, professional analysis:"""
    
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    
    if user_input := st.chat_input("Ask about this stock..."):
        with st.chat_message("user"):
            st.write(user_input)
            st.session_state.equity_messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            try:
                with st.spinner("Analyzing..."):
                    # Safe invoke with error handling
                    response = chain.invoke({
                        "ticker": ticker, 
                        "price": f"{info.get('currentPrice', 'N/A'):.2f}" if isinstance(info.get('currentPrice'), (int, float)) else 'N/A',
                        "mcap": f"{info.get('marketCap', 0)/1e9:.2f}" if info.get('marketCap') else 'N/A',
                        "pe": f"{info.get('trailingPE', 'N/A'):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else 'N/A',
                        "eps": f"{info.get('trailingEps', 'N/A'):.2f}" if isinstance(info.get('trailingEps'), (int, float)) else 'N/A',
                        "input": user_input
                    })
                    st.write(response)
                    st.session_state.equity_messages.append({"role": "assistant", "content": response})
            except StopIteration:
                st.error("⚠️ LLM response interrupted. Try a shorter question or check your API quota.")
            except Exception as e:
                st.error(f"Error: {str(e)[:200]}")

with tab2:
    st.header("Web Scrape & Ask")
    url = st.text_input("Paste URL (e.g., CNBC article)")
    
    if st.button("Scrape & Analyze") and url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            text = ' '.join([p.get_text(strip=True) for p in paragraphs])[:3000]  # Reduced limit
            
            if not text.strip():
                st.warning("No text content found on this page.")
            else:
                st.success("✅ Scraped successfully! Ask questions below.")
                
                # Scrape Q&A chain
                scrape_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a research assistant. Answer questions accurately based on this content:\n\n{content}"),
                    ("human", "{input}")
                ])
                scrape_chain = scrape_prompt | llm | StrOutputParser()
                
                if scrape_input := st.chat_input("Ask about the page..."):
                    try:
                        with st.chat_message("user"):
                            st.write(scrape_input)
                        with st.chat_message("assistant"):
                            with st.spinner("Analyzing..."):
                                resp = scrape_chain.invoke({"content": text, "input": scrape_input})
                                st.write(resp)
                    except StopIteration:
                        st.error("⚠️ LLM interrupted. Try a simpler question.")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:200]}")
        except requests.exceptions.RequestException as e:
            st.error(f"Scrape failed: {str(e)[:200]}")
        except Exception as e:
            st.error(f"Error: {str(e)[:200]}")
    
    st.info("💡 Example: Paste CNBC stock news URL, ask 'What is the current price mentioned?'")

with tab3:
    st.header("Support Assistant")
    
    if "support_messages" not in st.session_state:
        st.session_state.support_messages = []
    
    support_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful support assistant for the Equity Research Tool. Help with usage, features, and troubleshooting. Be concise and practical."),
        ("human", "{input}")
    ])
    support_chain = support_prompt | llm | StrOutputParser()
    
    if support_input := st.chat_input("How can I help you?"):
        with st.chat_message("user"):
            st.write(support_input)
        try:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    resp = support_chain.invoke({"input": support_input})
                    st.write(resp)
                    st.session_state.support_messages.append({"role": "assistant", "content": resp})
        except StopIteration:
            st.error("⚠️ LLM interrupted. Please try again.")
        except Exception as e:
            st.error(f"Error: {str(e)[:200]}")

# Footer
st.divider()
st.caption("⚠️ This tool is for educational purposes. Not financial advice. Always consult a financial advisor.")