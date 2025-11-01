# -*- coding: utf-8 -*-
"""
集中化配置：交易参数、风险参数、模型与路径等。
备注：请通过环境变量覆盖敏感项（API Key 等）。
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict

# =============== 路径相关（使用 pathlib） ===============
BASE_DIR: Path = Path(__file__).resolve().parents[1]
# 识别 Vercel 无状态/只读文件系统环境
IS_VERCEL: bool = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
# 可通过 APP_DATA_DIR 覆盖数据目录；在 Vercel 下默认使用 /tmp（可写但不持久）
_APP_DATA_DIR = os.getenv("APP_DATA_DIR")
if _APP_DATA_DIR:
    DATA_DIR: Path = Path(_APP_DATA_DIR)
    ARCHIVE_DIR: Path = DATA_DIR / "archives"
else:
    if IS_VERCEL:
        TMP_BASE = Path(os.getenv("TMPDIR", "/tmp")) / "alpha-okx-deepseek-qwen"
        DATA_DIR: Path = TMP_BASE / "data"
        ARCHIVE_DIR: Path = TMP_BASE / "archives"
    else:
        DATA_DIR: Path = BASE_DIR / "data"
        ARCHIVE_DIR: Path = BASE_DIR / "archives"
DB_PATH: Path = DATA_DIR / "history.db"

# 确保目录存在（在 Vercel 只会创建到 /tmp，属于临时目录，随请求生命周期清空）
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# =============== 日志配置（全局生效） ===============
# 控制台输出仅显示必要的信息；文件记录完整细节
LOG_DIR: Path = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE: Path = LOG_DIR / "app.log"

def _configure_logging_once() -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_crypto_ai_trader_logging_configured", False):
        return

    # 根日志级别用 DEBUG，方便文件记录；具体输出由各 handler 控制
    root_logger.setLevel(logging.DEBUG)

    # 控制台：默认 INFO（仅必要信息）
    console_level_name = os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper()
    try:
        console_level = getattr(logging, console_level_name)
    except AttributeError:
        console_level = logging.INFO
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%H:%M:%S"))

    # 文件：默认 DEBUG（完整细节），滚动保存
    file_level_name = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()
    try:
        file_level = getattr(logging, file_level_name)
    except AttributeError:
        file_level = logging.DEBUG
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    # 清理可能的默认 handler，避免重复输出（仅移除未绑定到我们设置的 handler 类型）
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 降低第三方日志噪音（可按需调整）
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.INFO)

    # 标记已配置，避免重复
    setattr(root_logger, "_crypto_ai_trader_logging_configured", True)

_configure_logging_once()

# =============== 风险与仓位参数 ===============
HOLD_TOLERANCE: float = 0.5  # HOLD 信号允许的价差百分比

# 根据信心等级分配可用保证金的百分比
CONFIDENCE_RATIOS: Dict[str, float] = {
    "HIGH": 0.30,
    "MEDIUM": 0.20,
    "LOW": 0.05,
}

# 保证金管理（风险管理配置，非交易所限制）
MAX_TOTAL_MARGIN_RATIO: float = 0.85  # 总保证金不超过权益的比例
MARGIN_SAFETY_BUFFER: float = 0.90  # 安全缓冲比例

# =============== 模型配置 ===============
MODEL_METADATA: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "display": "DeepSeek 策略",
        "provider": "deepseek",
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    },
    "qwen": {
        "display": "Qwen 策略",
        "provider": "qwen",
        "model": os.getenv("QWEN_MODEL", "qwen-max"),
        "base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    },
}

ENABLED_MODELS = [m.strip().lower() for m in os.getenv("ENABLED_MODELS", "deepseek,qwen").split(",") if m.strip()]

# =============== 交易对配置 ===============
TRADE_CONFIGS: Dict[str, Dict] = {
    "BTC/USDT:USDT": {
        "display": "BTC-USDT",
        "amount": 0.0001,
        "leverage": 2,
        "leverage_min": 1,
        "leverage_max": 3,
        "leverage_default": 2,
        "leverage_step": 1,
        "timeframe": "5m",
        "test_mode": False,
        "data_points": 96,
        "analysis_periods": {"short_term": 20, "medium_term": 50, "long_term": 96},
    },
    "ETH/USDT:USDT": {
        "display": "ETH-USDT",
        "amount": 0.001,
        "leverage": 2,
        "leverage_min": 1,
        "leverage_max": 3,
        "leverage_default": 2,
        "leverage_step": 1,
        "timeframe": "5m",
        "test_mode": False,
        "enable_add_position": False,  # 同方向信号不加仓
        "data_points": 96,
        "analysis_periods": {"short_term": 20, "medium_term": 50, "long_term": 96},
    },
}

# 单交易对兼容（保留旧接口需求）
DEFAULT_TRADE_SYMBOL: str = "ETH/USDT:USDT"
