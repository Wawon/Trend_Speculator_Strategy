import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.trend import ADXIndicator, macd
from ta.momentum import RSIIndicator

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def get_etf_data(etf_code):
    """获取ETF数据"""
    try:
        # 使用akshare获取ETF数据 - 正确方法
        df = ak.fund_etf_hist_em(symbol=etf_code)
        
        # 检查数据列名，akshare可能返回中文列名
        if '日期' in df.columns:
            df['date'] = pd.to_datetime(df['日期'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
            print("数据列名不匹配，尝试使用第一列作为日期")
            df['date'] = pd.to_datetime(df.iloc[:, 0])
            
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # 确保有必要的价格数据列
        if '收盘' in df.columns:
            df['close'] = df['收盘']
        elif 'close' in df.columns:
            pass  # 已有close列
        else:
            print("无法找到收盘价数据列")
            return None
            
        if '最高' in df.columns:
            df['high'] = df['最高']
        if '最低' in df.columns:
            df['low'] = df['最低']
            
        return df
    except Exception as e:
        print(f"获取ETF数据失败: {str(e)}")
        return None

def calculate_technical_indicators(df):
    """计算技术指标"""
    if df is None or len(df) < 30:
        return None
    
    # 计算ADX (14天周期)
    adx_indicator = ADXIndicator(df['high'], df['low'], df['close'], window=14)
    df['ADX'] = adx_indicator.adx()
    
    # 计算MACD (使用ta库的正确参数)
    df['MACD_DIF'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_DEA'] = df['MACD_DIF'].ewm(span=9, adjust=False).mean()
    
    # 计算RSI (14天周期)
    rsi_indicator = RSIIndicator(df['close'], window=14)
    df['RSI'] = rsi_indicator.rsi()
    
    return df

def evaluate_trend(df, etf_code):
    """评估趋势并计算评分"""
    if df is None or len(df) < 30:
        return None
    
    # 获取最新指标值
    latest = df.iloc[-1]
    
    # 计算各项指标
    adx_value = latest['ADX']
    macd_status = '是' if latest['MACD_DIF'] > 0 and latest['MACD_DEA'] > 0 else '否'
    rsi_value = latest['RSI']
    
    # 计算各项评分
    adx_score = min(adx_value, 50) / 50 * 100
    macd_score = 100 if macd_status == '是' else 0
    rsi_score = max(0, (rsi_value - 50) / 30 * 100)
    
    # 加权综合评分
    total_score = adx_score * 0.4 + macd_score * 0.3 + rsi_score * 0.3
    
    # 返回单行结果
    return {
        'ETF代码': etf_code,
        'ADX值': round(adx_value, 2),
        'MACD金叉': macd_status,
        'RSI值': round(rsi_value, 2),
        '综合趋势评分': round(total_score, 1)
    }

def evaluate_multiple_etfs(etf_codes):
    """批量评估多个ETF"""
    results = []
    
    for etf_code in etf_codes:
        print(f"\n正在处理ETF {etf_code}...")
        
        # 获取数据
        etf_data = get_etf_data(etf_code)
        if etf_data is None:
            print(f"ETF {etf_code} 数据获取失败")
            continue
            
        print(f"数据时间范围: {etf_data.index[0].date()} 到 {etf_data.index[-1].date()}")
        
        # 计算技术指标
        etf_data = calculate_technical_indicators(etf_data)
        if etf_data is None:
            print(f"ETF {etf_code} 数据不足")
            continue
            
        # 评估趋势
        evaluation = evaluate_trend(etf_data, etf_code)
        if evaluation:
            results.append(evaluation)
    
    if not results:
        print("\n没有有效的评估结果")
        return None
    
    # 转换为DataFrame并按综合趋势评分降序排序
    df = pd.DataFrame(results)
    return df.sort_values('综合趋势评分', ascending=False)

def main():
    # ===== 在这里修改需要评估的ETF代码列表 =====
    etf_codes = ['511010','511880','588000','512890','510300',
                 '510500','510050','159205','513100','513500',
                 '513130','513080','513520','518880','515220',
                 '501018','159980','159985','515790','516160',
                 '588200','520580','513030','511090'
    ]
    
    print(f"开始批量评估ETF: {', '.join(etf_codes)}")
    
    # 批量评估
    final_result = evaluate_multiple_etfs(etf_codes)
    
    if final_result is not None:
        # 输出结果
        print("\n===== ETF趋势评估结果 =====")
        print(final_result.to_string(index=False))
        
        # 保存为CSV文件
        output_file = "etf_trend_evaluation_batch.csv"
        final_result.to_csv(output_file, index=False, encoding='utf_8_sig')
        print(f"\n结果已保存到: {output_file}")

if __name__ == "__main__":
    main()