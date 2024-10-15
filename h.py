# 保存為 app.py

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib
from matplotlib.font_manager import FontProperties

# 設置支持中文的字體
# 方法一：使用系統已安裝的字體
matplotlib.rcParams['font.family'] = 'SimHei'  # 或 'Noto Sans CJK'
matplotlib.rcParams['axes.unicode_minus'] = False  # 確保負號顯示正確

# 方法二：使用自定義字體（若方法一無法顯示中文）
# font_path = "fonts/NotoSansCJK-Regular.ttc"  # 相對路徑
# font_prop = FontProperties(fname=font_path, size=12)
# matplotlib.rcParams['font.family'] = font_prop.get_name()
# matplotlib.rcParams['axes.unicode_minus'] = False  # 確保負號顯示正確

# 設置應用標題
st.title("多股票回測系統")

# 說明文字
st.write("""
    請輸入多支台灣股市代號，並選擇一支基準股票進行回測比較。
    您可以輸入多支股票代號，使用逗號分隔，例如：2330,2317,2412
""")

# 使用者輸入
symbols_input = st.text_input("請輸入多支台灣股市代號（用逗號分隔）:", "2330,2317,2412")
benchmark_input = st.text_input("請輸入用於對比的台灣股市代號:", "0050")

# 新增日期選擇功能
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
        # 使用 pd.concat 合併所有股票的數據
        portfolio_data = pd.concat(portfolio_data_list)
        portfolio_data.reset_index(inplace=True)

        # 透過 Pivot 表將數據整理為以日期為索引，股票代號為列的收盤價
        pivot_close = portfolio_data.pivot(index='Date', columns='Symbol', values='Close')

        # 處理缺失值（如有）
        pivot_close.fillna(method='ffill', inplace=True)
        pivot_close.dropna(inplace=True)

        # 計算每日收益率
        returns = pivot_close.pct_change()

        # 計算組合的平均每日收益率（等權重）
        portfolio_returns = returns.mean(axis=1)

        # 獲取基準股票的歷史數據
        benchmark_data = fetch_stock_data(benchmark_symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))

        if benchmark_data is not None and not benchmark_data.empty:
            # 計算基準股票的每日收益率
            benchmark_returns = benchmark_data['Close'].pct_change()

            # 對齊日期索引
            portfolio_returns = portfolio_returns.loc[benchmark_returns.index]
            benchmark_returns = benchmark_returns.loc[portfolio_returns.index]

            # 計算累積收益
            portfolio_cumulative_returns = (1 + portfolio_returns).cumprod()
            benchmark_cumulative_returns = (1 + benchmark_returns).cumprod()

            # 繪製累積收益曲線
            fig, ax = plt.subplots(figsize=(14,7))
            ax.plot(portfolio_cumulative_returns, label='投資組合累積收益')
            ax.plot(benchmark_cumulative_returns, label=f'{benchmark_input} 累積收益')
            ax.set_title('投資組合與基準股票累積收益對比', fontsize=16)
            ax.set_xlabel('日期', fontsize=14)
            ax.set_ylabel('累積收益', fontsize=14)
            ax.legend(prop={'size': 12})
            ax.grid(True)
            st.pyplot(fig)

            # 計算總收益
            total_portfolio_return = portfolio_cumulative_returns[-1] - 1
            total_benchmark_return = benchmark_cumulative_returns[-1] - 1

            # 顯示回測結果
            st.write(f"**投資組合總收益:** {total_portfolio_return * 100:.2f}%")
            st.write(f"**{benchmark_input} 總收益:** {total_benchmark_return * 100:.2f}%")

            # 計算每月獲利百分比
            portfolio_monthly = portfolio_cumulative_returns.resample('M').last().pct_change().dropna() * 100
            benchmark_monthly = benchmark_cumulative_returns.resample('M').last().pct_change().dropna() * 100

            # 合併數據
            monthly_returns_df = pd.DataFrame({
                '日期': portfolio_monthly.index.strftime('%Y-%m'),
                '投資組合月獲利%': portfolio_monthly.values,
                f'{benchmark_input} 月獲利%': benchmark_monthly.values
            })

            # 顯示每月獲利數據表
            st.write("### 每月獲利百分比比較")
            st.dataframe(monthly_returns_df.style.format({
                '投資組合月獲利%': "{:.2f}",
                f'{benchmark_input} 月獲利%': "{:.2f}"
            }))

        else:
            st.error(f"無法取得基準股票 {benchmark_input} 的資料。請檢查股票代號是否正確或該股票是否已退市。")
