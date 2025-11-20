import argparse
import json
import os
import warnings
from config import DB_URI, DB_USER, DB_PASSWORD, DEFAULT_DBGPT_ROOT, LEVEL_FIELDS
from preprocess.cleaners import clean_query
from executor.evaluator import ExecutionEvaluator
from metrics.google_bleu import compute_google_bleu
from metrics.external_apis import run_external_metrics

warnings.filterwarnings("ignore")

def parse_args():
    parser = argparse.ArgumentParser(description="Stage 2 Evaluation Driver")
    parser.add_argument("--input", type=str, required=True, help="Predicted JSON file")
    parser.add_argument("--dbgpt_root", type=str, default=DEFAULT_DBGPT_ROOT, help="dbgpt-hub-gql path")
    parser.add_argument("--db_uri", type=str, default=DB_URI)
    parser.add_argument("--db_user", type=str, default=DB_USER)
    parser.add_argument("--db_pass", type=str, default=DB_PASSWORD)
    return parser.parse_args()

def main():
    args = parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        return

    print(f"Loading predictions from: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 初始化评估器
    evaluator = ExecutionEvaluator(args.db_uri, args.db_user, args.db_pass)

    try:
        # 遍历不同难度的 Level
        for query_key, _ in LEVEL_FIELDS:
            print(f"\n{'='*40}")
            print(f"Evaluating: {query_key}")
            print(f"{'='*40}")

            cleaned_preds = []
            cleaned_golds = []
            ea_correct = 0
            total = 0

            for item in data:
                # 1. 数据提取
                raw_gold = item.get("gql_query", "")
                raw_pred = item.get(query_key, "") # 根据 Level 获取对应的预测
                db_id = item.get("db_id", "geography")

                # 2. 数据清洗
                gold_clean = clean_query(raw_gold)
                pred_clean = clean_query(raw_pred)

                # 3. Execution Accuracy (EA) 计算
                # 如果预测为空，直接判错，不查库
                if not pred_clean:
                    is_correct = 0
                else:
                    # 返回 1 (对), 0 (错), -1 (系统错误)
                    score = evaluator.evaluate(pred_clean, gold_clean, database=db_id)
                    is_correct = 1 if score == 1 else 0
                
                ea_correct += is_correct
                total += 1
                
                cleaned_preds.append(pred_clean)
                cleaned_golds.append(gold_clean)

            # 4. 计算批量指标
            ea_score = ea_correct / total if total > 0 else 0.0
            
            print("Calculating batch metrics (BLEU, Grammar, Similarity)...")
            bleu_score = compute_google_bleu(cleaned_preds, cleaned_golds)
            ext_scores = run_external_metrics(cleaned_preds, cleaned_golds, args.dbgpt_root)

            # 5. 输出报告
            print(f"\n Results for {query_key}:")
            print(f"   - Total Samples : {total}")
            print(f"   - EA (Accuracy) : {ea_score:.2%}")
            print(f"   - Grammar       : {ext_scores['Grammar']:.2%}")
            print(f"   - Similarity    : {ext_scores['Similarity']:.4f}")
            print(f"   - Google BLEU   : {bleu_score if isinstance(bleu_score, str) else f'{bleu_score:.4f}'}")
    
    finally:
        evaluator.close()
        print("\n Evaluation finished.")

if __name__ == "__main__":
    main()