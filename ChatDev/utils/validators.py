"""数据验证模块"""

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_numeric(value, min_val=None, max_val=None):
        """验证数值范围"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected numeric type, got {type(value)}")
        if min_val is not None and value < min_val:
            raise ValueError(f"Value {value} is less than minimum {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"Value {value} exceeds maximum {max_val}")
        return True
    
    @staticmethod
    def validate_string(value, min_len=0, max_len=None):
        """验证字符串长度"""
        if not isinstance(value, str):
            raise TypeError(f"Expected string, got {type(value)}")
        if len(value) < min_len:
            raise ValueError(f"String length {len(value)} is less than {min_len}")
        if max_len and len(value) > max_len:
            raise ValueError(f"String length {len(value)} exceeds {max_len}")
        return True
    
    @staticmethod
    def validate_dict_keys(data, required_keys):
        """验证字典必需的键"""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")
        missing = set(required_keys) - set(data.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")
        return True
