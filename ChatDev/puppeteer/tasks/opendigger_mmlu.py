import os
import string
import json
import pandas as pd
from tqdm import tqdm
from tasks.base.base_task import BaseTask

def load_dataset(mode, data_limit=None):
    # mode is ignored here as we only have 'test.parquet' for now, or we can map mode to filename
    path = os.path.join("data", "OpenDiggerMMLU", "test.parquet")
    data = pd.read_parquet(path)
    return data[:data_limit] if data_limit else data

def format_question(task):
    # Options are already a list in the parquet file
    options = [f"{letter}: {op}" for letter, op in zip(string.ascii_uppercase, task["options"])]
    
    # The question text is already fully formed in the dataset generation step
    question = task["question"] + "\n\nOptions:\n" + "\n".join(options)
    
    return {
        "type": "OpenDiggerMMLU",
        "Question": question,
        "Answer": task["answer"],
        "id": task["question_id"]
    }

def run(runner, evaluator, results_dir, mode, data_limit=None):
    dataset = load_dataset(mode, data_limit)
    result_path = os.path.join(results_dir, f"OpenDiggerMMLU_{mode}.jsonl")
    acc = 0

    with open(result_path, "w", encoding="utf-8") as fd:
        for _, row in tqdm(dataset.iterrows(), total=len(dataset)):
            task = format_question(row)
            final_ans = runner.run_reasoning(task)
            
            # Use the existing check_mmlu evaluator
            flag = evaluator.check_mmlu(final_ans, task["Answer"])
            if flag: 
                acc += 1
            record = {
                "id": task["id"],
                "pred": final_ans,
                "correct": flag,
                "ground_truth": task["Answer"]
            }
            fd.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n{'='*60}")
    print(f"✓ Analysis Complete!")
    print(f"  Accuracy: {acc}/{len(dataset)} = {acc/len(dataset):.2%}")
    print(f"  Results saved to: {result_path}")
    print(f"{'='*60}\n")
    
    return acc, len(dataset)
