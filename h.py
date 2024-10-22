import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
import plotly.io as pio

# 设置应用标题
print("多股票回测系统\n")

# 说明文字
print("""
请输入多支台湾股市代号，并选择一支基准股票进行回测比较。
您可以输入多支股票代号，使用逗号分隔，例如：2330,2317,2412
""")

# 用户输入
symbols_input = input("请输入多支台湾股市代号（用逗号分隔）: ").strip() or "2330,2317,2412"
benchmark_input = input("请输入用于对比的台湾股市代号: ").strip() or "0050"

# 选择回测的日期范围
print("\n### 选择回测的日期范围")
default_end_date = datetime.today()
default_start_date = default_end_date - timedelta(days=730)  # 默认过去两年

# 用户输入日期
start_date_input = input(f"请输入开始日期 (YYYY-MM-DD)，默认为 {default_start_date.strftime('%Y-%m-%d')}: ").strip() or default_start_date.strftime('%Y-%m-%d')
end_date_input = input(f"请输入结束日期 (YYYY-MM-DD)，默认为 {default_end_date.strftime('%Y-%m-%d')}: ").strip() or default_end_date.strftime('%Y-%m-%d')

# 转换日期
try:
    start_date = datetime.strptime(start_date_input, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
except ValueError:
    print("日期格式错误，请使用 YYYY-MM-DD 格式。")
    exit()

# 确保开始日期不晚于结束日期
if start_date > end_date:
    print("开始日期不能晚于结束日期。请重新运行程序并选择正确的日期。")
else:
    # 定义函数以获取单个股票的历史数据
    def fetch_stock_data(symbol, start_date, end_date):
        try:
            stock = yf.download(symbol, start=start_date, end=end_date)
            if stock.empty:
                print(f"未能获取到 {symbol} 的数据。请检查股票代号是否正确或该股票是否已退市。")
                return None
            stock['Symbol'] = symbol
            return stock
        except Exception as e:
            print(f"获取 {symbol} 数据时出错。错误信息：{e}")
            return None

    # 处理股票代号输入，替换全角逗号为半角逗号，并分割
    symbols_list = [symbol.strip() + ".TW" for symbol in symbols_input.replace('，', ',').split(",")]

    # 处理基准股票代号
    benchmark_symbol = benchmark_input.strip() + ".TW"

    # 定义日期范围（根据用户选择）
    end_date_dt = datetime.combine(end_date, datetime.max.time())
    start_date_dt = datetime.combine(start_date, datetime.min.time())

    # 获取多支股票的历史数据
    portfolio_data_list = []

    for symbol in symbols_list:
        data = fetch_stock_data(symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))
        if data is not None:
            portfolio_data_list.append(data)

    # 检查是否有有效的数据
    if not portfolio_data_list:
        print("未能获取到任何有效的投资组合股票数据。请检查股票代号并重试。")
    else:
        # 使用 pd.concat 合并所有股票的数据
        portfolio_data = pd.concat(portfolio_data_list)

        # 重置索引
        portfolio_data.reset_index(inplace=True)

        # 检查是否存在 'Date' 列，如果没有，尝试重命名
        if 'Date' not in portfolio_data.columns:
            if 'index' in portfolio_data.columns:
                portfolio_data.rename(columns={'index': 'Date'}, inplace=True)
            else:
                print("无法找到日期列，请检查数据。")
                exit()

        # 确保 'Date' 列是 datetime 类型
        portfolio_data['Date'] = pd.to_datetime(portfolio_data['Date'])

        # 删除关键列中的缺失值
        portfolio_data.dropna(subset=['Date', 'Symbol', 'Close'], inplace=True)

        # 使用 pivot_table 并指定聚合函数
        pivot_close = portfolio_data.pivot_table(index='Date', columns='Symbol', values='Close', aggfunc='mean')

        # 处理缺失值（如有）
        pivot_close = pivot_close.ffill().dropna()

        # 检查 pivot_close 是否为空
        if pivot_close.empty:
            print("经过处理后，没有可用的数据进行分析。")
            exit()

        # 计算每日收益率
        returns = pivot_close.pct_change()

        # 计算组合的平均每日收益率（等权重）
        portfolio_returns = returns.mean(axis=1)

        # 获取基准股票的历史数据
        benchmark_data = fetch_stock_data(benchmark_symbol, start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d'))

        if benchmark_data is not None and not benchmark_data.empty:
            benchmark_data.reset_index(inplace=True)
            if 'Date' not in benchmark_data.columns:
                if 'index' in benchmark_data.columns:
                    benchmark_data.rename(columns={'index': 'Date'}, inplace=True)
                else:
                    print("无法找到基准股票的日期列，请检查数据。")
                    exit()
            benchmark_data['Date'] = pd.to_datetime(benchmark_data['Date'])
            benchmark_data.set_index('Date', inplace=True)

            # 计算基准股票的每日收益率
            benchmark_returns = benchmark_data['Close'].pct_change()

            # 对齐日期索引
            common_index = portfolio_returns.index.intersection(benchmark_returns.index)
            portfolio_returns = portfolio_returns.loc[common_index]
            benchmark_returns = benchmark_returns.loc[common_index]

            # 处理缺失值
            portfolio_returns = portfolio_returns.fillna(0)
            benchmark_returns = benchmark_returns.fillna(0)

            # 计算累积收益
            portfolio_cumulative_returns = (1 + portfolio_returns).cumprod() - 1
            benchmark_cumulative_returns = (1 + benchmark_returns).cumprod() - 1

            # 绘制累积收益图表
            fig = go.Figure()

            # 添加投资组合累积收益曲线
            fig.add_trace(go.Scatter(
                x=portfolio_cumulative_returns.index,
                y=portfolio_cumulative_returns.values,
                mode='lines',
                name='投资组合累积收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累积收益: %{y:.2%}<extra></extra>'
            ))

            # 添加基准股票累积收益曲线
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative_returns.index,
                y=benchmark_cumulative_returns.values,
                mode='lines',
                name=f'{benchmark_input} 累积收益',
                hovertemplate=
                    '日期: %{x}<br>' +
                    '累积收益: %{y:.2%}<extra></extra>'
            ))

            # 设置图表布局
            fig.update_layout(
                title='投资组合与基准股票累积收益对比',
                xaxis_title='日期',
                yaxis_title='累积收益',
                hovermode='x unified',
                template='plotly_white'
            )

            # 设置 Y 轴为百分比格式
            fig.update_yaxes(tickformat=".2%")

            # 显示图表
            fig.show()

            # 创建自定义的悬停文本
            hover_text = (
                '日期: ' + benchmark_data.index.strftime('%Y-%m-%d') + '<br>' +
                '开盘价: ' + benchmark_data['Open'].astype(str) + '<br>' +
                '最高价: ' + benchmark_data['High'].astype(str) + '<br>' +
                '最低价: ' + benchmark_data['Low'].astype(str) + '<br>' +
                '收盘价: ' + benchmark_data['Close'].astype(str)
            )

            # 绘制基准股票的 K 线图
            fig_candlestick = go.Figure(data=[go.Candlestick(
                x=benchmark_data.index,
                open=benchmark_data['Open'],
                high=benchmark_data['High'],
                low=benchmark_data['Low'],
                close=benchmark_data['Close'],
                name=f'{benchmark_input} K 线',
                text=hover_text,
                hoverinfo='text'
            )])

            fig_candlestick.update_layout(
                title=f'{benchmark_input} K 线图',
                xaxis_title='日期',
                yaxis_title='价格',
                template='plotly_white'
            )

            fig_candlestick.show()

            # 计算总收益
            total_portfolio_return = portfolio_cumulative_returns.iloc[-1]
            total_benchmark_return = benchmark_cumulative_returns.iloc[-1]

            # 显示回测结果
            print(f"\n投资组合总收益: {total_portfolio_return * 100:.2f}%")
            print(f"{benchmark_input} 总收益: {total_benchmark_return * 100:.2f}%\n")

            # **修改此处，使用 'ME' 代替 'M'**
            portfolio_monthly = portfolio_cumulative_returns.resample('ME').last().pct_change().dropna() * 100
            benchmark_monthly = benchmark_cumulative_returns.resample('ME').last().pct_change().dropna() * 100

            # 合并数据
            monthly_returns_df = pd.DataFrame({
                '日期': portfolio_monthly.index.strftime('%Y-%m'),
                '投资组合月获利%': portfolio_monthly.values,
                f'{benchmark_input} 月获利%': benchmark_monthly.values
            })

            # 显示每月获利数据表
            print("### 每月获利百分比比较")
            print(monthly_returns_df.to_string(index=False, formatters={
                '投资组合月获利%': '{:.2f}'.format,
                f'{benchmark_input} 月获利%': '{:.2f}'.format
            }))
        else:
            print(f"无法取得基准股票 {benchmark_input} 的资料。请检查股票代号是否正确或该股票是否已退市。")

