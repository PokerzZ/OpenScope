"""数据验证模块"""
class DataValidator:
    @staticmethod
    def validate_numeric(value, min_val=None, max_val=None):
        if not isinstance(value, (int, float)): raise TypeError()
        return True
