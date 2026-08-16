# -*- coding: utf-8 -*-
"""
forge_version_api.py
完整修复版：兼容bmclapi / bmclapi2两种返回格式
修复list对象无get()、函数未定义问题
【路径重大修复：全部使用绝对路径，消除 ./runtime 相对路径导致WinError5拒绝访问】
"""
import json
import os
import aiohttp
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

# --------------------------【路径修复区，全部使用绝对路径】--------------------------
# 当前文件：core/forge_version_api.py → parent=core, parent.parent=项目根目录
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parent.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
CACHE_DIR = RUNTIME_DIR / "cache"

# 配置：同目录下的节点配置文件
API_ENDPOINT_CONFIG_PATH = str(THIS_FILE.parent / "forge_api_endpoints.json")
# 缓存、黑名单 全部指向 runtime/cache 绝对路径
FULL_CACHE_FILE = str(CACHE_DIR / "forge_cache.json")
NODE_BLACKLIST_PATH = str(CACHE_DIR / "node_blacklist.json")

PAGE_RETRY_MAX = 2
SLEEP_BETWEEN_REQUEST = 0.3
LIMIT_PER_PAGE = 500
DEBUG = True

REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://docs.bangbang93.com/"
}


def ensure_cache_dir():
    """确保cache文件夹完整存在，替换原来os.makedirs，使用pathlib更稳定"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_external_endpoints() -> List[str]:
    if not os.path.exists(API_ENDPOINT_CONFIG_PATH):
        print(f"⚠️ 未找到自定义镜像节点配置文件: {API_ENDPOINT_CONFIG_PATH}")
        return []
    try:
        with open(API_ENDPOINT_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg_data = json.load(f)
        endpoint_list = cfg_data
        if isinstance(endpoint_list, list) and len(endpoint_list) > 0:
            print(f"✅成功加载自定义镜像节点，共{len(endpoint_list)}条")
            return endpoint_list
        else:
            print("⚠️ 配置文件节点列表为空")
            return []
    except Exception as e:
        print(f"❌读取节点配置失败:{str(e)}")
        return []


def get_filtered_endpoints(raw_endpoints: List[str]) -> List[str]:
    ensure_cache_dir()
    blacklist = []
    if os.path.exists(NODE_BLACKLIST_PATH):
        try:
            with open(NODE_BLACKLIST_PATH, "r", encoding="utf-8") as f:
                blacklist = json.load(f)
        except Exception:
            pass
    available_nodes = [url for url in raw_endpoints if url not in blacklist]
    return available_nodes


def group_forge_by_mcversion(raw_build_list: List[dict]) -> Dict[str, List[dict]]:
    """将全部forge构建，按照mcversion分组"""
    group = {}
    for build in raw_build_list:
        mc_ver = build.get("mcversion")
        if not mc_ver:
            continue
        if mc_ver not in group:
            group[mc_ver] = []
        group[mc_ver].append(build)
    return group


async def fetch_page(base_url: str, offset: int, session: aiohttp.ClientSession) -> List[dict]:
    """拉取单页数据【修复兼容两种返回结构】"""
    api_url = f"{base_url}/forge/list/{offset}/{LIMIT_PER_PAGE}"
    for retry in range(PAGE_RETRY_MAX + 1):
        try:
            if DEBUG:
                print(f"📄请求分页 offset={offset} url={api_url}")
            resp = await session.get(api_url, headers=REQ_HEADERS, timeout=aiohttp.ClientTimeout(total=30))
            if resp.status == 200:
                text_data = await resp.text(encoding="utf-8")
                json_data = json.loads(text_data)
                # 兼容两种返回格式
                if isinstance(json_data, dict):
                    build_list = json_data.get("list", [])
                elif isinstance(json_data, list):
                    build_list = json_data
                else:
                    build_list = []
                return build_list
            else:
                print(f"⚠️ offset={offset} HTTP状态码:{resp.status}")
        except Exception as err:
            print(f"⚠️ offset={offset} 请求异常，重试{retry+1} | {str(err)}")
        await asyncio.sleep(0.4)
    print(f"❌ offset={offset} 多次请求失败")
    return []


async def fetch_all_forge_data(base_url: str) -> Optional[Dict]:
    """【完整主拉取函数】循环分页拉取全部forge数据"""
    timeout_setting = aiohttp.ClientTimeout(total=300, connect=20, sock_read=90)
    connector = aiohttp.TCPConnector(force_close=True, family=2, limit=30)
    all_builds = []
    offset = 0

    async with aiohttp.ClientSession(timeout=timeout_setting, connector=connector) as session:
        while True:
            page_data = await fetch_page(base_url, offset, session)
            if not page_data:
                print("✅分页拉取完毕，无更多数据")
                break
            all_builds.extend(page_data)
            print(f"▶当前累计获取构建数量: {len(all_builds)}")
            offset += LIMIT_PER_PAGE
            await asyncio.sleep(SLEEP_BETWEEN_REQUEST)

    if len(all_builds) == 0:
        return None

    grouped_data = group_forge_by_mcversion(all_builds)
    output_versions = []
    for mcver, builds in grouped_data.items():
        output_versions.append({
            "mcversion": mcver,
            "builds": builds
        })
    return {"versions": output_versions}


async def refresh_forge_cache() -> bool:
    raw_endpoints = load_external_endpoints()
    endpoints = get_filtered_endpoints(raw_endpoints)
    if not endpoints:
        print("⚠️ 所有节点处于黑名单冷却中，请稍后重试！")
        return False

    ensure_cache_dir()

    for index, base_domain in enumerate(endpoints):
        node_num = index + 1
        print(f"\n=====正在尝试【节点{node_num}】：{base_domain}=====")
        try:
            cache_data = await fetch_all_forge_data(base_domain)
            if cache_data and len(cache_data.get("versions", [])) > 0:
                print(f"✅节点{node_num} 全部数据拉取完成，写入缓存！")
                with open(FULL_CACHE_FILE, "w", encoding="utf-8") as fw:
                    json.dump(cache_data, fw, ensure_ascii=False, indent=2)
                return True
        except Exception as err:
            import traceback
            traceback.print_exc()
            print(f"❌节点[{node_num}] 拉取全过程失败: {str(err)}")

    print("\n❌所有API节点全部尝试完毕，无法获取数据！")
    return False


# 测试入口
if __name__ == "__main__":
    asyncio.run(refresh_forge_cache())