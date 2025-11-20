import os
import json
import re
import shutil
import subprocess
import logging
import warnings
from neo4j import GraphDatabase
import evaluate

# 忽略部分警告
warnings.filterwarnings("ignore")

# =============================================================================
# 配置部分
# =============================================================================
# 请确认这是你的真实路径
DBGPT_HUB_GQL_ROOT = "/home/ubuntu/dbgpt-hub-gql"
TEMP_DIR = "temp_eval_results"


# =============================================================================
# 文本提取与清洗工具
# =============================================================================
def extract_cypher(pred: str):
    pattern = r"```cypher(.*?)```"
    match = re.search(pattern, pred, re.DOTALL)
    if match:
        return match.group(1).replace("\n", " ").strip()
    return pred.replace("\n", " ").strip()


def extract_gql(pred: str):
    pattern = r"```gql(.*?)```"
    match = re.search(pattern, pred, re.DOTALL)
    if match:
        return match.group(1).replace("\n", " ").strip()
    return pred.replace("\n", " ").strip()


def clean_query(pred: str):
    """综合清洗逻辑"""
    if not isinstance(pred, str):
        return ""

    pred = pred.replace("<think>\n\n</think>\n\n", "")
    pred = re.sub(r"<think>.*?</think>", "", pred, flags=re.DOTALL)

    if "```cypher" in pred:
        return extract_cypher(pred)
    if "```gql" in pred:
        return extract_gql(pred)
    return pred.replace("\n", " ").strip()


