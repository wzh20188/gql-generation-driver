from abc import ABC, abstractmethod
from typing import List, Dict

class Text2GraphSystem(ABC):
    """生成系统接口"""
    @abstractmethod
    def predict_batch(self, data: List[Dict]) -> List[Dict]:
        """批量预测"""
        pass