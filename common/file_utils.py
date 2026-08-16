import os
import re
import time
import shutil
import zipfile
import tarfile
from pathlib import Path
from common.logger import logger
from common.exceptions import DeployPermissionError


def ensure_dir(save_path: str):
    """
    安全创建目录
    :param save_path: 目录绝对路径
    """
    path = Path(save_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"目录【{save_path}】权限不足！\n"
            "请勿放在C:\\Program Files、系统盘根目录；\n"
            "请将整个程序解压至桌面、D盘文件夹再运行！"
        )
    except Exception as e:
        raise e


def extract_archive(file_path: str, target_dir: str):
    """自动识别zip/tar压缩包并解压"""
    ensure_dir(target_dir)
    if file_path.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as zf:
            zf.extractall(target_dir)
    elif file_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(file_path, "r:gz") as tf:
            tf.extractall(target_dir)
    else:
        raise NotImplementedError("仅支持 zip / tar.gz 解压")
    logger.info(f"解压完成: {file_path} -> {target_dir}")


def copy_file(src: str, dst: str):
    shutil.copy2(src, dst)


def wait_eula_generated(folder_path: str, timeout=20):
    """轮询等待eula.txt生成，最长等待20秒"""
    eula_path = os.path.join(folder_path, "eula.txt")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(eula_path):
            return True
        time.sleep(0.8)
    logger.error("等待超时，eula.txt未能生成！")
    return False


def patch_eula_file(folder_path: str):
    """正则修改eula，不依赖固定行数，兼容所有版本"""
    eula_path = os.path.join(folder_path, "eula.txt")
    if not os.path.exists(eula_path):
        logger.error("找不到eula.txt，无法修改协议！")
        return False

    with open(eula_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"eula\s*=\s*(true|false)", re.IGNORECASE)
    new_content = pattern.sub("eula=true", content)

    with open(eula_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    logger.info("✅ EULA协议自动同意完成：eula=true")
    return True

