import os
import json
import sys

# 动态添加 opendigger 路径以便导入
current_dir = os.path.dirname(os.path.abspath(__file__))
# puppeteer/tasks -> puppeteer -> ChatDev
chatdev_root = os.path.dirname(os.path.dirname(current_dir))
if chatdev_root not in sys.path:
    sys.path.append(chatdev_root)

try:
    from opendigger.getdata import OpenPuppeteerDataCore
except ImportError:
    # Fallback: try relative import if running from puppeteer root
    # Assuming we are in ChatDev/puppeteer, ../opendigger is ChatDev/opendigger
    # We need to add ChatDev to path
    sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
    from opendigger.getdata import OpenPuppeteerDataCore

def run(runner, evaluator, results_dir, mode, data_limit=None):
    # 1. 准备数据
    repo_name = "X-lab2017/open-digger" # 默认仓库，后续可扩展为参数
    print(f"正在获取 {repo_name} 的数据...")
    
    try:
        core = OpenPuppeteerDataCore()
        df = core.build_aligned_dataset(repo_name)
    except Exception as e:
        print(f"数据获取初始化失败: {e}")
        return

    if df is None:
        print("数据获取失败！")
        return

    # 保存数据供 Agent 读取
    data_filename = f"{repo_name.replace('/', '_')}_context.csv"
    data_path = os.path.join(results_dir, data_filename)
    df.to_csv(data_path, index=False)
    print(f"数据已保存至: {data_path}")

    # 2. 构造 Task Prompt
    # 明确列名信息，防止 Agent 猜错大小写
    # 强制执行顺序：FeatureEngineer 必须先运行
    question = f"""
    Target Repository: {repo_name}
    Data File: {data_path}
    
    IMPORTANT: The data file is a CSV with the following columns (all lowercase):
    - 'month': Date string (YYYY-MM-DD)
    - 'openrank': Influence metric
    - 'activity': Activity metric
    - 'issue_response_time': Average issue response time
    - 'change_request_response_time': Average PR response time
    - 'inactive_contributors': Count of inactive contributors
    - 'churn_risk_activity': 0 or 1 label
    - 'churn_risk_contributor': 0 or 1 label

    Execution Plan (Strict Order):
    1. FeatureEngineer: 
       - MUST execute 'run_python' FIRST to read the file: `pd.read_csv('{data_path}')`.
       - Print `df.head()` and `df.columns` to verify data.
       - Calculate 6-month moving averages for 'openrank' and 'activity'.
       - Output the recent 6 months of data as JSON.
    
    2. Predictor: 
       - Use the data output by FeatureEngineer.
       - Use 'run_python' to fit an ExponentialSmoothing model on the last 12 months.
       - IMPORTANT CODE INSTRUCTION: Use `ExponentialSmoothing(data, trend='add', seasonal=None).fit()`.
       - DO NOT use `seasonal='Error'`.
       - Predict the next month's 'openrank' and 'activity'.
       - DO NOT create fake data.
    
    3. Explainer: 
       - Analyze the correlation between 'activity' and 'issue_response_time'.
       - Explain WHY the trend is changing (e.g., "Activity dropped because response time increased").
    
    4. Governor: 
       - Based on the 'churn_risk_activity' label and prediction, provide specific advice.
       - Example: If response time > 7 days, suggest "Setup auto-response bot".
    
    5. Arbitrator: 
       - Combine all outputs into a single JSON object.
       - Keys: 'analysis_summary', 'prediction_next_month', 'explanation', 'governance_advice'.
    """

    task = {
        "type": "OpenDiggerAnalysis",
        "Question": question,
        "id": 1,
        "concepts": ["OpenRank", "Activity", "Churn", "Governance"]
    }

    # 3. 运行推理
    print("开始多智能体推理...")
    
    # 训练循环
    if mode == "train":
        import random
        import glob
        
        # 获取所有训练数据
        train_data_dir = os.path.join(chatdev_root, "puppeteer", "data", "OpenDigger", "train")
        train_files = glob.glob(os.path.join(train_data_dir, "*_context.csv"))
        
        if not train_files:
            print(f"Warning: No training files found in {train_data_dir}. Using default.")
            train_files = [data_path]
            
        epochs = 5 # 示例：训练 5 轮
        for i in range(epochs):
            print(f"Training Epoch {i+1}/{epochs}")
            
            # 随机选择一个训练文件
            current_data_path = random.choice(train_files)
            current_repo_name = os.path.basename(current_data_path).replace("_context.csv", "")
            print(f"Using training data: {current_repo_name}")
            
            # 动态构造 Question
            current_question = f"""
    Target Repository: {current_repo_name}
    Data File: {current_data_path}
    
    IMPORTANT: The data file is a CSV with the following columns (all lowercase):
    - 'month': Date string (YYYY-MM-DD)
    - 'openrank': Influence metric
    - 'activity': Activity metric
    - 'issue_response_time': Average issue response time
    - 'change_request_response_time': Average PR response time
    - 'inactive_contributors': Count of inactive contributors
    - 'churn_risk_activity': 0 or 1 label
    - 'churn_risk_contributor': 0 or 1 label

    Execution Plan (Strict Order):
    1. FeatureEngineer: 
       - MUST execute 'run_python' FIRST to read the file: `pd.read_csv('{current_data_path}')`.
       - Print `df.head()` and `df.columns` to verify data.
       - Calculate 6-month moving averages for 'openrank' and 'activity'.
       - Output the recent 6 months of data as JSON.
    
    2. Predictor: 
       - Use the data output by FeatureEngineer.
       - Use 'run_python' to fit an ExponentialSmoothing model on the last 12 months.
       - IMPORTANT CODE INSTRUCTION: Use `ExponentialSmoothing(data, trend='add', seasonal=None).fit()`.
       - DO NOT use `seasonal='Error'`.
       - Predict the next month's 'openrank' and 'activity'.
       - DO NOT create fake data.
    
    3. Explainer: 
       - Analyze the correlation between 'activity' and 'issue_response_time'.
       - Explain WHY the trend is changing (e.g., "Activity dropped because response time increased").
    
    4. Governor: 
       - Based on the 'churn_risk_activity' label and prediction, provide specific advice.
       - Example: If response time > 7 days, suggest "Setup auto-response bot".
    
    5. Arbitrator: 
       - Combine all outputs into a single JSON object.
       - Keys: 'analysis_summary', 'prediction_next_month', 'explanation', 'governance_advice'.
    """
            
            task["Question"] = current_question
            task["id"] = i # 更新 ID 以区分不同轮次
            final_ans = runner.run_reasoning(task)
    else:
        # 测试模式只运行一次
        final_ans = runner.run_reasoning(task)

    # 4. 保存结果
    result_path = os.path.join(results_dir, "opendigger_report.jsonl")
    with open(result_path, "w", encoding="utf-8") as fd:
        record = {
            "id": task["id"],
            "repo": repo_name,
            "report": final_ans
        }
        fd.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"报告已生成: {result_path}")
