import re

def extract_cypher(pred: str) -> str:
    pattern = r'```cypher(.*?)```'
    match = re.search(pattern, pred, re.DOTALL)
    if match:
        return match.group(1).replace('\n', ' ').strip()
    return pred.replace('\n', ' ').strip()

def extract_gql(pred: str) -> str:
    pattern = r'```gql(.*?)```'
    match = re.search(pattern, pred, re.DOTALL)
    if match:
        return match.group(1).replace('\n', ' ').strip()
    return pred.replace('\n', ' ').strip()

def clean_query(pred: str) -> str:
    """综合清洗逻辑：去除 think 标签，提取代码块，去除换行"""
    if not isinstance(pred, str):
        return ""
    
    pred = pred.replace('<think>\n\n</think>\n\n', '')
    pred = re.sub(r'<think>.*?</think>', '', pred, flags=re.DOTALL)
    
    if '```cypher' in pred:
        return extract_cypher(pred)
    elif '```gql' in pred:
        return extract_gql(pred)
    else:
        return pred.replace('\n', ' ').strip()