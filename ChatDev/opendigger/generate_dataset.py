"""Generate OpenDigger MMLU-style QA datasets."""

import os
import pandas as pd
from typing import Any, Dict, List

COLUMNS_TO_SHOW = [
    "month",
    "openrank",
    "activity",
    "issue_response_time",
    "change_request_response_time",
    "inactive_contributors",
]
OUTPUT_FILENAME = "test.parquet"
WINDOW_SIZE = 6
QUESTION_CATEGORY = "OpenSourceGovernance"
ANSWER_OPTIONS = [
    "Significant Increase (> 10%)",
    "Stable/Slight Increase (0% to 10%)",
    "Stable/Slight Decrease (-10% to 0%)",
    "Significant Decrease (< -10%)",
]
REPO_SEPARATOR = "/"
SAFE_REPO_SEPARATOR = "_"
CONTEXT_SUFFIX = "_context.csv"
OUTPUT_SUBDIR = os.path.join("puppeteer", "data", "OpenDiggerMMLU")
INPUT_SUBDIR = os.path.join("puppeteer", "data", "OpenDigger", "train")

def safe_repo_slug(repo_name: str) -> str:
    """Convert a repo slug into a filesystem-safe identifier."""
    return repo_name.replace(REPO_SEPARATOR, SAFE_REPO_SEPARATOR)

def format_month_range(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """Format a month range for prompt text."""
    return f"{start.strftime('%Y-%m')} to {end.strftime('%Y-%m')}"

def format_month(month: pd.Timestamp) -> str:
    """Format a single month token."""
    return month.strftime("%Y-%m")

def generate_qa_pairs(
    df: pd.DataFrame, repo_name: str, window_size: int = WINDOW_SIZE
) -> List[Dict[str, Any]]:
    """Build QA pairs from a rolling window over a repo's metrics."""
    qa_pairs = []
    
    # 确保月份是 datetime 类型
    df['month'] = pd.to_datetime(df['month'])
    df = df.sort_values('month')
    
    # 我们至少需要 window_size + 1 个数据点
    if len(df) < window_size + 1:
        return []

    for i in range(len(df) - window_size):
        window = df.iloc[i : i + window_size].copy()
        target = df.iloc[i + window_size]
        
        # 上下文字符串（选择相关列）
        # 过滤存在的列
        cols = [c for c in COLUMNS_TO_SHOW if c in df.columns]
        context_str = window[cols].to_string(index=False)
        
        # 计算 'activity'（活跃度）的趋势
        last_val = window.iloc[-1]['activity']
        target_val = target['activity']
        
        if last_val == 0:
            growth_rate = 0 # 避免除以零
        else:
            growth_rate = (target_val - last_val) / last_val
            
        # 确定标签
        if growth_rate > 0.10:
            answer = "A" # 显著增加
        elif 0 <= growth_rate <= 0.10:
            answer = "B" # 稳定/轻微增加
        elif -0.10 <= growth_rate < 0:
            answer = "C" # 稳定/轻微减少
        else:
            answer = "D" # 显著减少
            
        # 构建问题
        month_range = format_month_range(window.iloc[0]["month"], window.iloc[-1]["month"])
        question = (
            "You are an Open Source Community Manager. Analyze the following data "
            f"for repository '{repo_name}' from {month_range}:\n\n{context_str}\n\n"
            "Based on the trend, how will the 'activity' metric change in the next "
            f"month ({format_month(target['month'])})?"
        )
        
        options = ANSWER_OPTIONS
        
        qa_pairs.append({
            "question_id": f"{safe_repo_slug(repo_name)}_{target['month'].strftime('%Y%m')}",
            "question": question,
            "options": options,
            "answer": answer,
            "category": QUESTION_CATEGORY,
            "src_repo": repo_name,
            "target_month": target['month'].strftime('%Y-%m')
        })
        
    return qa_pairs

def main() -> None:
    """Entry point for generating QA data from CSV contexts."""
    # 现有 CSV 文件的路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, INPUT_SUBDIR)
    
    all_data = []
    
    if not os.path.exists(data_dir):
        print(f"Data directory not found: {data_dir}")
        return

    print(f"Scanning {data_dir}...")
    for filename in os.listdir(data_dir):
        if filename.endswith(CONTEXT_SUFFIX):
            repo_name = filename.replace("_context.csv", "").replace("_", "/")
            file_path = os.path.join(data_dir, filename)
            
            print(f"Processing {repo_name} from {filename}...")
            try:
                df = pd.read_csv(file_path)
                pairs = generate_qa_pairs(df, repo_name)
                all_data.extend(pairs)
                print(f"Generated {len(pairs)} samples for {repo_name}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
            
    # 创建 DataFrame
    df_final = pd.DataFrame(all_data)
    
    # 保存为 Parquet 格式
    output_dir = os.path.join(base_dir, OUTPUT_SUBDIR)
    os.makedirs(output_dir, exist_ok=True)
        
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)
    df_final.to_parquet(output_path)
    print(f"Dataset saved to {output_path} with {len(df_final)} samples.")

if __name__ == "__main__":
    main()
