"""日志管理模块"""
import logging
import logging.handlers
from pathlib import Path

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name, log_dir="logs", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True)
        
        # 文件处理器（带轮转）
        fh = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        fh.setLevel(level)
        
        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def get_logger(self):
        return self.logger
