import os
import sys
import json
import threading
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS

# Add parent directory to path
# 将父目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from web_ui.backend.inference import run_pipeline
from utils.logging import LogManager

app = Flask(__name__)
CORS(app)  # 为所有路由启用 CORS

# 全局日志历史和同步
log_history = []
log_condition = threading.Condition()

def add_log(message_str):
    with log_condition:
        log_history.append(message_str)
        log_condition.notify_all()

# 自定义日志处理程序将日志推送到历史记录
import logging
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            # 作为 SSE 数据发送
            sse_msg = f"data: {json.dumps({'type': 'log', 'message': log_entry})}\n\n"
            add_log(sse_msg)
        except Exception:
            pass

# 设置日志拦截
queue_handler = QueueHandler()
queue_handler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s] %(message)s'))
logging.getLogger().addHandler(queue_handler)

# 专门捕获 'global' 日志记录器
global_logger = logging.getLogger('global')
global_logger.setLevel(logging.INFO)
global_logger.addHandler(queue_handler)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    repo = data.get('repo')
    date = data.get('date')
    
    if not repo or not date:
        return jsonify({"error": "Missing repo or date"}), 400

    # 清除以前的日志
    with log_condition:
        log_history.clear()
        
    # 定义回调来处理结果
    def on_result(result):
        # 结果可能是字典或字符串。
        # 检查是否包含错误
        if isinstance(result, dict) and 'error' in result:
             sse_msg = f"data: {json.dumps({'type': 'error', 'message': result['error']})}\n\n"
        else:
             sse_msg = f"data: {json.dumps({'type': 'result', 'payload': result})}\n\n"
        add_log(sse_msg)

    # 启动独立线程
    thread = threading.Thread(target=run_pipeline, args=(repo, date, on_result))
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/graphs/<path:filepath>')
def serve_graph(filepath):
    """Serve generated graph HTML files"""
    try:
        # 从相对路径构建绝对路径
        puppeteer_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        full_path = os.path.join(puppeteer_dir, filepath)
        
        if os.path.exists(full_path):
            return send_file(full_path)
        else:
            return f"File not found: {full_path}", 404
    except Exception as e:
        return str(e), 404

@app.route('/stream')
def stream():
    def event_stream():
        last_index = 0
        while True:
            messages_to_send = []
            with log_condition:
                # 如果历史记录已清除（索引重置）
                if last_index > len(log_history):
                    last_index = 0

                if last_index < len(log_history):
                    messages_to_send = log_history[last_index:]
                    last_index = len(log_history)
                else:
                    log_condition.wait(timeout=1.0)
                    # 等待后再次检查
                    if last_index > len(log_history): last_index = 0
                    if last_index < len(log_history):
                        messages_to_send = log_history[last_index:]
                        last_index = len(log_history)
            
            for msg in messages_to_send:
                yield msg
            
            # 保持连接
            yield ": keep-alive\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    # 确保 opendigger cli 权限
    try:
        pass # OpenPuppeteerDataCore 在初始化时处理检查，但我们无法在这里轻松初始化它。
    except:
        pass
        
    print("Starting OpenScope Web UI on http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000, debug=False)
