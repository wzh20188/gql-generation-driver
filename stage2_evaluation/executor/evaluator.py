from neo4j import GraphDatabase
import logging

class ExecutionEvaluator:
    def __init__(self, uri, user, password):
        self.uri = uri
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print(f"✅ Connected to Database at {uri}")
        except Exception as e:
            print(f"❌ Failed to connect to Database: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def _normalize(self, value):
        """递归标准化数据格式，处理浮点数精度和时间格式"""
        if isinstance(value, float):
            return round(value, 9)
        elif isinstance(value, (int, str, bool)) or value is None:
            return value
        elif hasattr(value, "isoformat"):
            return value.isoformat()
        elif hasattr(value, "total_seconds"):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return tuple(self._normalize(v) for v in value)
        elif isinstance(value, dict):
            return tuple(sorted((k, self._normalize(v)) for k, v in value.items()))
        else:
            return str(value)

    def _compare_results(self, res_gold, res_predict):
        """比较两个结果集是否一致（忽略顺序）"""
        def normalize_row(row):
            return tuple(self._normalize(v) for v in row.values())

        gold_set = {normalize_row(r) for r in res_gold}
        pred_set = {normalize_row(r) for r in res_predict}
        return gold_set == pred_set

    def evaluate(self, query_predict, query_gold, database="geography"):
        """
        执行预测查询和标准查询，并比对结果。
        Return: 1 (Correct), 0 (Incorrect), -1 (System Error/Gold Error)
        """
        if not self.driver:
            return -1
        
        # 1. 获取 Gold 结果
        try:
            with self.driver.session(database=database) as session:
                res_gold = session.run(query_gold).data()
        except Exception as e:
            # Gold 语句本身执行失败，可能是数据问题
            return -1
            
        # 2. 获取 Predict 结果
        try:
            with self.driver.session(database=database) as session:
                res_predict = session.run(query_predict).data()
        except Exception as e:
            # 预测语句语法错误或运行时错误
            return 0
            
        # 3. 比对
        return 1 if self._compare_results(res_gold, res_predict) else 0