class MCBuilderBaseError(Exception):
    """项目基础异常"""
    pass


class NetworkFetchError(MCBuilderBaseError):
    """网络API拉取失败"""
    pass


class DownloadFailedError(MCBuilderBaseError):
    """文件下载失败、哈希校验不通过"""
    pass


class JavaNotFoundError(MCBuilderBaseError):
    """未找到满足版本要求的Java环境"""
    pass


class DeployPermissionError(MCBuilderBaseError):
    """目录权限不足"""
    pass


class KernelInitError(MCBuilderBaseError):
    """服务端初次初始化失败"""
    pass