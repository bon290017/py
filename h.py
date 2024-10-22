import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import datetime, timedelta
from matplotlib.font_manager import FontProperties
import os

# 设置支持中文的字体（如果需要在其他图表中使用）
def get_font_properties(font_size=12):
    font_path = os.path.join("fonts", "NotoSansTC-SemiBold.ttf")
    if os.path.exists(font_path):
        try:
            font_prop = FontProperties(fname=font_path, size=font_size)
            return font_prop
        except Exception as e:
            st.warning(f"加载字体时出错：{e}。将使用默认字体。")
            return None
    else:
        st.warning("未找到自定义中文字体文件。将使用默认字体。")
        return None

# 设置应用标题
st.title("多股票回测系统")

# 说明文字
st.write("""
    请输入多支台湾股市代号，并选择一支基准股票进行回测比较。
    您可以输入多支股票代号，使用逗号分隔，例如：2330,2317,2412
""")

# 用户输入
symbols_input = st.text_input("请输入多支台湾股市代号（用逗号分隔）:", "2330,2317,2412")
benchmark_input = st.text_input("请输入用于对比的台湾股市代号:", "0050")

# 新增日期选择功能，标签使用中文
st.write("### 选择回测的日期范围")
default_end_date = datetime.today()
default_start_date = default_end_date - timedelta(days=730)  # 默认过去两年

start_date = st.date_input("开始日期", default_start_date)
end_date = st.date_input("结束日期", default_end_date)

# 确保开始日期不晚于结束日期
if start_date > end_date:
    st.error("开始日期不能晚于结束日期。请重新选择日期。")

# 按钮触发回测
if st.button("开始回测"):
    # 获取字体属性（如果需要）
    font_prop = get_font_properties()

    # 定义函数以获取单个股票的历史数据
    def fetch_stock_data(symbol, start_date, end_date):
        try:
            stock = yf.download(symbol, start=start_date, end=end_date)
            if stock.empty:
                st.warning(f"未能获取到 {symbol} 的数据。请检查股票代号是否正确或该股票是否已退市。")
                return None
            stock['Symbol'] = symbol
            return stock
        except Exception as e:
            st.error(f"获取 {symbol} 数据时出错。错误信息：{e}")
            return None

    # 处理股票代号输入，替换全角逗号为半角逗号，并分割
    symbols_list = [symbol.strip() + "
