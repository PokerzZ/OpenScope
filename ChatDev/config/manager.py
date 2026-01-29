"""配置管理模块"""
import os
import json
from typing import Dict, Any

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file=None):
        self.config = {}
        if config_file:
            self.load_from_file(config_file)
        self.load_from_env()
    
    def load_from_file(self, filepath):
        """从JSON文件加载配置"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            self.config.update(json.load(f))
    
    def load_from_env(self, prefix="APP_"):
        """从环境变量加载配置"""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self.config[config_key] = value
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return self.config.copy()
