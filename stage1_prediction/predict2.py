import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from openai import OpenAI


# -------------------------------
# 1. schema JSON -> schema TEXT（与文件B完全一致）
# -------------------------------
def schema_to_text(schema_json):
    lines, vertices, edges = [], [], []
    for item in schema_json["schema"]:
        label = item["label"]
        type_ = item["type"]
        props = item.get("properties", [])
        props_str = ", ".join(
            [f'{p["name"]}: {p["type"]}' + (" (optional)" if p.get("optional") else "")
             for p in props]
        )

        if type_ == "VERTEX":
            primary = item.get("primary")
            if primary:
                vertices.append(f"- {label} [primary: {primary}] ({props_str})")
            else:
                vertices.append(f"- {label}({props_str})")

        elif type_ == "EDGE":
            temporal = item.get("temporal")
            if temporal:
                edges.append(f"- {label} [temporal: {temporal}] ({props_str})")
            else:
                edges.append(f"- {label}({props_str})")

    if vertices:
        lines.append("Vertex types:")
        lines.extend(vertices)
    if edges:
        lines.append("\nEdge types:")
        lines.extend(edges)

    return "\n".join(lines)



# -------------------------------
# 2. 全局 schema_text（与文件B完全一致）
# -------------------------------
schema_path = r"E:\accuracy\data\synthesis_schema_data_corpus\Sorted_corpus_0911\geography_5_csv_files_08051006\import_config.json"
schema_json = json.load(open(schema_path, "r", encoding="utf-8"))
SCHEMA_TEXT = schema_to_text(schema_json)



# -------------------------------
# 3. Prompt（完全复制文件B）
# -------------------------------
def build_prompt(nl_question: str):
    return [
        {
            "role": "system",
            "content": (
                "You are an expert in graph query languages.\n"
                "The database schema is as follows:\n"
                f"{SCHEMA_TEXT}\n\n"
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



# -------------------------------
# 4. 单条模型调用（完全复制文件B）
# -------------------------------
def call_single_instance(client, instance_id, question, model, max_retries=3, timeout=30):
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=build_prompt(question),
                extra_body={"enable_thinking": False},
                timeout=timeout
            )
            return completion.choices[0].message.content.strip()

        except Exception:
            if attempt == max_retries:
                return None
            time.sleep(1)



# -------------------------------
# 5. 多级生成（文件A新增）
# -------------------------------
LEVEL_FIELDS = [
    ("initial_nl", "initial_query"),
    ("level_1", "level_1_query"),
    ("level_2", "level_2_query"),
    ("level_3", "level_3_query"),
    ("level_4", "level_4_query")
]


def predict_all_levels(data, api_key, base_url, model="qwen-plus", max_workers=5):

    def process_record(item):
        local_client = OpenAI(api_key=api_key, base_url=base_url)
        result = item.copy()
        instance_id = item["instance_id"]

        for nl_field, query_field in LEVEL_FIELDS:
            question = item.get(nl_field)
            if not question:
                result[query_field] = None
                continue

            cypher = call_single_instance(
                local_client,
                instance_id,
                question,
                model
            )
            result[query_field] = cypher

        return result


    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(process_record, item) for item in data]

        for f in tqdm(as_completed(futures), total=len(futures), desc="Predicting"):
            results.append(f.result())

    results.sort(key=lambda x: int(x["instance_id"].split("_")[-1]))
    return results



# -------------------------------
# 6. 主程序
# -------------------------------
if __name__ == "__main__":

    input_path = r"E:\accuracy\data\4_level_results_test\4_level_results_test\geography_5_csv_files_08051006_corpus_seeds.json"
    output_path = r"E:\accuracy\data\4_level_results_test\4_level_results_test\4_levels_predicted.json"

    api_key = "sk-5786643bb9c14649902802b03a98c39e"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    data = json.load(open(input_path, "r", encoding="utf-8"))

    results = predict_all_levels(
        data,
        api_key,
        base_url,
        model="qwen-plus",
        max_workers=5
    )

    json.dump(results, open(output_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("\n 预测完成！结果保存到：", output_path)
