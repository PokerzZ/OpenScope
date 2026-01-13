from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import sys
import os
import yaml
import logging
from typing import List

# 将父目录添加到路径以导入 puppeteer 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tasks.runner import BenchmarkRunner
from inference.reasoning.reasoning import GraphReasoning
from inference.graph.agent_graph import AgentGraph
from agent.register.register import agent_global_registry

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.history: List[str] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # 发送历史记录到新连接
        for message in self.history:
            await websocket.send_text(message)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        self.history.append(message)
        # 可选：限制历史记录大小以防止内存问题
        if len(self.history) > 10000:
            self.history = self.history[-10000:]
            
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# 自定义 Logger 将日志重定向到 WebSocket
class WebSocketLogger(logging.Handler):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.loop = asyncio.get_event_loop()

    def emit(self, record):
        try:
            msg = self.format(record)
            # 获取可以进行清理 JSON 解析的原始消息内容（无格式化）
            raw_msg = record.getMessage()

            # 尽可能将日志消息解析为结构，或作为原始文本发送
            log_data = {
                "type": "log",
                "level": record.levelname,
                "message": msg,
                "raw_content": raw_msg,
                "timestamp": record.created
            }
            
            # 检查是否是我们用于可视化的特殊日志格式
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                if "[Reasoning Path" in record.msg:
                     log_data["category"] = "path_update"
                elif "Agent Sequence:" in record.msg:
                     log_data["category"] = "agent_sequence"
            
            # 使用 run_coroutine_threadsafe 从同步上下文调用异步方法
            asyncio.run_coroutine_threadsafe(
                self.manager.broadcast(json.dumps(log_data)), 
                self.loop
            )
        except Exception:
            self.handleError(record)

# 设置日志
ws_handler = WebSocketLogger(manager)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ws_handler.setFormatter(formatter)

# 附加到全局日志
global_logger = logging.getLogger('global')
global_logger.addHandler(ws_handler)
global_logger.setLevel(logging.INFO)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            if request_data.get("action") == "start_inference":
                repo_name = request_data.get("repo_name", "golang/go")
                await run_inference_task(repo_name)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_inference_task(repo_name):
    # 配置
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    personas_path = os.path.join(base_path, "personas/opendigger_personas.jsonl")
    global_config_path = os.path.join(base_path, "config/global.yaml")
    policy_config_path = os.path.join(base_path, "config/policy.json")

    with open(global_config_path, "r") as f:
        global_config = yaml.safe_load(f)
    
    # 确保测试模式
    with open(policy_config_path, 'r') as f:
        policy_config = json.load(f)
    policy_config["dataset_name"] = "OpenDiggerMMLU"
    policy_config["dataset_mode"] = "test"
    policy_config['paths']["checkpoint_path"] = "checkpoint/OpenDiggerMMLU_test"
    with open(policy_config_path, 'w') as f:
        json.dump(policy_config, f, indent=4)

    # 初始化 Runner
    runner = BenchmarkRunner(personas_path, global_config)
    
    # 构建任务
    # 在真实场景中，我们会获取仓库的真实数据
    # 对于演示，我们使用手动数据模板
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
    question = f"""You are an Open Source Community Manager. Analyze the following data for repository '{repo_name}' from 2015-01 to 2015-06:

{manual_data}

Based on the trend, how will the 'activity' metric change in the next month ({target_month})?

Options:
A: Significant Increase (> 10%)
B: Stable/Slight Increase (0% to 10%)
C: Stable/Slight Decrease (-10% to 0%)
D: Significant Decrease (< -10%)"""

    task = {
        "type": "OpenDiggerMMLU",
        "Question": question,
        "Answer": "Unknown",
        "id": "web_test_001"
    }

    await manager.broadcast(json.dumps({
        "type": "status",
        "status": "started",
        "message": f"Starting inference for {repo_name}..."
    }))

    # 在单独的线程中运行推理以避免阻塞 WebSocket
    # 注意：这是一个简化的集成。理想情况下，我们将 Runner 重构为异步或使用适当的后台任务
    try:
        # 我们需要在执行器中运行它，因为 runner.run_reasoning 是阻塞的
        loop = asyncio.get_event_loop()
        final_ans = await loop.run_in_executor(None, lambda: runner.run_reasoning(task))
        
        await manager.broadcast(json.dumps({
            "type": "result",
            "final_answer": final_ans
        }))
        
    except Exception as e:
        await manager.broadcast(json.dumps({
            "type": "error",
            "message": str(e)
        }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
