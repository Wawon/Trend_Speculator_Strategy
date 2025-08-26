import akshare as ak
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator

# 配置参数
ETF_CODES = [
    '588000',  # 科创50ETF
    '588200',  # 科创创业ETF
    '159205',  # 沪深300ETF
    '510500',  # 中证500ETF
    '510300'   # 沪深300ETF
]
RSI_PERIOD = 14  # RSI指标计算周期
EMA_SHORT = 12   # 短期EMA周期
EMA_LONG = 26    # 长期EMA周期

def get_etf_data(etf_code):
    """
    获取ETF历史数据和实时数据
    
    参数:
        etf_code (str): ETF代码
        
    返回:
        pandas.DataFrame: 包含收盘价和成交量的DataFrame，索引为日期
    """
    try:
        # 获取历史数据 - 使用akshare获取ETF历史行情
        hist_df = ak.fund_etf_hist_em(symbol=etf_code)
        # 获取实时数据 - 使用akshare获取ETF实时行情
        realtime_df = ak.fund_etf_spot_em()
        # 筛选出当前ETF的实时数据
        realtime_data = realtime_df[realtime_df['代码'] == etf_code].iloc[0]
        
        # 处理历史数据列名 - 兼容不同版本的列名
        hist_df['date'] = pd.to_datetime(hist_df['日期'] if '日期' in hist_df.columns else hist_df['date'])
        hist_df['close'] = hist_df['收盘'].astype(float) if '收盘' in hist_df.columns else hist_df['close'].astype(float)
        hist_df['volume'] = hist_df['成交量'].astype(float) if '成交量' in hist_df.columns else hist_df['volume'].astype(float)
        hist_df.set_index('date', inplace=True)  # 设置日期为索引
        
        # 添加最新实时数据到历史数据中
        latest_data = {
            'close': float(realtime_data['最新价']),  # 最新收盘价
            'volume': float(realtime_data['成交量'])   # 最新成交量
        }
        latest_date = pd.to_datetime('today').normalize()  # 获取当天日期（去除时间部分）
        hist_df.loc[latest_date] = latest_data  # 添加最新数据
        
        return hist_df[['close', 'volume']].sort_index()  # 返回排序后的收盘价和成交量数据
    except Exception as e:
        print(f"获取ETF {etf_code} 数据失败: {e}")
        return None

def check_rsi_divergence(df):
    """
    检查RSI顶背离 - 价格创新高但RSI指标未创新高
    
    参数:
        df (pandas.DataFrame): 包含收盘价的数据框
        
    返回:
        bool: 是否存在RSI顶背离
    """
    if len(df) < RSI_PERIOD + 5:  # 确保数据长度足够计算RSI和检查背离
        return False
    
    # 计算RSI指标 - 使用ta库计算相对强弱指数
    rsi = RSIIndicator(df['close'], window=RSI_PERIOD).rsi()
    
    # 检查最近5个周期是否存在顶背离
    last_5 = df['close'].tail(5)      # 最近5个周期的收盘价
    last_5_rsi = rsi.tail(5)          # 最近5个周期的RSI值
    
    # 价格创新高但RSI未创新高 - 典型的顶背离信号
    if (last_5.idxmax() == last_5.index[-1] and  # 价格最高点在最近一个周期
        last_5_rsi.idxmax() != last_5_rsi.index[-1]):  # RSI最高点不在最近一个周期
        return True
    return False

def check_obv_divergence(df):
    """
    检查OBV顶背离 - 价格创新高但能量潮指标未创新高
    
    参数:
        df (pandas.DataFrame): 包含收盘价和成交量的数据框
        
    返回:
        bool: 是否存在OBV顶背离
    """
    if len(df) < 10:  # 确保数据长度足够检查背离
        return False
    
    # 计算OBV指标 - 使用ta库计算能量潮指标
    obv = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
    
    # 检查最近5个周期
    last_5_close = df['close'].tail(5)  # 最近5个周期的收盘价
    last_5_obv = obv.tail(5)           # 最近5个周期的OBV值
    
    # 价格创新高但OBV未创新高 - 量价背离信号
    if (last_5_close.idxmax() == last_5_close.index[-1] and  # 价格最高点在最近一个周期
        last_5_obv.idxmax() != last_5_obv.index[-1]):        # OBV最高点不在最近一个周期
        return True
    return False

def check_ema_death_cross(df):
    """
    检查EMA死叉 - 短期EMA下穿长期EMA形成的卖出信号
    
    参数:
        df (pandas.DataFrame): 包含收盘价的数据框
        
    返回:
        bool: 是否出现EMA死叉
    """
    if len(df) < EMA_LONG + 1:  # 确保数据长度足够计算长期EMA
        return False
    
    # 计算EMA指标 - 使用ta库计算指数移动平均线
    ema_short = EMAIndicator(df['close'], window=EMA_SHORT).ema_indicator()  # 短期EMA
    ema_long = EMAIndicator(df['close'], window=EMA_LONG).ema_indicator()    # 长期EMA
    
    # 检查是否出现死叉 - 短期EMA从上向下穿过长期EMA
    return (ema_short.iloc[-2] > ema_long.iloc[-2] and  # 前一个周期短期EMA在长期EMA之上
            ema_short.iloc[-1] < ema_long.iloc[-1])    # 当前周期短期EMA在长期EMA之下

def monitor_etf(etf_code):
    """
    监控单个ETF的风险指标
    
    参数:
        etf_code (str): ETF代码
        
    返回:
        dict: 包含各项风险指标的字典，如果获取数据失败则返回None
    """
    df = get_etf_data(etf_code)  # 获取ETF数据
    if df is None:  # 数据获取失败
        return None
    
    return {
        'ETF代码': etf_code,  # ETF代码
        '最新价格': round(df['close'].iloc[-1], 3),  # 最新收盘价，保留3位小数
        'RSI顶背离': check_rsi_divergence(df),  # RSI顶背离信号
        'OBV顶背离': check_obv_divergence(df),  # OBV顶背离信号
        'EMA死叉': check_ema_death_cross(df)    # EMA死叉信号
    }

def main():
    """
    主函数 - 执行ETF持仓风险监测
    """
    print("开始ETF持仓风险监测...")
    results = []  # 存储所有ETF的监测结果
    for etf_code in ETF_CODES:  # 遍历所有ETF代码
        print(f"\n正在分析ETF {etf_code}...")
        result = monitor_etf(etf_code)  # 监控单个ETF
        if result:  # 如果监控成功
            results.append(result)  # 添加到结果列表
            print(f"最新价格: {result['最新价格']}")
            print(f"RSI顶背离: {'是' if result['RSI顶背离'] else '否'}")
            print(f"OBV顶背离: {'是' if result['OBV顶背离'] else '否'}")
            print(f"EMA死叉: {'是' if result['EMA死叉'] else '否'}")
    
    if results:  # 如果有有效结果
        # 保存结果到CSV文件 - 使用utf_8_sig编码支持中文
        pd.DataFrame(results).to_csv('etf_risk_monitor.csv', index=False, encoding='utf_8_sig')
        print("\n监测结果已保存到 etf_risk_monitor.csv")
    else:
        print("没有有效的监测结果")

if __name__ == "__main__":
    main()  # 程序入口点 - 当直接运行此脚本时执行main函数
