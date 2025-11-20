import evaluate

def compute_google_bleu(preds, golds):
    """计算 Google BLEU 分数"""
    try:
        # 确保载入 logic 即使离线也能尝试（如果有缓存）
        google_bleu = evaluate.load('google_bleu')
        
        # 清洗空值
        safe_preds = [p.strip() if p else "" for p in preds]
        safe_golds = [g.strip() if g else "" for g in golds]
        
        res = google_bleu.compute(predictions=safe_preds, references=safe_golds)
        return res['google_bleu']
    except Exception as e:
        print(f"Warning: Google BLEU computation failed: {e}")
        return "N/A"