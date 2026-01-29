"""Batch OpenDigger dataset generation utilities."""

import os
from typing import Dict, List

import pandas as pd
from getdata import OpenPuppeteerDataCore
from tqdm import tqdm

# 定义数据集保存路径
# 路径: ChatDev/puppeteer/data/OpenDigger
DATASET_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "puppeteer", "data", "OpenDigger")
TRAIN_DIR = os.path.join(DATASET_ROOT, "train")
TEST_DIR = os.path.join(DATASET_ROOT, "test")
CONTEXT_SUFFIX = "_context.csv"

# 确保目录存在
os.makedirs(TRAIN_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

# 仓库列表 (Repo List)
# 包含不同类型的项目以保证数据多样性：成熟期、成长期、稳定期等
REPOS: Dict[str, List[str]] = {
    "train": [
        "X-lab2017/open-digger",
        "pytorch/pytorch",
        "tensorflow/tensorflow",
        "kubernetes/kubernetes",
        "microsoft/vscode",
        "apache/echarts",
        "ant-design/ant-design",
        "vuejs/core",
        "facebook/react",
        "twbs/bootstrap",
        "golang/go",
        "rust-lang/rust"
    ],
    "test": [
        "langchain-ai/langchain",
        "Significant-Gravitas/AutoGPT",
        "huggingface/transformers",
        "django/django",
        "flask/flask"
    ]
}

def safe_repo_name(repo: str) -> str:
    """Convert a repo slug into a filesystem-safe name."""
    return repo.replace("/", "_")

def batch_process() -> None:
    """Fetch OpenDigger metrics for train/test repo lists."""
    print(f"🚀 开始批量构建数据集...")
    print(f"📂 数据将保存至: {DATASET_ROOT}")
    
    try:
        core = OpenPuppeteerDataCore()
    except Exception as e:
        print(f"❌ 初始化 OpenPuppeteerDataCore 失败: {e}")
        return

    for split, repo_list in REPOS.items():
        save_dir = TRAIN_DIR if split == "train" else TEST_DIR
        saved_count = 0
        print(f"\nProcessing {split} set ({len(repo_list)} repos)...")
        
        for repo in tqdm(repo_list, desc=f"{split} repos"):
            try:
                # print(f"Fetching {repo}...")
                df = core.build_aligned_dataset(repo)
                
                if df is not None and not df.empty:
                    # 保存为 CSV
                    safe_name = safe_repo_name(repo)
                    file_path = os.path.join(save_dir, f"{safe_name}{CONTEXT_SUFFIX}")
                    df.to_csv(file_path, index=False)
                    saved_count += 1
                else:
                    print(f"⚠️ No data found for {repo}")
            except Exception as e:
                print(f"❌ Error processing {repo}: {e}")

        print(f"✅ Saved {saved_count} datasets for {split}")

    print("\n✨ 批量处理完成！")
    print(f"训练集路径: {TRAIN_DIR}")
    print(f"测试集路径: {TEST_DIR}")

if __name__ == "__main__":
    batch_process()
