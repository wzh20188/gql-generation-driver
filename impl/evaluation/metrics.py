import os
import sys
import shutil
import subprocess
import json
import re
import evaluate
from driver.evaluation import BaseMetric, DatabaseDriver

class ExecutionAccuracy(BaseMetric):
    def __init__(self, driver: DatabaseDriver):
        self.driver = driver

    def _normalize(self, value):
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
        def normalize_row(row):
            return tuple(self._normalize(v) for v in row.values())
        gold_set = {normalize_row(r) for r in res_gold}
        pred_set = {normalize_row(r) for r in res_predict}
        return gold_set == pred_set

    def compute(self, predictions: list, golds: list, **kwargs) -> float:
        db_ids = kwargs.get("db_ids", ["geography"] * len(predictions))
        correct = 0
        total = 0

        for pred, gold, db_id in zip(predictions, golds, db_ids):
            if not pred:
                total += 1
                continue 

            res_gold = self.driver.query(gold, db_name=db_id)
            if res_gold is None:
                total += 1
                continue

            res_pred = self.driver.query(pred, db_name=db_id)
            if res_pred is None:
                total += 1
                continue

            if self._compare_results(res_gold, res_pred):
                correct += 1
            total += 1

        return correct / total if total > 0 else 0.0
    
    def execute_single(self, pred, gold, db_id):
        """
        执行单条查询并返回 evaluation-friendly 结构
        """
        # 处理空预测
        if not pred:
            return False, None, None

        # 执行金标准查询
        try:
            res_gold = self.driver.query(gold, db_name=db_id)
        except Exception as e:
            res_gold = f"[GOLD ERROR] {str(e)}"

        # 执行模型预测查询
        try:
            res_pred = self.driver.query(pred, db_name=db_id)
        except Exception as e:
            res_pred = f"[PRED ERROR] {str(e)}"

        # 判断一致性
        try:
            is_correct = self._compare_results(res_gold, res_pred)
        except:
            is_correct = False

        return is_correct, res_gold, res_pred

class GoogleBleu(BaseMetric):
    def compute(self, predictions: list, golds: list, **kwargs):
        try:
            google_bleu = evaluate.load('google_bleu')
            safe_preds = [p.strip() if p else "" for p in predictions]
            safe_golds = [g.strip() if g else "" for g in golds]
            res = google_bleu.compute(predictions=safe_preds, references=safe_golds)
            return res['google_bleu']
        except Exception as e:
            print(f"Warning: BLEU failed: {e}")
            return 0.0

class ExternalMetric(BaseMetric):

    def __init__(self, dbgpt_root: str):
        self.dbgpt_root = dbgpt_root
        self.temp_dir = os.path.abspath("temp_eval_results_oop")

    def _parse_log_score(self, log_content, etype):

        try:
            # 尝试直接解析浮点数 
            val = float(log_content.strip())
            return val
        except ValueError:
            try:
                # 尝试解析 JSON 
                data = json.loads(log_content)
                if isinstance(data, list):
                    valid = [x['score'] for x in data if x.get('score', -1) >= 0]
                    return sum(valid) / len(valid) if valid else 0.0
                elif isinstance(data, dict):
                    return data.get('accuracy', 0.0) if etype == 'grammar' else data.get('score', 0.0)
            except:
                pass
        
        # 正则提取数字 (防止日志中有额外打印信息)
        try:
            matches = re.findall(r"[-+]?\d*\.\d+|\d+", log_content)
            if matches:
                return float(matches[-1])
        except:
            pass
        return 0.0

    def compute(self, predictions: list, golds: list, **kwargs) -> dict:
        dataset_type = kwargs.get('dataset_type', 'text2cypher')
        
        if not os.path.exists(self.dbgpt_root):
            print(f"ERROR: DBGPT root not found: {self.dbgpt_root}")
            return {'Grammar': 0.0, 'Similarity': 0.0}

        # 1. 准备目录
        os.makedirs(self.temp_dir, exist_ok=True)
        
        pred_file = os.path.join(self.temp_dir, 'predictions.txt')
        gold_file = os.path.join(self.temp_dir, 'gold.txt')

        # 确保去除换行符，保证一行一条
        clean_preds = [p.replace('\n', ' ').strip() if p else "" for p in predictions]
        clean_golds = [g.replace('\n', ' ').strip() if g else "" for g in golds]

        with open(pred_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(clean_preds))
        with open(gold_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(clean_golds))

        results = {}
        original_cwd = os.getcwd()

        try:
            # 2. 自动创建日志目录 
            log_dir = os.path.join(self.dbgpt_root, "dbgpt_hub_gql", "output", "logs")
            if not os.path.exists(log_dir):
                # print(f"DEBUG: Creating log directory at {log_dir}")
                os.makedirs(log_dir, exist_ok=True)

            # 3. 切换目录 
            os.chdir(self.dbgpt_root)
            impl = 'tugraph-db' if dataset_type == 'text2cypher' else 'iso-gql'

            for etype in ['grammar', 'similarity']:
                score = 0.0
                try:
                    cmd = [
                        sys.executable, 
                        'dbgpt_hub_gql/eval/evaluation.py',
                        '--input', pred_file,
                        '--gold', gold_file,
                        '--etype', etype,
                        '--impl', impl
                    ]
                    
                    # 4. 执行外部脚本           
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

                    # 5. 读取日志 
                    log_path = os.path.join('dbgpt_hub_gql', 'output', 'logs', 'eval.log')
                    if os.path.exists(log_path):
                        with open(log_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            score = self._parse_log_score(content, etype)
                    else:
                        print(f"WARNING: Log file missing for {etype}")

                except subprocess.CalledProcessError as e:
                    err_msg = e.stderr.decode('utf-8') if e.stderr else ""
                    print(f"Script Error ({etype}): {err_msg.strip()}")
                except Exception as e:
                    print(f"Error ({etype}): {e}")
                
                results[etype.capitalize()] = score

        finally:
            os.chdir(original_cwd)
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        return results