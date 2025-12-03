# import json
# import argparse
# import os
# from impl.text2graph_system.qwen_zeroshot_system import QwenZeroshotSystem
# from impl.db_driver.tugraph_driver import TuGraphAdapter
# from impl.evaluation.metrics import ExecutionAccuracy, GoogleBleu, ExternalMetric
# from impl.text2graph_system.utils import clean_query

# def load_config(path="experiment/test_config"):
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--config", default="experiment/test_config.json", help="Path to config file")
#     args = parser.parse_args()
#     cfg = load_config(args.config)
#     db_driver = None

#     # 1. Prediction Phase
#     data_path = cfg["data"]["input_path"]
#     output_path = cfg["data"]["output_path"]

#     if cfg["pipeline"]["run_prediction"]:
#         print(f"Loading raw data from {data_path}...")
#         with open(data_path, "r", encoding="utf-8") as f:
#             raw_data = json.load(f)
#         print("Initializing Text2Graph System...")
#         system = QwenZeroshotSystem(self.cfg["prediction"])
#         print("Running Prediction Batch...")
#         results = system.predict_batch(raw_data)
#         os.makedirs(os.path.dirname(output_path), exist_ok=True)
#         with open(output_path, "w", encoding="utf-8") as f:
#             json.dump(results, f, indent=2, ensure_ascii=False)
#         print(f"Predictions saved to {output_path}")
#     else:
#         print(f"Skipping prediction. Loading existing results from {output_path}...")
#         with open(output_path, "r", encoding="utf-8") as f:
#             results = json.load(f)

#     # 2. Evaluation Phase
#     if cfg["pipeline"]["run_evaluation"]:
#         print("\nStarting Evaluation...")
#         eval_cfg = cfg["evaluation"]

#         # [EA 模式 关闭] 暂时注释掉数据库连接
#         # print(f"Connecting to TuGraph ({eval_cfg['db_uri']})...")
#         # try:
#         #     db_driver = TuGraphAdapter(eval_cfg["db_uri"], eval_cfg["db_user"], eval_cfg["db_pass"])
#         #     db_driver.connect()
#         #     ea_metric = ExecutionAccuracy(db_driver)
#         # except Exception as e:
#         #     print(f"Database Connection Failed: {e}")
#         #     return

#         # [文本指标 开启]
#         bleu_metric = GoogleBleu()
#         ext_metric = ExternalMetric(eval_cfg["dbgpt_root"])
#         levels = cfg["prediction"]["level_fields"]

#         try:
#             for _, query_key in levels:
#                 print(f"\n{'='*40}")
#                 print(f"Evaluating Level: {query_key}")
#                 print(f"{'='*40}")

#                 preds = []
#                 golds = []

#                 # 数据准备
#                 for item in results:
#                     raw_p = item.get(query_key, "")
#                     raw_g = item.get("gql_query", "")
#                     p = clean_query(raw_p)
#                     g = clean_query(raw_g)
#                     preds.append(p)
#                     golds.append(g)
    
#                 # [EA 计算 关闭]
#                 # print("Calculating Execution Accuracy...")
#                 # ea = ea_metric.compute(preds, golds, db_ids=[])

#                 # 计算 Google BLEU
#                 print("Calculating Google BLEU...")
#                 bleu = bleu_metric.compute(preds, golds)

#                 #计算 Grammar & Similarity 
#                 print("Calculating Grammar & Similarity...")
#                 ext_res = ext_metric.compute(preds, golds)

#                 print(f"\nResults for {query_key}:")
#                 print(f"  - Samples    : {len(preds)}")
#                 # print(f"  - EA (Acc)   : {ea:.2%}")
#                 print(f"  - Grammar    : {ext_res['Grammar']:.2%}")
#                 print(f"  - Similarity : {ext_res['Similarity']:.4f}")
#                 print(f"  - BLEU       : {bleu if isinstance(bleu, str) else f'{bleu:.4f}'}")

#                 # 保存详细 JSON 评测结果
#                 output_dir = "evaluation_detail/execution_results"
#                 os.makedirs(output_dir, exist_ok=True)
#                 detailed_records = []

#                 for i, item in enumerate(results):
#                     record = {
#                         "instance_id": item.get("id", i),
#                         "gold_query": golds[i],
#                         "pred_query": item.get(query_key, ""),
#                         "cleaned_pred": preds[i],
#                         "metrics": {
#                             # 如果未来开启 EA，这里直接补进去就行
#                             # "accuracy": ea,
#                             "grammar": ext_res["Grammar"],
#                             "similarity": ext_res["Similarity"],
#                             "google_bleu": float(bleu) if not isinstance(bleu, str) else bleu
#                         },
#                         "gold_result": None,
#                         "pred_result": None
#                     }
#                     detailed_records.append(record)

#                 # 写入 JSON
#                 save_path = os.path.join(output_dir, f"{query_key}_results.json")
#                 with open(save_path, "w", encoding="utf-8") as f:
#                     json.dump(detailed_records, f, indent=2, ensure_ascii=False)
#                 print(f"Detailed results saved → {save_path}")
#         finally:
#             if db_driver:
#                 db_driver.close()
#                 print("\nDatabase connection closed.")
#         print("\nEvaluation Finished.")

# if __name__ == "__main__":
#     main()


import json
import argparse
import os
import sys
from impl.text2graph_system.qwen_zeroshot_system import QwenZeroshotSystem
from impl.db_driver.tugraph_driver import TuGraphAdapter
from impl.evaluation.metrics import ExecutionAccuracy, GoogleBleu, ExternalMetric
from impl.text2graph_system.utils import clean_query

