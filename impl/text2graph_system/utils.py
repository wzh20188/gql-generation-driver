import json
import re

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

def clean_query(pred: str) -> str:
    """原样保留 cleaners.py 的逻辑"""
    if not isinstance(pred, str):
        return ""
    
    # 去除 think 标签
    pred = pred.replace('<think>\n\n</think>\n\n', '')
    pred = re.sub(r'<think>.*?</think>', '', pred, flags=re.DOTALL)
    
    # 提取代码块
    match_cypher = re.search(r'```cypher(.*?)```', pred, re.DOTALL)
    if match_cypher:
        return match_cypher.group(1).replace('\n', ' ').strip()
        
    match_gql = re.search(r'```gql(.*?)```', pred, re.DOTALL)
    if match_gql:
        return match_gql.group(1).replace('\n', ' ').strip()
        
    return pred.replace('\n', ' ').strip()