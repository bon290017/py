import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timedelta
import os

# 設置支援中文的字體（如果需要在其他圖表中使用）
def get_font_properties(font_size=12):
    font_path = os.path.join("fonts", "NotoSansTC-SemiBold.ttf")
    if os.path.exists(font_path):
        try:
            from matplotlib.font_manager import FontProperties
            font_prop = FontProperties(fname=font_path, size=font_size)
            return font_prop
        except Exception as e:
            st.warning(f"加載字體時出錯：{e}。將使用默認字體。")
            return None
    else:
        st.warning("未找到自定義中文字體文件。將使用默認字體。")
        return None

# 定義函數以獲取股票的歷史數據
def fetch_stock_data(symbol, start_date, end_date):
    try:
        stock = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if stock.empty:
            st.warning(f"未能獲取到 {symbol} 的數據。請檢查股票代號是否正確或該股票是否已退市。")
            return None
        stock['Symbol'] = symbol
        stock.reset_index(inplace=True)
        return stock
    except Exception as e:
        st.error(f"獲取 {symbol} 數據時出錯。錯誤信息：{e}")
        return None

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
    # 獲取字體屬性（如果需要）
    font_prop = get_font_properties()

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
        portfolio_data = pd.concat(portfolio_data_list, ignore_index=True)

        # **新增調試輸出**：顯示合併後的數據預覽
        st.write("### 合併後的投資組合數據預覽")
        st.write(portfolio_data.head())

        # 顯示所有列名以進行調試
        st.write("### 投資組合數據列名")
        st.write(portfolio_data.columns.tolist())

        # 確保列名標準化（移除空格並轉為標準格式）
        if isinstance(portfolio_data.columns, pd.MultiIndex):
            portfolio_data.columns = ['_'.join(col).strip() for col in portfolio_data.columns.values]
        else:
            portfolio_data.columns = portfolio_data.columns.str.strip().str.capitalize()

        # 再次顯示列名以確認標準化
        st.write("### 標準化後的數據列名")
        st.write(portfolio_data.columns.tolist())

        # 檢查是否包含必要的列
        required_columns = ['Date', 'Symbol', 'Close']
        if not all(column in portfolio_data.columns for column in required_columns):
            missing_cols = [col for col in required_columns if col not in portfolio_data.columns]
            st.error(f"數據缺少必要的列：{missing_cols}")
        else:
            # 檢查重複的 Date 和 Symbol 組合
            duplicates = portfolio_data.duplicated(subset=['Date', 'Symbol'], keep=False)
            if duplicates.any():
                st.warning("數據中存在重複的 Date 和 Symbol 組合。將進行匯總。")
                # 使用 pivot_table 進行匯總，這裡選擇 'last' 作為匯總方法
                close_prices = portfolio_data.pivot_table(index='Date', columns='Symbol', values='Close', aggfunc='last')
            else:
                # 使用 pivot 進行轉換
                close_prices = portfolio_data.pivot(index='Date', columns='Symbol', values='Close')

            # **新增調試輸出**：顯示 'Close' 價格數據預覽
            st.write("### 投資組合收盤價數據預覽")
            st.write(close_prices.head())

            # 檢查 close_prices 的形狀和數據類型
            st.write("### 'close_prices' DataFrame 信息")
            st.write(close_prices.info())

            # 確保所有 'Close' 價格都是數值型，並轉換為浮點數
            close_prices = close_prices.apply(pd.to_numeric, errors='coerce')

            # **新增調試輸出**：顯示轉換後的 'Close' 價格數據預覽
            st.write("### 數值型轉換後的投資組合收盤價數據預覽")
            st.write(close_prices.head())

            try:
                # 處理缺失值
                close_prices = close_prices.ffill().dropna()

                # **新增調試輸出**：顯示處理後的 'Close' 價格數據
                st.write("### 處理後的投資組合收盤價數據預覽")
                st.write(close_prices.head())

                # 計算每日收益率
                returns = close_prices.pct_change()

                # 計算組合的平均每日收益率（等權重）
                portfolio_returns = returns.mean(axis=1)

                # **新增調試輸出**：顯示組合每日收益率預覽
                st.write("### 組合每日收益率預覽")
                st.write(portfolio_returns.head())

                # 獲取基準股票的歷史數據
                benchmark_data = fetch_stock_data(benchmark_symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))

                if benchmark_data is not None and not benchmark_data.empty:
                    benchmark_data.set_index('Date', inplace=True)
                    benchmark_returns = benchmark_data['Close'].pct_change()

                    # **新增調試輸出**：顯示基準股票收盤價數據預覽
                    st.write(f"### 基準股票 {benchmark_input} 收盤價數據預覽")
                    st.write(benchmark_data['Close'].head())

                    # 對齊日期索引
                    combined_index = portfolio_returns.index.intersection(benchmark_returns.index)
                    portfolio_returns = portfolio_returns.loc[combined_index]
                    benchmark_returns = benchmark_returns.loc[combined_index]

                    # 處理缺失值
                    portfolio_returns = portfolio_returns.fillna(0)
                    benchmark_returns = benchmark_returns.fillna(0)

                    # **新增調試輸出**：顯示對齊後的收益率預覽
                    st.write("### 對齊後的組合與基準股票收益率預覽")
                    st.write(pd.DataFrame({
                        'Portfolio Returns': portfolio_returns.head(),
                        f'{benchmark_input} Returns': benchmark_returns.head()
                    }))

                    # 計算累積收益
                    portfolio_cumulative_returns = (1 + portfolio_returns).cumprod() - 1
                    benchmark_cumulative_returns = (1 + benchmark_returns).cumprod() - 1

                    # **新增調試輸出**：顯示累積收益預覽
                    st.write("### 組合累積收益預覽")
                    st.write(portfolio_cumulative_returns.head())
                    st.write(f"### 基準股票 {benchmark_input} 累積收益預覽")
                    st.write(benchmark_cumulative_returns.head())

                    # 準備 Plotly 圖表
                    fig = go.Figure()

                    # 添加投資組合累積收益曲線
                    fig.add_trace(go.Scatter(
                        x=portfolio_cumulative_returns.index,
                        y=portfolio_cumulative_returns.values,
                        mode='lines',
                        name='投資組合累積收益',
                        hovertemplate=
                            '日期: %{x}<br>' +
                            '累積收益: %{y:.2%}<extra></extra>'
                    ))

                    # 添加基準股票累積收益曲線
                    fig.add_trace(go.Scatter(
                        x=benchmark_cumulative_returns.index,
                        y=benchmark_cumulative_returns.values,
                        mode='lines',
                        name=f'{benchmark_input} 累積收益',
                        hovertemplate=
                            '日期: %{x}<br>' +
                            '累積收益: %{y:.2%}<extra></extra>'
                    ))

                    # 設置圖表布局
                    fig.update_layout(
                        title='投資組合與基準股票累積收益對比',
                        xaxis_title='日期',
                        yaxis_title='累積收益',
                        hovermode='x unified',
                        template='plotly_white'
                    )

                    # 設置 Y 軸為百分比格式
                    fig.update_yaxes(tickformat=".2%")

                    # **新增調試輸出**：顯示累積收益圖表前的數據形狀
                    st.write("### 組合累積收益數據形狀", portfolio_cumulative_returns.shape)
                    st.write("### 基準股票累積收益數據形狀", benchmark_cumulative_returns.shape)

                    # 顯示 Plotly 圖表
                    st.plotly_chart(fig, use_container_width=True)

                    # 繪製基準股票的 K 線圖
                    fig_candlestick = go.Figure(data=[go.Candlestick(
                        x=benchmark_data.index,
                        open=benchmark_data['Open'],
                        high=benchmark_data['High'],
                        low=benchmark_data['Low'],
                        close=benchmark_data['Close'],
                        name=f'{benchmark_input} K 線',
                        hovertemplate=
                            '日期: %{x}<br>' +
                            '開盤價: %{open}<br>' +
                            '最高價: %{high}<br>' +
                            '最低價: %{low}<br>' +
                            '收盤價: %{close}<extra></extra>'
                    )])

                    fig_candlestick.update_layout(
                        title=f'{benchmark_input} K 線圖',
                        xaxis_title='日期',
                        yaxis_title='價格',
                        template='plotly_white'
                    )

                    st.plotly_chart(fig_candlestick, use_container_width=True)

                    # 計算總收益
                    total_portfolio_return = portfolio_cumulative_returns.iloc[-1]
                    total_benchmark_return = benchmark_cumulative_returns.iloc[-1]

                    # 顯示回測結果
                    st.write(f"**投資組合總收益：** {total_portfolio_return * 100:.2f}%")
                    st.write(f"**{benchmark_input} 總收益：** {total_benchmark_return * 100:.2f}%")

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
            except Exception as e:
                st.error(f"處理數據時出錯：{e}")
