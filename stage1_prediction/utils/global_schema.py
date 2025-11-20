import json
from .schema_parser import schema_to_text

# 使用与你脚本完全相同的 schema 路径
SCHEMA_PATH = r"E:\accuracy\data\synthesis_schema_data_corpus\Sorted_corpus_0911\geography_5_csv_files_08051006\import_config.json"

schema_json = json.load(open(SCHEMA_PATH, "r", encoding="utf-8"))
# 统一处理字符串，避免多余空格差异
SCHEMA_TEXT = schema_to_text(schema_json).rstrip() + "\n"
