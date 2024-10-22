import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
from matplotlib.font_manager import FontProperties
import os

# 設置應用標題
st.title("邦的股市回測系統")

# 說明文字
st.write("""
    請輸入多支台灣股市代號，並選擇一支基準股票進行回測比較。
    您可以輸入多支股票代號，使用逗號分隔，例如：2330,2317,2412
""")

# 使用者輸入
symbols_input = st.text_input("請輸入多支台灣股市代號（用逗號分隔）:", "2330,2317,2412")
benchmark_input = st.text_input("請輸入用於對比的台灣股市代號:", "0050")

# 新增日期選擇功能，標籤使用中文
st.write("### 選擇回測的日期範圍")
default_end_date = datetime.today()
default_start_date = default_end_date - timedelta(days=730)  # 預設過去兩年

start_date = st.date_input("開始日期", default_start_date)
end_date = st.date_input("結束日期", default_end_date)

# 確保開始日期不晚於結束日期
if start_date > end_date:
    st.error("開始日期不能晚於結束日期。請重新選擇日期。")

# 按鈕觸發回測
if st.button("開始回測"):
    # 定義函數以獲取單個股票的歷史數據
    def fetch_stock_data(symbol, start_date, end_date):
        try:
            stock = yf.download(symbol, start=start_date, end=end_date)
            if stock.empty:
                st.warning(f"未能獲取到 {symbol} 的數據。請檢查股票代號是否正確或該股票是否已退市。")
                return None
            stock.reset_index(inplace=True)  # 重置索引，將日期變成一個欄位
            stock['Symbol'] = symbol
            return stock
        except Exception as e:
            st.error(f"獲取 {symbol} 數據時出錯。錯誤信息：{e}")
            return None

    # 處理股票代號輸入，替換全角逗號為半角逗號，並分割
    symbols_list = [symbol.strip() + ".TW" for symbol in symbols_input.replace('，', ',').split(",")]

    # 處理基準股票代號
    benchmark_symbol = benchmark_input.strip() + ".TW"

    # 定義日期範圍（根據使用者選擇）
    end_date_dt = datetime.combine(end_date, datetime.min.time())
    start_date_dt = datetime.combine(start_date, datetime.min.time())

    # 獲取多支股票的歷史數據
    portfolio_data_list = []

    for symbol in symbols_list:
        data = fetch_stock_data(symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))
        if data is not None:
            portfolio_data_list.append(data)

    # 檢查是否有有效的數據
    if not portfolio_data_list:
        st.error("未能獲取到任何有效的投資組合股票數據。請檢查股票代號並重試。")
    else:
        # 使用 pd.concat 合併所有股票的數據，忽略索引
        portfolio_data = pd.concat(portfolio_data_list, ignore_index=True)

        # 顯示欄位名稱以進行調試
        st.write("投資組合資料的欄位名稱：", portfolio_data.columns.tolist())

        # 確保 'Date' 欄位為 datetime 類型
        portfolio_data['Date'] = pd.to_datetime(portfolio_data['Date'])

        # 檢查必要的欄位是否存在
        required_columns = ['Date', 'Symbol', 'Close']
        missing_columns = [col for col in required_columns if col not in portfolio_data.columns]
        if missing_columns:
            st.error(f"資料缺少以下欄位：{missing_columns}")
        else:
            # 移除缺失值
            portfolio_data.dropna(subset=required_columns, inplace=True)

            # 移除重複的日期和股票代號組合，保留第一筆記錄
            portfolio_data = portfolio_data.drop_duplicates(subset=['Date', 'Symbol'], keep='first')

            # 使用 pivot_table 並指定聚合函數
            pivot_close = portfolio_data.pivot_table(index='Date', columns='Symbol', values='Close', aggfunc='mean')

            # 處理缺失值（如有
