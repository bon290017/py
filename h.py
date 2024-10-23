import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import datetime
import numpy as np

# 此代碼會利用 Yahoo Finance API 獲取股票資料

def get_stock_data(ticker, start, end):
    stock = yf.Ticker(ticker)
    data = stock.history(start=start, end=end)
    return data

def combine_stocks(tickers, start, end):
    combined_data = None
    for ticker in tickers:
        data = get_stock_data(ticker, start, end)['Close']
        data = data.rename(ticker)
        if combined_data is None:
            combined_data = data
        else:
            combined_data += data
    combined_data /= len(tickers)  # 合成經平均的統一資料
    return combined_data

# Streamlit 主程序
st.title('Taiwan Stock Backtesting System')

# 設定選擇股票代碼
stock_symbols = st.text_input('Enter stock symbols (comma separated)', '2330.TW, 2317.TW')
benchmark_symbol = st.text_input('Enter benchmark stock symbol', '0050.TW')

# 選擇回歸期間
start_date = st.date_input('Start date', datetime.date(2020, 1, 1))
end_date = st.date_input('End date', datetime.date.today())

if st.button('Run Backtest'):
    symbols = [symbol.strip() for symbol in stock_symbols.split(',')]
    benchmark = benchmark_symbol.strip()

    # 獲取並合成策略數據
    strategy_data = combine_stocks(symbols, start_date, end_date)
    benchmark_data = get_stock_data(benchmark, start_date, end_date)['Close']

    # 策略數據和標準比較圖表
    fig, ax = plt.subplots()
    ax.plot(strategy_data.index, strategy_data, label='Strategy', color='blue')
    ax.plot(benchmark_data.index, benchmark_data, label=benchmark, color='red')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.set_title('Stock Backtesting Comparison')
    ax.legend()
    st.pyplot(fig)

    # 計算平均收益率和平均市場相關性
    strategy_return = strategy_data.pct_change().mean() * 252
    benchmark_return = benchmark_data.pct_change().mean() * 252
    correlation = np.corrcoef(strategy_data.pct_change()[1:], benchmark_data.pct_change()[1:])[0, 1]

    st.write(f"Average Strategy Return: {strategy_return:.2%}")
    st.write(f"Average Benchmark Return: {benchmark_return:.2%}")
    st.write(f"Correlation between Strategy and Benchmark: {correlation:.2f}")

# GitHub 鏈接
st.markdown("[View Source Code on GitHub](https://github.com/yourusername/yourrepository)")
