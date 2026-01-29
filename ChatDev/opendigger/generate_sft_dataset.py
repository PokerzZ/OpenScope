"""Generate SFT training data from OpenDigger metrics."""

import os
import pandas as pd
import json
from typing import List

WINDOW_SIZE = 6
COLUMNS_TO_SHOW = [
    "month",
    "openrank",
    "activity",
    "issue_response_time",
    "change_request_response_time",
    "inactive_contributors",
]
OUTPUT_FILENAME = "sft_train_data.jsonl"
CONTEXT_SUFFIX = "_context.csv"
SYSTEM_PROMPT = (
    "You are an Open Source Community Manager. Analyze the provided community "
    "metrics and generate a structured JSON report."
)
USER_PROMPT_TEMPLATE = """Repository: {repo_name}
Analysis Period: {start_month} to {end_month}

Data:
{context_str}

Please provide a detailed analysis in JSON format containing predictions for the next month ({target_month}), key insights, and actionable recommendations."""

def generate_insights(
    window: pd.DataFrame, trend: str, activity_growth: float
) -> List[str]:
    """Generate insight sentences based on recent metrics."""
    insights = []
    
    # 1. 活跃度洞察
    avg_activity = window['activity'].mean()
    if activity_growth > 0.1:
        insights.append(f"活跃度在过去 6 个月呈现上升趋势，近期增长显著 (+{activity_growth*100:.1f}%)")
    elif activity_growth < -0.1:
        insights.append(f"活跃度近期出现下滑 (-{abs(activity_growth)*100:.1f}%)，需关注社区参与度")
    else:
        insights.append("社区活跃度保持相对稳定，无剧烈波动")

    # 2. 响应时间洞察
    avg_issue_time = window['issue_response_time'].mean()
    if avg_issue_time == 0:
        insights.append("历史数据显示 Issue 响应数据缺失或为 0，建议检查数据源")
    elif window.iloc[-1]['issue_response_time'] < window.iloc[0]['issue_response_time']:
        insights.append("Issue 响应效率有所提升，社区维护者响应更加积极")
    
    # 3. 整体趋势洞察
    insights.append(f"OpenRank 趋势评估为: {trend}，显示项目影响力{('正在扩大' if trend=='increasing' else '趋于平稳')}")
    
    return insights

def generate_recommendations(
    trend: str, activity_growth: float, inactive_count: float
) -> List[str]:
    """Generate recommendation sentences based on trend signals."""
    recs = []
    
    if trend == "decreasing" or activity_growth < 0:
        recs.append("建议举办黑客松或开发者活动以重新激活社区热情")
        recs.append("分析流失贡献者的特征，尝试定向召回")
    else:
        recs.append("继续保持当前的 Issue 响应机制")
        recs.append("可以考虑设立贡献者激励计划以维持高活跃度")
        
    if inactive_count > 0:
        recs.append("关注非活跃贡献者，建立定期的社区关怀机制")
    else:
        recs.append("关注新晋贡献者的 Onboarding 体验")
        
    return recs

def format_analysis_period(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """Format a month range for analysis metadata."""
    return f"{start.strftime('%Y-%m')} to {end.strftime('%Y-%m')}"

def format_month(start: pd.Timestamp) -> str:
    """Format a single month as YYYY-MM."""
    return start.strftime("%Y-%m")

def generate_sft_dataset() -> None:
    """Generate SFT samples and write them to jsonl."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "puppeteer", "data", "OpenDigger", "train")
    output_dir = os.path.join(base_dir, "puppeteer", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)
    
    dataset = []
    window_size = WINDOW_SIZE
    
    if not os.path.exists(data_dir):
        print(f"Data directory not found: {data_dir}")
        return

    print(f"Scanning {data_dir}...")
    files = [f for f in os.listdir(data_dir) if f.endswith(CONTEXT_SUFFIX)]
    
    for filename in files:
        repo_name = filename.replace("_context.csv", "").replace("_", "/")
        file_path = os.path.join(data_dir, filename)
        
        try:
            df = pd.read_csv(file_path)
            # 确保类型正确
            df['month'] = pd.to_datetime(df['month'])
            df = df.sort_values('month')
            
            if len(df) < window_size + 1:
                continue
                
            for i in range(len(df) - window_size):
                # 输入窗口
                window = df.iloc[i : i + window_size].copy()
                # 目标月份
                target = df.iloc[i + window_size]
                
                # 构建输入提示（表格的文本表示）
                # 创建格式良好的 markdown 表格字符串
                # context_str = window[COLUMNS_TO_SHOW].to_markdown(index=False)
                context_str = window[COLUMNS_TO_SHOW].to_string(index=False)
                
                system_prompt = SYSTEM_PROMPT
                start_month = format_month(window.iloc[0]["month"])
                end_month = format_month(window.iloc[-1]["month"])
                analysis_period = format_analysis_period(
                    window.iloc[0]["month"], window.iloc[-1]["month"]
                )
                user_prompt = USER_PROMPT_TEMPLATE.format(
                    repo_name=repo_name,
                    start_month=start_month,
                    end_month=end_month,
                    context_str=context_str,
                    target_month=target["month"].strftime("%Y-%m"),
                )

                # 构建真实值（输出）
                # 1. 计算趋势
                last_activity = window.iloc[-1]['activity']
                target_activity = target['activity']
                growth = (target_activity - last_activity) / (last_activity + 1e-5)
                
                trend = "stable"
                if growth > 0.05: trend = "increasing"
                elif growth < -0.05: trend = "decreasing"
                
                # 2. Generate JSON Content
                output_obj = {
                    "repository": repo_name,
                    "analysis_period": analysis_period,
                    "predictions": {
                        "next_month_openrank": round(float(target['openrank']), 2),
                        "next_month_activity": round(float(target['activity']), 2),
                        "trend": trend
                    },
                    "insights": generate_insights(window, trend, growth),
                    "recommendations": generate_recommendations(trend, growth, window.iloc[-1]['inactive_contributors'])
                }
                
                dataset.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": json.dumps(output_obj, ensure_ascii=False, indent=2)}
                    ]
                })
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Successfully generated {len(dataset)} SFT samples at {output_path}")

if __name__ == "__main__":
    generate_sft_dataset()
