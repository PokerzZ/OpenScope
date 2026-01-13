import os
import yaml
import json
from tasks.runner import BenchmarkRunner

def main():
    # 1. 配置路径
    personas_path = "personas/opendigger_personas.jsonl"
    global_config_path = "config/global.yaml"
    policy_config_path = "config/policy.json"
    
    # 加载全局配置
    with open(global_config_path, "r") as f:
        global_config = yaml.safe_load(f)

    # 更新 policy.json 以确保使用正确的模型和模式
    with open(policy_config_path, 'r') as f:
        policy_config = json.load(f)
    
    # 设置为 test 模式以避免训练，并指向正确的 checkpoint 目录
    policy_config["dataset_name"] = "OpenDiggerMMLU"
    policy_config["dataset_mode"] = "test"
    policy_config['paths']["checkpoint_path"] = "checkpoint/OpenDiggerMMLU_test"
    
    with open(policy_config_path, 'w') as f:
        json.dump(policy_config, f, indent=4)

    # 2. 初始化 Runner
    runner = BenchmarkRunner(personas_path, global_config)

    # 3. 定义手动输入的数据
    # 您可以在这里修改 manual_data 字符串来测试不同的数据
    manual_data = """
     month  openrank  activity  issue_response_time  change_request_response_time  inactive_contributors
2015-01-01     22.94    431.87                    0                             0                    0.0
2015-02-01     48.74    476.34                    0                             0                    0.0
2015-03-01     59.72    408.14                    0                             0                    0.0
2015-04-01     81.25    465.29                    0                             0                    0.0
2015-05-01     92.50    465.37                    0                             0                    0.0
2015-06-01    119.60    576.24                    0                             0                    0.0
"""
    target_month = "2015-07"
    
    # 构建 Prompt
    question = f"""You are an Open Source Community Manager. Analyze the following data for repository 'golang/go' from 2015-01 to 2015-06:

{manual_data}

Based on the trend, how will the 'activity' metric change in the next month ({target_month})?

Options:
A: Significant Increase (> 10%)
B: Stable/Slight Increase (0% to 10%)
C: Stable/Slight Decrease (-10% to 0%)
D: Significant Decrease (< -10%)"""

    # 构建任务对象
    task = {
        "type": "OpenDiggerMMLU",
        "Question": question,
        "Answer": "Unknown", # 推理模式下不需要真实标签
        "id": "manual_test_001"
    }

    print("-" * 50)
    print("Starting Manual Inference (开始手动推理)")
    print("-" * 50)
    print(f"Input Question (输入问题):\n{question}")
    print("-" * 50)
    
    # 4. 运行推理
    final_ans = runner.run_reasoning(task)
    
    print("-" * 50)
    print(f"Final Answer (最终预测): {final_ans}")
    print("-" * 50)

    # 5. 可视化日志
    visualize_logs()

def visualize_logs():
    import glob
    import json
    
    # 找到最新的日志目录
    log_base_dir = "logs/OpenDiggerMMLU"
    if not os.path.exists(log_base_dir):
        print("No logs found.")
        return

    # 获取所有子目录并按修改时间排序
    subdirs = [os.path.join(log_base_dir, d) for d in os.listdir(log_base_dir) if os.path.isdir(os.path.join(log_base_dir, d))]
    if not subdirs:
        print("No log directories found.")
        return
        
    latest_log_dir = max(subdirs, key=os.path.getmtime)
    print(f"Visualizing logs from: {latest_log_dir}")
    print("=" * 50)

    # 查找所有 path_*.jsonl 文件
    path_files = sorted(glob.glob(os.path.join(latest_log_dir, "path_*.jsonl")))
    
    for path_file in path_files:
        path_id = os.path.basename(path_file).split('_')[1].split('.')[0]
        print(f"Reasoning Path {path_id}:")
        print("-" * 20)
        
        try:
            with open(path_file, 'r') as f:
                steps = json.load(f)
                
            for i, step in enumerate(steps):
                agent = step.get('agent', 'Unknown')
                action = step.get('action', {}).get('action', 'Unknown')
                result = step.get('result', {}).get('step_data', '')
                
                print(f"Step {i+1}: Agent [{agent}] -> Action [{action}]")
                if result:
                    # 只打印结果的前几行，避免太长
                    preview = result.strip().split('\n')
                    print(f"  Result Preview: {preview[0]}...")
                    if len(preview) > 1:
                         print(f"                  {preview[-1]}")
                print()
        except Exception as e:
            print(f"Error reading {path_file}: {e}")
        
        print("=" * 50)

if __name__ == "__main__":
    main()
