import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from openai import OpenAI
from driver.prediction import Text2GraphSystem
from impl.text2graph_system.utils import schema_to_text, clean_query

class QwenZeroshotSystem(Text2GraphSystem):
    def __init__(self, config: dict):
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.max_workers = config.get("max_workers", 5)
        self.level_fields = config.get("level_fields", [])
        
        # 加载 Schema
        schema_path = config["schema_path"]
        schema_json = json.load(open(schema_path, "r", encoding="utf-8"))
        self.schema_text = schema_to_text(schema_json).rstrip() + "\n"

    def _build_prompt(self, nl_question: str):
        return [
            {
                "role": "system",
                "content": (
                    "You are an expert in graph query languages.\n"
                    "The database schema is as follows:\n"
                    f"{self.schema_text}\n\n"
                    "Your task: Given a natural language question, output ONLY one query:\n"
                    "Cypher (for Neo4j)\n\n"
                    "Requirements:\n"
                    "- Use the schema exactly (labels, properties, edge types).\n"
                    "- Maintain the exact relationship types and directions.\n"
                    "- Preserve all temporal constraints.\n"
                    "- Use DISTINCT when necessary.\n"
                    "- For path length, use length(p)-1 if matching multi-hop paths.\n"
                    "- Do not merge different edge types unless explicitly required.\n"
                    "- Output must be plain query only, no comments, no explanation.\n"
                )
            },
            {"role": "user", "content": nl_question.strip()}
        ]

    def _call_single(self, client, question, max_retries=3):
        for _ in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model=self.model,
                    messages=self._build_prompt(question),
                    extra_body={"enable_thinking": False},
                    timeout=30
                )
                return completion.choices[0].message.content.strip()
            except Exception:
                time.sleep(1)
        return None

    def predict_batch(self, data: list) -> list:
        def process_record(item):
            # 每个线程独立实例化 Client
            local_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            result = item.copy()
            
            for nl_field, query_field in self.level_fields:
                question = item.get(nl_field)
                if not question:
                    result[query_field] = None
                    continue
                
                raw_pred = self._call_single(local_client, question)
                # 注意：这里只做清理，不做执行。
                # 为了保持输出一致性，在这里调用 clean_query
                result[query_field] = clean_query(raw_pred)
            
            return result

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(process_record, item) for item in data]
            for f in tqdm(as_completed(futures), total=len(futures), desc="Predicting"):
                results.append(f.result())
        
        # 保持原逻辑的排序方式
        try:
            results.sort(key=lambda x: int(str(x.get("instance_id", "0")).split("_")[-1]))
        except:
            pass
            
        return results