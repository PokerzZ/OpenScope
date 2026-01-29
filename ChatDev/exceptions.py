"""异常定义模块"""

class OpenScopeException(Exception):
    """基础异常类"""
    pass

class ConfigError(OpenScopeException):
    """配置错误"""
    pass

class DataError(OpenScopeException):
    """数据错误"""
    pass

class ValidationError(OpenScopeException):
    """验证错误"""
    pass

class APIError(OpenScopeException):
    """API调用错误"""
    def __init__(self, status_code, message, response=None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"API Error {status_code}: {message}")

class TimeoutError(OpenScopeException):
    """超时错误"""
    pass

class ModelError(OpenScopeException):
    """模型相关错误"""
    pass