class PipelineRunner:
    """
    负责串联 Text2Graph 系统的预测与评估流程的执行器
    """
    def __init__(self, config_path):
        self.config_path = config_path
        self.cfg = self._load_config(config_path)
        self.db_driver = None
        self.results = [] # 用于在预测和评估阶段之间共享数据

    def _load_config(self, path):
        print(f"Loading configuration from {path}...")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_db_driver(self):
        """初始化数据库连接"""
        # 目前 EA 被注释
        eval_cfg = self.cfg["evaluation"]
        # print(f"Connecting to TuGraph ({eval_cfg['db_uri']})...")
        # self.db_driver = TuGraphAdapter(eval_cfg["db_uri"], eval_cfg["db_user"], eval_cfg["db_pass"])
        # self.db_driver.connect()
        pass

    def run_prediction_phase(self):
        """执行预测阶段逻辑"""
        data_path = self.cfg["data"]["input_path"]
        output_path = self.cfg["data"]["output_path"]

        if self.cfg["pipeline"]["run_prediction"]:
            print(f"Loading raw data from {data_path}...")
            with open(data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            print("Initializing Text2Graph System...")
            system = QwenZeroshotSystem(self.cfg["prediction"])
            
            print("Running Prediction Batch...")
            self.results = system.predict_batch(raw_data)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"Predictions saved to {output_path}")
        else:
            print(f"Skipping prediction. Loading existing results from {output_path}...")
            if not os.path.exists(output_path):
                print(f"Error: Output file {output_path} not found. Cannot evaluate.")
                sys.exit(1)
                
            with open(output_path, "r", encoding="utf-8") as f:
                self.results = json.load(f)

    def run_evaluation_phase(self):
        """执行评估阶段逻辑"""
        if not self.cfg["pipeline"]["run_evaluation"]:
            return

        print("\nStarting Evaluation...")
        eval_cfg = self.cfg["evaluation"]

        # 1. 初始化指标
        # 如果开启 EA，需在此处使用 self.db_driver 初始化 ExecutionAccuracy
        # ea_metric = ExecutionAccuracy(self.db_driver)
        
        bleu_metric = GoogleBleu()
        ext_metric = ExternalMetric(eval_cfg["dbgpt_root"])
        
        levels = self.cfg["prediction"]["level_fields"]

        # 2. 遍历不同难度层级进行评估
        for _, query_key in levels:
            self._evaluate_single_level(query_key, bleu_metric, ext_metric)

    def _evaluate_single_level(self, query_key, bleu_metric, ext_metric):
        """对单个难度层级进行评估并保存详细结果"""
        print(f"\n{'='*40}")
        print(f"Evaluating Level: {query_key}")
        print(f"{'='*40}")
        
        preds = []
        golds = []
        
        # 数据清洗与准备
        for item in self.results:
            raw_p = item.get(query_key, "")
            raw_g = item.get("gql_query", "")
            p = clean_query(raw_p)
            g = clean_query(raw_g)
            preds.append(p)
            golds.append(g)
        
        # --- 指标计算 ---
        # print("Calculating Execution Accuracy...")
        # ea = ea_metric.compute(preds, golds, db_ids=[])
        
        print("Calculating Google BLEU...")
        bleu = bleu_metric.compute(preds, golds)
        
        print("Calculating Grammar & Similarity...")
        ext_res = ext_metric.compute(preds, golds)
        
        # --- 打印摘要 ---
        print(f"\nResults for {query_key}:")
        print(f"  - Samples    : {len(preds)}")
        # print(f"  - EA (Acc)   : {ea:.2%}")
        print(f"  - Grammar    : {ext_res['Grammar']:.2%}")
        print(f"  - Similarity : {ext_res['Similarity']:.4f}")
        print(f"  - BLEU       : {bleu if isinstance(bleu, str) else f'{bleu:.4f}'}")

        # --- 保存详细结果 ---
        self._save_detailed_results(query_key, preds, golds, bleu, ext_res)

    def _save_detailed_results(self, query_key, preds, golds, bleu, ext_res):
        """保存评估详情到文件"""
        output_dir = "evaluation_detail/execution_results"
        os.makedirs(output_dir, exist_ok=True)

        detailed_records = []
        for i, item in enumerate(self.results):
            record = {
                "instance_id": item.get("id", i),
                "gold_query": golds[i],
                "pred_query": item.get(query_key, ""),
                "cleaned_pred": preds[i],
                "metrics": {
                    # "accuracy": ea,
                    "grammar": ext_res["Grammar"],
                    "similarity": ext_res["Similarity"],
                    "google_bleu": float(bleu) if not isinstance(bleu, str) else bleu
                },
                "gold_result": None,
                "pred_result": None
            }
            detailed_records.append(record)

        save_path = os.path.join(output_dir, f"{query_key}_results.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(detailed_records, f, indent=2, ensure_ascii=False)
        print(f"Detailed results saved → {save_path}")

    def cleanup(self):
        """资源清理"""
        if self.db_driver:
            try:
                self.db_driver.close()
                print("\nDatabase connection closed.")
            except Exception as e:
                print(f"Error closing database: {e}")

    def run(self):
        """主入口方法"""
        try:
            # 1. 初始化资源 
            self._init_db_driver()

            # 2. 运行阶段
            self.run_prediction_phase()
            self.run_evaluation_phase()

        finally:
            self.cleanup()
            print("\nEvaluation Finished.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment/test_config.json", help="Path to config file")
    args = parser.parse_args()

    # 实例化并运行
    runner = PipelineRunner(args.config)
    runner.run()

if __name__ == "__main__":
    main()