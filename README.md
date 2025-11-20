# GQL-Generation-Driver

本项目是一个 **面向图数据库（TuGraph / Neo4j）的自动查询生成与评测系统**。通过自然语言输入，系统会：

1. **Stage 1**：生成对应的 Cypher/GQL 查询语句
2. **Stage 2**：对生成的查询进行完整的自动化评测，包括：
   - 查询执行正确率 Execution Accuracy（EA）
   - 查询语法有效性 Grammar Validity
   - 查询结构相似度 Structural Similarity
   - Google-BLEU 文本相似度评分

------

# 安装与运行说明

## 克隆本项目（务必包含子模块）

```bash
git clone --recursive https://github.com/wzh20188/gql-generation-driver.git
cd gql-generation-driver
```

如果忘记加入 `--recursive`，可执行：

```bash
git submodule update --init --recursive
```

------

# 安装依赖

```bash
pip install -r requirements.txt
```

# Stage 1：自然语言 → GQL/Cypher 查询生成

执行：

```bash
cd stage1_prediction
python predict.py
```

输入数据位于：

```
stage1_prediction/inputs/
```

输出预测结果：

```
stage1_prediction/outputs/predicted.json
```

------

# Stage 2：自动评测（EA / Grammar / Similarity / BLEU）

运行：

```bash
cd stage2_evaluation
python main.py --input ../stage1_prediction/outputs/predicted.json
```

配置文件：

```
stage2_evaluation/config.py
```

------

# 配置说明

在 `stage2_evaluation/config.py` 中可以设置：

```python
DB_URI = "bolt://localhost:7687"
DB_USER = "admin"
DB_PASSWORD = "73@TuGraph"

DEFAULT_DBGPT_ROOT = os.path.join(BASE_DIR, "dbgpt-hub-gql")

LEVEL_FIELDS = [
    ("initial_query", "initial_results.json"),
    ("level_1_query", "level_1_results.json"),
    ...
]
```

------

# 为什么使用 Git Submodule？

项目依赖外部评测框架：

**DB-GPT-Hub**
 https://github.com/eosphoros-ai/DB-GPT-Hub

------

# 数据格式说明

### 输入数据格式

每条数据包含数据库名称、原始问题、逐层推理问题、以及可选的外部知识等信息。
数据格式示例如下：

```json
{
  "id": "唯一标识",
  "database": "数据库名称",
  "initial_question": "原始自然语言问题",
  "initial_gql": "原始自然语言问题对应的正确Cypher/GQL",
  "level_1": "第一层（粗粒度推理）问题",
  "level_2": "第二层（结构化推理）问题",
  "level_3": "第三层（子目标规划）问题",
  "level_4": "第四层（最终推理）问题",
  "external_knowledge": "依赖数据库之外的知识（如百科、事实常识，可为空）",
  "evidence": "明确 schema linking 信息，如表字段、图数据库节点关系",
  "difficulty": "问题难度（easy / medium / hard）",
  "source": "数据来源"
}
```



###  预测输出格式

模型在 Stage 1 会对每一条数据生成对应的预测查询语句。
输出文件的格式如下：

```json
{
  "id": "唯一标识",
  "database": "数据库名称",
  "initial_question": "原始自然语言问题",
  "initial_gql": "原始自然语言问题对应的正确Cypher/GQL",
  "level_1": "第一层（粗粒度推理）问题",
  "level_2": "第二层（结构化推理）问题",
  "level_3": "第三层（子目标规划）问题",
  "level_4": "第四层（最终推理）问题",
  "external_knowledge": "依赖数据库之外的知识（如百科、事实常识，可为空）",
  "evidence": "明确 schema linking 信息，如表字段、图数据库节点关系",
  "difficulty": "问题难度（easy / medium / hard）",
  "source": "数据来源",
  "initial_query": "模型预测的查询语句",
  "level_1_query": "模型预测的查询语句",
  "level_2_query": "模型预测的查询语句",
  "level_3_query": "模型预测的查询语句",
  "level_4_query": "模型预测的查询语句"
}

```



### 测评输出格式：加入每一个预测结果对应的评测分数

Stage 2 评测会为每一层预测生成对应的：

- EA（Execution Accuracy）
- Grammar（语法有效性）
- Similarity（结构相似度）
- Google BLEU（文本相似度）

并保存至：

```
stage2_evaluation/execution_results/
```

每一层会对应一个 JSON 文件，例如：`level_1_results.json`

文件结构如下：

```json
[
  {
    "instance_id": "id",
    "gold_query": "标准答案查询语句",
    "pred_query": "模型预测的查询语句",
	"cleaned_pred": "清洗后的版本",
     "metrics": {
    "accuracy": 1,
    "grammar": 1,
    "google_bleu": "0.633",
    "similarity": 0.9212
  	},
    "gold_result": [{...}]    // Gold查询执行结果
    "pred_result": [{...}]    // 模型预测执行结果
  }
]

```
