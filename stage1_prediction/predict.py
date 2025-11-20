import json
from utils.model_api import predict_all_levels

if __name__ == "__main__":

    input_path = r"inputs/geography_5_csv_files_08051006_corpus_seeds.json"
    output_path = r"outputs/predicted.json"

    # 加载配置
    cfg = json.load(open("configs/qwen.json", "r", encoding="utf-8"))
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]
    model = cfg["model"]

    # 加载数据
    data = json.load(open(input_path, "r", encoding="utf-8"))

    # 执行预测
    results = predict_all_levels(
        data,
        api_key,
        base_url,
        model=model,
        max_workers=5
    )

    json.dump(results, open(output_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("\n 预测完成！结果保存到：", output_path)
