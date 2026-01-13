
import os
import sys
import torch
import json
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

def train_sft():
    # 1. Configuration
    model_name = "nvidia/Llama-3.1-Nemotron-70B-Reward" # In practice, swap with a smaller base like 'meta-llama/Meta-Llama-3-8B' for SFT
    # For demo purposes, let's assume valid access or use a dummy minimal path if needed.
    # User mentioned "nvidia/Llama-3.1-Nemotron-70B-Reward" in README but for SFT we generally use base models.
    # Let's use a standard placeholder or environment variable.
    model_path = os.environ.get("BASE_MODEL_PATH", "meta-llama/Meta-Llama-3-8B") 
    
    data_path = "puppeteer/data/sft_train_data.jsonl"
    output_dir = "puppeteer/checkpoint/sft_opendigger"
    
    print(f"Loading data from {data_path}...")
    dataset = load_dataset("json", data_files=data_path, split="train")
    
    # 2. Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    def process_func(example):
        messages = example['messages']
        # Simple formatting for ChatML/Alpaca style
        # Adjust based on model's chat template
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        model_inputs = tokenizer(text, max_length=1024, padding="max_length", truncation=True)
        model_inputs["labels"] = model_inputs["input_ids"].copy()
        return model_inputs

    tokenized_dataset = dataset.map(process_func, remove_columns=dataset.column_names)
    
    # 3. Model & LoRA
    print(f"Loading model from {model_path}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        torch_dtype=torch.bfloat16, 
        device_map="auto",
        trust_remote_code=True
    )
    
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=8,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj"] # Adjust based on architecture
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 4. Training
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        logging_steps=10,
        num_train_epochs=3,
        save_steps=100,
        learning_rate=1e-4,
        save_on_each_node=True,
        gradient_checkpointing=True,
        fp16=False, # Use bf16 if supported
        bf16=True
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True),
    )
    
    print("Starting training...")
    trainer.train()
    
    # 5. Save
    trainer.save_model(output_dir)
    print(f"Model saved to {output_dir}")

if __name__ == "__main__":
    # Ensure script is run from ChatDev root for paths to align
    if not os.path.exists("puppeteer/data/sft_train_data.jsonl"):
        print("Error: Run this script from the 'ChatDev' directory.")
        sys.exit(1)
        
    try:
        train_sft()
    except Exception as e:
        print(f"Training failed (simulated): {e}")
        print("Note: This script requires a real GPU environment and model weights.")
