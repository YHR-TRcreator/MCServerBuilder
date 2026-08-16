# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from common.constants import LOG_DIR

# 创建logger实例
logger = logging.getLogger("MCServerBuilder")
logger.setLevel(logging.INFO)

# 初始化日志函数，统一在main启动处调用，禁止全局自动执行
def init_logger():
    """初始化日志系统，程序启动时手动调用"""
    from common.file_utils import ensure_dir
    ensure_dir(LOG_DIR)

    log_path = Path(LOG_DIR) / "builder.log"

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    # 文件输出
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)