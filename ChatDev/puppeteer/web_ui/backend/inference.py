import os
import sys
import json
import pandas as pd
from datetime import datetime

# 调整路径以确保导入正常工作
current_dir = os.path.dirname(os.path.abspath(__file__))
puppeteer_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(puppeteer_dir)

from opendigger.getdata import OpenPuppeteerDataCore
from tasks.runner import BenchmarkRunner
from utils.logging import LogManager

def prepare_context_data(repo_name, target_date_str, window_size=6):
    """
    获取数据并构建问题上下文
    target_date_str: "YYYY-MM"
    """
    import logging
    logging.getLogger('global').info(f"OpenDigger: Checking & Fetching data for {repo_name}...")
    
    core = OpenPuppeteerDataCore()
    df = core.build_aligned_dataset(repo_name)
    
    if df is None or df.empty:
        return None, f"Could not fetch data for {repo_name}"

    # 转换日期列
    df['month'] = pd.to_datetime(df['month'])
    
    try:
        target_date = pd.to_datetime(target_date_str)
    except ValueError:
        return None, "Invalid date format. Use YYYY-MM."

    # 排序
    df = df.sort_values('month')
    
    # 查找目标日期的索引
    target_mask = df['month'] == target_date
    if not target_mask.any():
        return None, f"Target date {target_date_str} not found in data range ({df['month'].iloc[0].strftime('%Y-%m')} to {df['month'].iloc[-1].strftime('%Y-%m')})"
    
    target_idx = df.index[df['month'] == target_date][0]
    
    # 目标之前需要 window_size 个数据点
    # 所以我们需要索引：target_idx - window_size 到 target_idx - 1
    
    # 检查是否有足够的历史数据
    start_idx = target_idx - window_size
    if start_idx < 0:
        return None, f"Not enough history before {target_date_str}. need {window_size} months."
    
    # 切片窗口
    window = df.iloc[start_idx : target_idx].copy()
    target = df.iloc[target_idx]
    
    # 构建上下文字符串（逻辑同 generate_dataset.py）
    cols_to_show = ['month', 'openrank', 'activity', 'issue_response_time', 'change_request_response_time', 'inactive_contributors']
    cols = [c for c in cols_to_show if c in df.columns]
    
    # 格式化月份用于显示
    window_display = window.copy()
    window_display['month'] = window_display['month'].dt.strftime('%Y-%m')
    
    context_str = window_display[cols].to_string(index=False)
    
    question = f"You are an Open Source Community Manager. Analyze the following data for repository '{repo_name}' from {window.iloc[0]['month'].strftime('%Y-%m')} to {window.iloc[-1]['month'].strftime('%Y-%m')}:\n\n{context_str}\n\nBased on the trend, how will the 'activity' metric change in the next month ({target['month'].strftime('%Y-%m')})?"
    
    options = [
        "Significant Increase (> 10%)",
        "Stable/Slight Increase (0% to 10%)",
        "Stable/Slight Decrease (-10% to 0%)",
        "Significant Decrease (< -10%)"
    ]
    
    # 确定标签（真实值）用于检查/调试，虽然代理不应该看到它
    # 系统有时期望任务中有 'answer' 键用于评估，但对于推理，我们只希望它们工作。
    # 我们提供一个虚拟答案或在有效时计算它。
    last_val = window.iloc[-1]['activity']
    target_val = target['activity']
    if last_val == 0:
        growth_rate = 0
    else:
        growth_rate = (target_val - last_val) / last_val
        
    if growth_rate > 0.10: gt = "A"
    elif 0 <= growth_rate <= 0.10: gt = "B"
    elif -0.10 <= growth_rate < 0: gt = "C"
    else: gt = "D"
    
    task = {
        "question_id": f"inference_{repo_name}_{target_date_str}",
        "Question": question,
        "options": options,
        "answer": gt,
        "category": "OpenSourceGovernance",
        "src_repo": repo_name,
        "target_month": target_date_str,
        # 帮助我们的代理了解元数据
        "type": "OpenDiggerMMLU" 
    }
    
    return task, None

from threading import Thread
import yaml

def run_pipeline(repo, date, result_callback):
    """
    Runs the inference pipeline.
    result_callback: function(result_dict)
    """
    
    # 在开头定义 puppeteer_dir
    puppeteer_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    task, error = prepare_context_data(repo, date)
    if error:
        result_callback({"error": error})
        return

    # 加载配置
    config_path = os.path.join(puppeteer_dir, "config", "global.yaml")
    with open(config_path, 'r') as f:
        global_config = yaml.safe_load(f)

    # 角色
    personas_path = os.path.join(puppeteer_dir, "personas", "opendigger_personas.jsonl")
    
    runner = BenchmarkRunner(personas_path, global_config)
    
    try:
        # 任务类型已在 prepare_context_data 中设置为 "OpenDiggerMMLU"
        # 这确保使用正确的聚合提示
        
        # BenchmarkRunner.run_reasoning 返回 final_ans
        # 等等，run_reasoning 期望一个任务列表？不，setup_reasoning(data_item)
        final_ans = runner.run_reasoning(task)
        
        # 最终答案可能是一个字符串（来自聚合器提示）
        # 我们尝试将其解析为 JSON（如果可能），或原样返回。
        
        # 查找生成的图表文件
        log_dir = runner.workspace_path
        agent_graph_path = os.path.join(log_dir, "agent_graph.html")
        action_graph_path = os.path.join(log_dir, "action_graph.html")
        
        # 转换为相对于 puppeteer 目录的路径以供 Web 服务使用
        # (puppeteer_dir is already defined at the beginning of the function)
        
        result_data = {
            "final_answer": final_ans,
            "agent_graph": os.path.relpath(agent_graph_path, puppeteer_dir) if os.path.exists(agent_graph_path) else None,
            "action_graph": os.path.relpath(action_graph_path, puppeteer_dir) if os.path.exists(action_graph_path) else None
        }
        
        result_callback(result_data)
        
        # 记录完成
        import logging
        logging.getLogger('global').info(f"\n{'='*60}")
        logging.getLogger('global').info(f"✓ Analysis Complete! Final Answer: {final_ans}")
        logging.getLogger('global').info(f"  Graphs saved to: {log_dir}")
        logging.getLogger('global').info(f"{'='*60}\n")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        result_callback({"error": str(e)})

if __name__ == "__main__":
    # Test
    def cb(res):
        print("RESULT:", res)
    run_pipeline("X-lab2017/open-digger", "2023-01", cb)
