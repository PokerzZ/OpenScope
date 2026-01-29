"""OpenDigger data collection utilities for OpenScope."""

import os
import subprocess
import pandas as pd
import json
import re
import stat
import logging
from typing import Optional, Sequence

# --- 1. 动态环境配置：支持子文件夹 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 指定子文件夹路径和二进制文件名
SUB_DIR_NAME = "opendigger-cli"
BINARY_NAME = "od-cli"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_METRICS = [
    "openrank",
    "activity",
    "issue_response_time",
    "change_request_response_time",
    "inactive_contributors",
]
SAFE_REPO_SEPARATOR = "_"

# 计算二进制文件的绝对路径
BIN_PATH = os.path.join(BASE_DIR, SUB_DIR_NAME, BINARY_NAME)
# 计算子文件夹的绝对路径，用于注入 PATH
BIN_DIR_PATH = os.path.join(BASE_DIR, SUB_DIR_NAME)

# 动态将“二进制文件所在的文件夹”加入当前进程的 PATH
os.environ["PATH"] = BIN_DIR_PATH + os.pathsep + os.environ["PATH"]

class OpenPuppeteerDataCore:
    """Core utilities for downloading and assembling OpenDigger metrics."""
    def __init__(self, binary_name: str = BINARY_NAME):
        self.binary_name = binary_name
        self.storage_dir = os.path.join(BASE_DIR, "data_warehouse")
        
        self._health_check()
        
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            logging.info("Created OpenDigger storage directory: %s", self.storage_dir)

    def _health_check(self):
        """检查子文件夹内的文件是否存在且可执行"""
        if not os.path.exists(BIN_PATH):
            raise FileNotFoundError(f"❌ 错误：在 {BIN_PATH} 找不到二进制文件！")
        
        # 自动修复执行权限
        st = os.stat(BIN_PATH)
        if not (st.st_mode & stat.S_IEXEC):
            logging.info(f"🔧 自动修复子文件夹内 {self.binary_name} 的执行权限...")
            os.chmod(BIN_PATH, st.st_mode | stat.S_IEXEC)

    def fetch_and_clean(self, repo: str, metric: str) -> Optional[pd.DataFrame]:
        """Download and normalize a single OpenDigger metric."""
        safe_repo = repo.replace("/", SAFE_REPO_SEPARATOR)
        file_path = os.path.join(self.storage_dir, f"{safe_repo}_{metric}.json")
        
        # 因为我们已经把子文件夹加入了 PATH，所以这里直接写名字即可
        cmd = [self.binary_name, "download", repo, metric, "-o", file_path]
        
        logging.info(
            "Downloading OpenDigger metric '%s' for %s -> %s",
            metric,
            repo,
            file_path,
        )
        try:
            # check=True 会在命令失败时抛出异常
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            with open(file_path, 'r') as f:
                raw = json.load(f)
            
            monthly = {k: v for k, v in raw.items() if re.match(r'^\d{4}-\d{2}$', k)}
            df = pd.DataFrame(list(monthly.items()), columns=['month', metric])
            df['month'] = pd.to_datetime(df['month'])
            return df
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ {repo} {metric} 抓取失败！命令行输出: {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            logging.error(
                f"❌ {repo} {metric} 抓取超时（{DEFAULT_TIMEOUT_SECONDS}s）。"
            )
            return None

    def build_aligned_dataset(
        self, repo: str, metrics: Optional[Sequence[str]] = None
    ) -> Optional[pd.DataFrame]:
        """Merge OpenDigger metrics into a single aligned dataset."""
        if metrics is None:
            # 默认指标集，包含核心活跃度、响应速度和贡献者流失情况
            metrics = DEFAULT_METRICS
        
        dfs = []
        for metric in metrics:
            df = self.fetch_and_clean(repo, metric)
            if df is not None:
                dfs.append(df)
        
        if not dfs:
            return None
            
        # 按 'month' 列合并所有数据框
        final_df = dfs[0]
        for df in dfs[1:]:
            final_df = pd.merge(final_df, df, on='month', how='outer')
            
        final_df = final_df.sort_values('month')
        pd.set_option('future.no_silent_downcasting', True)
        final_df = final_df.infer_objects(copy=False).fillna(0)
        
        # --- 特征工程 ---
        if 'openrank' in final_df.columns:
            final_df['rank_velocity'] = final_df['openrank'].diff().fillna(0)
            
        # --- 标签生成 (流失风险) ---
        # 规则 1: 活跃度骤降 (Activity Churn Risk)
        # 定义: 当月活跃度低于过去 3 个月平均值的 50%
        if 'activity' in final_df.columns:
            final_df['activity_ma3'] = final_df['activity'].rolling(window=3).mean().fillna(0)
            final_df['churn_risk_activity'] = final_df.apply(
                lambda row: 1 if row['activity_ma3'] > 0 and row['activity'] < 0.5 * row['activity_ma3'] else 0, 
                axis=1
            )

        # 规则 2: 贡献者流失 (Contributor Churn Signal)
        # 定义: 非活跃贡献者数量显著增加 (例如超过上个月的 20%)
        if 'inactive_contributors' in final_df.columns:
             final_df['inactive_diff'] = final_df['inactive_contributors'].diff().fillna(0)
             final_df['churn_risk_contributor'] = final_df.apply(
                 lambda row: 1 if row['inactive_diff'] > 5 else 0, # 阈值可调
                 axis=1
             )

        return final_df

if __name__ == "__main__":
    core = OpenPuppeteerDataCore()
    data = core.build_aligned_dataset("X-lab2017/open-digger")
    
    if data is not None:
        print("\n✅ [OpenPuppeteer-Rank] 数据集成成功！")
        print(data.tail(5))
