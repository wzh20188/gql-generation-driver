# Text2Graph Evaluation Driver

This is a modular, Object-Oriented Programming experimental framework for **Text-to-Graph Query Generation (Text2Cypher/GQL)**. The system is designed to handle the entire pipeline from transforming natural language questions into graph queries, to executing and evaluating the results using multiple metrics. 

This project supports integrating **Qwen** and other Large Language Models (LLMs) for prediction, connects to **TuGraph** for Execution Accuracy verification, and utilizes external tools for comprehensive metric analysis.

## Key Features

**Full Pipeline Control**: Supports flexible toggling between the **Prediction Phase** (LLM query generation) and the **Evaluation Phase** (metrics calculation). 

**LLM Integration**: Built-in interface compatible with the OpenAI SDK format (default configuration targets AliCloud DashScope/Qwen). 

**Database Adaptability**: Connects to **TuGraph** using the Bolt protocol (compatible with the Neo4j Python Driver). 

**Multi-Dimensional Evaluation**:    

- **Execution Accuracy (EA)**: Compares query results returned by the database.    
- **Google BLEU**: Text-level N-gram similarity.    
- **External Metrics**: Integration with external tools to calculate **Grammar Correctness** and **Structural Similarity**. 

**Clean OOP Architecture**: The use of abstract base classes (Drivers) makes it easy to extend the system with new models or database adapters.

## Project Structure

```
\gql-generation-driver
├─ driver/                  # Abstract Interface Definitions
├─ example_data/            # Sample Input Data (JSON)
├─ experiment/              # Configuration Files
├─ impl/                    # Core Implementation Layer
│  ├─ db_driver/            # Database Adapters
│  ├─ evaluation/           # Evaluation Metrics Implementation
│  └─ text2graph_system/    # Generation System Implementation
├─ tools/                   
├─ output/                  # Prediction Results Output Directory
├─ evaluation_detail/       # Detailed Evaluation Report Directory
├─ requirements.txt         # Project dependency list
└─ run_pipeline.py          # Program Main Entry Point
```

## Environment Setup

### 1. Install Dependencies

Ensure your Python version is >= 3.8. Run the following command in the project root directory:

```
Bash
```

```bash
pip install -r requirements.txt
```

### 2. Set PYTHONPATH

To ensure Python can correctly resolve module imports within the project structure, set the `PYTHONPATH` before execution.

**PowerShell (Windows):**

```
PowerShell
```

```powershell
$env:PYTHONPATH="."
```

**CMD (Windows):**

```
DOS
```

```dos
set PYTHONPATH=.
```

**Bash/Zsh (Linux/macOS):**

```
Bash
```

```bash
export PYTHONPATH=.
```

## Configuration Guide

The main configuration file is located at `experiment/test_config.json`. Key fields are described below:

JSON

```json
{
  "pipeline": {
    "run_prediction": true,    // true: Calls LLM to generate queries; false: Loads existing results
    "run_evaluation": true     // true: Runs metrics calculation
  },
  "data": {
    "input_path": "example_data/dataset.json",
    "output_path": "output/prediction_result.json"
  },
  "prediction": {
    "api_key": "sk-xxxxxx",                // Your LLM API Key
    "base_url": "https://dashscope...",    // Model API Endpoint
    "model": "qwen-plus",                  // Model name
    "schema_path": "data/schema.json",     // Path to the Graph Database Schema file
    "max_workers": 5,                      // Concurrency level for API calls
    "level_fields": [                      // Defines the mapping for different query complexity levels
      ["initial_nl", "initial_query"],
      ["level_1", "level_1_query"]
    ]
  },
  "evaluation": {
    "db_uri": "bolt://localhost:7687",     // TuGraph/Neo4j Connection URI
    "db_user": "admin",
    "db_pass": "password",
    "dbgpt_root": "tools/dbgpt-hub-gql"    // Path to the external evaluation script root
  }
}
```

## Usage Guide

### Method A: Run with Default Configuration

```bash
python run_pipeline.py
```

### Method B: Specify a Custom Configuration

Use the `--config` argument to point to an alternative configuration file:

```bash
python run_pipeline.py --config experiment/debug_config.json
```

## Data Format Description

### Input Data Format

Each data entry includes information such as the database name, the original question, the layered reasoning questions, and optional external knowledge. The data format example is as follows:

```json
{
  "id": "Unique Identifier",
  "database": "Database Name",
  "initial_question": "Original Natural Language Question",
  "initial_gql": "Correct Cypher/GQL corresponding to the original natural language question",
  "level_1": "Level 1 (Coarse-grained Reasoning) Question",
  "level_2": "Level 2 (Structured Reasoning) Question",
  "level_3": "Level 3 (Sub-goal Planning) Question",
  "level_4": "Level 4 (Final Reasoning) Question",
  "external_knowledge": "Knowledge depending on sources outside the database (e.g., encyclopedia, common facts, can be empty)",
  "difficulty": "Question Difficulty (easy / medium / hard)",
  "source": "Data Source"
}
```

### Predicted Output Format

The model generates the corresponding predicted query statement for each data entry, located in the path defined by `data.output_path` (e.g., `output/`). The format of the output file is as follows:

```json
{
  "id": "Unique Identifier",
  "database": "Database Name",
  "initial_question": "Original Natural Language Question",
  "initial_gql": "Correct Cypher/GQL corresponding to the original natural language question",
  "level_1": "Level 1 (Coarse-grained Reasoning) Question",
  "level_2": "Level 2 (Structured Reasoning) Question",
  "level_3": "Level 3 (Sub-goal Planning) Question",
  "level_4": "Level 4 (Final Reasoning) Question",
  "external_knowledge": "Knowledge depending on sources outside the database (e.g., encyclopedia, common facts, can be empty)",
  "difficulty": "Question Difficulty (easy / medium / hard)",
  "source": "Data Source",
  "initial_query": "Model Predicted Query Statement",
  "level_1_query": "Model Predicted Query Statement",
  "level_2_query": "Model Predicted Query Statement",
  "level_3_query": "Model Predicted Query Statement",
  "level_4_query": "Model Predicted Query Statement"
}
```

### Evaluation Output Format: Including Evaluation Scores for Each Prediction Result

The evaluation will generate the following metrics for each layer's prediction:

- **EA (Execution Accuracy)**
- **Grammar (Grammatical Validity)**
- **Similarity (Structural Similarity)**
- **Google BLEU (Textual Similarity)**

And save them to: `evaluation_detail/execution_results/`

Each layer will correspond to a JSON file, for example: `level_1_results.json`

The file structure is as follows:

```json
[
  {
    "instance_id": "Unique Identifier",
    "gold_query": "Standard Answer Query Statement",
    "pred_query": "Model Predicted Query Statement",
	"cleaned_pred": "Cleaned Version (of the Predicted Query)",
     "metrics": {
    "accuracy": 1,
    "grammar": 1,
    "google_bleu": "0.633",
    "similarity": 0.9212
  	},
    "gold_result": [{...}]    // Execution result of the Gold Query
    "pred_result": [{...}]    // Execution result of the Model Prediction
  }
]
```
