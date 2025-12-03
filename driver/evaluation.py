from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union

class DatabaseDriver(ABC):
    """数据库驱动接口"""
    @abstractmethod
    def connect(self):
        """建立连接"""
        pass

    @abstractmethod
    def query(self, cypher: str, db_name: str) -> Union[List[Dict], None]:
        """执行查询，返回结果列表；若报错返回 None"""
        pass

    @abstractmethod
    def close(self):
        """关闭连接"""
        pass

class BaseMetric(ABC):
    """评估指标接口"""
    @abstractmethod
    def compute(self, predictions: List[str], golds: List[str], **kwargs) -> Any:
        """计算指标"""
        pass