# =============================================================================
# 执行评测器 (EA)
# =============================================================================
class ExecutionEvaluator:
    def __init__(self, uri="bolt://localhost:7687", user="admin", password="73@TuGraph"):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print(f"Connected to TuGraph at {uri}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def compare_results(self, res_gold, res_predict):
        def normalize(value):
            if isinstance(value, float):
                return round(value, 9)
            if isinstance(value, (int, str, bool)) or value is None:
                return value
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if hasattr(value, "total_seconds"):
                return str(value)
            if isinstance(value, (list, tuple)):
                return tuple(normalize(v) for v in value)
            if isinstance(value, dict):
                return tuple(sorted((k, normalize(v)) for k, v in value.items()))
            return str(value)

        def normalize_row(row):
            return tuple(normalize(v) for v in row.values())

        gold_set = {normalize_row(r) for r in res_gold}
        pred_set = {normalize_row(r) for r in res_predict}
        return gold_set == pred_set

    def evaluate(self, query_predict, query_gold, database="geography"):
        """返回 1=正确, 0=执行失败或不一致, -1=gold 执行失败"""
        if not self.driver:
            return -1

        # Gold
        try:
            with self.driver.session(database=database) as session:
                res_gold = session.run(query_gold).data()
        except Exception:
            return -1

        # Predict
        try:
            with self.driver.session(database=database) as session:
                res_predict = session.run(query_predict).data()
        except Exception:
            return 0

        return 1 if self.compare_results(res_gold, res_predict) else 0


# =============================================================================
# 批量评测逻辑 (Grammar, Similarity)
# =============================================================================
def run_batch_eval(pred_list, gold_list, dataset_type="text2cypher"):
    os.makedirs(TEMP_DIR, exist_ok=True)
    pred_file = os.path.abspath(os.path.join(TEMP_DIR, "predictions.txt"))
    gold_file = os.path.abspath(os.path.join(TEMP_DIR, "gold.txt"))

    with open(pred_file, "w", encoding="utf-8") as f:
        f.write("\n".join(pred_list))

    with open(gold_file, "w", encoding="utf-8") as f:
        f.write("\n".join(gold_list))

    results = {}

    # ----------------- Google BLEU -----------------
    print("Evaluating Google-BLEU...")
    try:
        google_bleu = evaluate.load("google_bleu")
        preds = [p.strip() for p in pred_list]
        golds = [g.strip() for g in gold_list]
        bleu_res = google_bleu.compute(predictions=preds, references=golds)
        results["Google_BLEU"] = bleu_res["google_bleu"]
    except Exception as e:
        print(f"Google BLEU failed: {e}")
        results["Google_BLEU"] = "N/A (Error)"

    # ----------------- Grammar / Similarity -----------------
    current_dir = os.getcwd()

    if os.path.exists(DBGPT_HUB_GQL_ROOT):
        os.chdir(DBGPT_HUB_GQL_ROOT)
        impl = "tugraph-db" if dataset_type == "text2cypher" else "iso-gql"

        for etype in ["grammar", "similarity"]:
            print(f"Evaluating {etype} (via external tool)...")
            try:
                cmd = [
                    "python3",
                    "dbgpt_hub_gql/eval/evaluation.py",
                    "--input",
                    pred_file,
                    "--gold",
                    gold_file,
                    "--etype",
                    etype,
                    "--impl",
                    impl,
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                log_file = "dbgpt_hub_gql/output/logs/eval.log"
                score = 0.0

                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8") as f:
                        log_content = f.read().strip()

                        # 1. 尝试解析为数字
                        try:
                            score = float(log_content)
                        except ValueError:
                            # 2. 尝试解析 JSON
                            try:
                                log_json = json.loads(log_content)
                                if isinstance(log_json, list):
                                    valid_scores = [x["score"] for x in log_json if x["score"] >= 0]
                                    score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
                                elif isinstance(log_json, dict):
                                    score = (
                                        log_json.get("accuracy", 0.0)
                                        if etype == "grammar"
                                        else log_json.get("score", 0.0)
                                    )
                            except Exception:
                                score = 0.0

                results[etype.capitalize()] = score

            except Exception as e:
                print(f"{etype} evaluation failed: {e}")
                results[etype.capitalize()] = 0.0

        os.chdir(current_dir)

    else:
        print(f"Warning: Directory '{DBGPT_HUB_GQL_ROOT}' not found.")
        results["Grammar"] = 0.0
        results["Similarity"] = 0.0

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    return results


# =============================================================================
# 主程序
# =============================================================================
if __name__ == "__main__":
    evaluator = ExecutionEvaluator()

    INPUT_FILE = "/home/ubuntu/predicted.json"

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found: {INPUT_FILE}")
        exit(1)

    print(f"Loading data from {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    LEVEL_FIELDS = [
        ("initial_query", "initial_results.json"),
        ("level_1_query", "level_1_results.json"),
        ("level_2_query", "level_2_results.json"),
        ("level_3_query", "level_3_results.json"),
        ("level_4_query", "level_4_results.json"),
    ]

    for query_key, output_file in LEVEL_FIELDS:
        print("\n==============================")
        print(f" Processing: {query_key}")
        print("==============================")

        total = 0
        ea_correct = 0
        cleaned_preds = []
        cleaned_golds = []

        for item in data:
            raw_gold = item.get("gql_query", "")
            raw_pred = item.get(query_key, "")
            db_id = item.get("db_id", "geography")

            pred_clean = clean_query(raw_pred)
            gold_clean = clean_query(raw_gold)

            if not pred_clean:
                total += 1
                cleaned_preds.append("")
                cleaned_golds.append(gold_clean)
                continue

            ea_score = evaluator.evaluate(pred_clean, gold_clean, database=db_id)
            ea_correct += 1 if ea_score == 1 else 0

            cleaned_preds.append(pred_clean)
            cleaned_golds.append(gold_clean)
            total += 1

        ea_final = ea_correct / total if total > 0 else 0

        print("Running Batch Metrics...")
        batch_metrics = run_batch_eval(cleaned_preds, cleaned_golds, dataset_type="text2cypher")

        print(f"----- Evaluation Report for {query_key} -----")
        print(f"Total Instances : {total}")
        print(f"EA (Accuracy)   : {ea_final:.2%}")

        grammar_val = batch_metrics.get("Grammar", 0.0)
        sim_val = batch_metrics.get("Similarity", 0.0)

        g_str = f"{grammar_val:.2%}" if isinstance(grammar_val, (int, float)) else str(grammar_val)
        s_str = f"{sim_val:.4f}" if isinstance(sim_val, (int, float)) else str(sim_val)

        print(f"Grammar         : {g_str}")
        print(f"Similarity      : {s_str}")
        print(f"Google BLEU     : {batch_metrics.get('Google_BLEU', 'N/A')}")
        print("---------------------------------------------")

    evaluator.close()
    print("\n✨ All evaluation done!")
