import os

# 数据库连接配置
DB_URI = "bolt://localhost:7687"
DB_USER = "admin"
DB_PASSWORD = "73@TuGraph"

# 默认路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DBGPT_ROOT = os.path.join(BASE_DIR, "dbgpt-hub-gql", "src", "dbgpt_hub_gql")
TEMP_DIR = os.path.join(BASE_DIR, "temp_eval_results")

# 评测层级定义
LEVEL_FIELDS = [
    ("initial_query", "initial_results.json"),
    ("level_1_query", "level_1_results.json"),
    ("level_2_query", "level_2_results.json"),
    ("level_3_query", "level_3_results.json"),
    ("level_4_query", "level_4_results.json"),
]