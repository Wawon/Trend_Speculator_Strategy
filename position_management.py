import akshare as ak
import pandas as pd
import numpy as np

# ================= 配置参数 =================
# 风险控制参数
MAX_LOSS_PER_ETF = 150  # 单只ETF最大亏损承受额(元)
ATR_PERIOD = 14        # ATR计算周期
ATR_MULTIPLIER = 2     # ATR系数

# 需要评估的ETF代码列表
ETF_CODES = [
    '588000',  # 科创50ETF
    '588200',  # 科创创业ETF
    '159205',  # 沪深300ETF
    '510500',  # 中证500ETF
    '510300'   # 沪深300ETF
]

def get_etf_data(etf_code):
    """获取ETF历史数据"""
    try:
        df = ak.fund_etf_hist_em(symbol=etf_code)
        # 处理中文列名
        if '日期' in df.columns:
            df['date'] = pd.to_datetime(df['日期'])
            df['close'] = df['收盘'].astype(float)
            df['high'] = df['最高'].astype(float)
            df['low'] = df['最低'].astype(float)
        else:
            df['date'] = pd.to_datetime(df['date'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        return df[['high', 'low', 'close']]
    except Exception as e:
        print(f"获取ETF {etf_code} 数据失败: {e}")
        return None

def calculate_position(etf_code):
    """计算入场仓位和止损百分比"""
    try:
        # 获取历史数据
        df = get_etf_data(etf_code)
        if df is None or len(df) < ATR_PERIOD:
            return None
            
        # 计算ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        latest_atr = df['tr'].tail(ATR_PERIOD).mean()
        current_price = df['close'].iloc[-1]
        
        if pd.isna(latest_atr) or current_price <= 0:
            return None
            
        # 计算止损百分比 (ATR倍数/最新价)
        stop_loss_pct = (ATR_MULTIPLIER * latest_atr) / current_price * 100
        
        # 计算可买入数量(100的整数倍)
        quantity = max(100, (int(MAX_LOSS_PER_ETF // (ATR_MULTIPLIER * latest_atr)) // 100) * 100)
        
        return {
            'ETF代码': etf_code,
            '最新价格': round(current_price, 3),
            'ATR值': round(latest_atr, 3),
            '建议买入数量': quantity,
            '止损百分比(%)': round(stop_loss_pct, 2),
            '最大亏损额(元)': round(ATR_MULTIPLIER * latest_atr * quantity, 2)
        }
    except Exception as e:
        print(f"计算ETF {etf_code} 仓位时出错: {e}")
        return None

def main():
    results = []
    for etf_code in ETF_CODES:
        print(f"\n正在处理ETF {etf_code}...")
        position = calculate_position(etf_code)
        if position:
            print(f"最新价格: {position['最新价格']}")
            print(f"ATR值: {position['ATR值']}")
            print(f"建议买入数量: {position['建议买入数量']}股 (100的整数倍)")
            print(f"止损百分比: {position['止损百分比(%)']}%")
            print(f"预计最大亏损: {position['最大亏损额(元)']}元")
            results.append(position)
    
    if results:
        # 保存结果到CSV
        df = pd.DataFrame(results)
        df.to_csv('etf_position_management.csv', index=False, encoding='utf_8_sig')
        print("\n仓位管理建议已保存到 etf_position_management.csv")
    else:
        print("没有有效的计算结果")

if __name__ == "__main__":
    main()