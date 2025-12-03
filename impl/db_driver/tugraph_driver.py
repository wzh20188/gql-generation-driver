import logging
from neo4j import GraphDatabase
from driver.evaluation import DatabaseDriver

class TuGraphAdapter(DatabaseDriver):
    """
    TuGraph 数据库适配器
    """
    def __init__(self, uri, user, password):
        self.uri = uri
        self.auth = (user, password)
        self.driver = None

    def connect(self):
        try:
            # TuGraph 默认端口通常也是 7687 (Bolt)
            self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
            self.driver.verify_connectivity()
            print(f"Connected to TuGraph at {self.uri}")
        except Exception as e:
            print(f"Failed to connect to TuGraph: {e}")
            self.driver = None

    def query(self, cypher: str, db_name: str = "default") -> list:
        """
        执行查询
        :param cypher: Cypher 查询语句
        :param db_name: TuGraph 中的图名称
        """
        if not self.driver:
            return None
        
        try:
            with self.driver.session(database=db_name) as session:
                result = session.run(cypher).data()
                return result
        except Exception as e:
            return None

    def close(self):
        if self.driver:
            self.driver.close()