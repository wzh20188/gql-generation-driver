import os
import subprocess
import json
import shutil
from config import TEMP_DIR

def run_external_metrics(pred_list, gold_list, dbgpt_root, dataset_type='text2cypher'):
    """调用 dbgpt-hub-gql 的 evaluation.py 计算 Grammar 和 Similarity"""
    
    if not os.path.exists(dbgpt_root):
        print(f"Warning: DBGPT root '{dbgpt_root}' not found. Skipping external metrics.")
        return {'Grammar': 0.0, 'Similarity': 0.0}

    # 准备临时文件
    os.makedirs(TEMP_DIR, exist_ok=True)
    pred_file = os.path.abspath(os.path.join(TEMP_DIR, 'predictions.txt'))
    gold_file = os.path.abspath(os.path.join(TEMP_DIR, 'gold.txt'))

    with open(pred_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join([p if p else "" for p in pred_list]))
    with open(gold_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join([g if g else "" for g in gold_list]))

    results = {}
    current_dir = os.getcwd()
    
    # 切换目录执行外部脚本
    os.chdir(dbgpt_root)
    impl = 'tugraph-db' if dataset_type == 'text2cypher' else 'iso-gql'

    for etype in ['grammar', 'similarity']:
        score = 0.0
        try:
            cmd = [
                'python3', 'dbgpt_hub_gql/eval/evaluation.py',
                '--input', pred_file,
                '--gold', gold_file,
                '--etype', etype,
                '--impl', impl
            ]
            # 静默执行
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 读取日志结果
            log_file = 'dbgpt_hub_gql/output/logs/eval.log'
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    score = _parse_log_score(f.read().strip(), etype)
        except Exception:
            pass
        
        results[etype.capitalize()] = score

    # 还原目录并清理
    os.chdir(current_dir)
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    return results

def _parse_log_score(log_content, etype):
    """解析日志内容的辅助函数"""
    try:
        val = float(log_content)
        return val
    except ValueError:
        try:
            data = json.loads(log_content)
            if isinstance(data, list):
                valid = [x['score'] for x in data if x['score'] >= 0]
                return sum(valid) / len(valid) if valid else 0.0
            elif isinstance(data, dict):
                return data.get('accuracy', 0.0) if etype == 'grammar' else data.get('score', 0.0)
        except:
            pass
    return 0.0