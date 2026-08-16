from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def publish(self, event_name: str, *args, **kwargs):
        if event_name not in self._subscribers:
            return
        for cb in self._subscribers[event_name]:
            cb(*args, **kwargs)


event_bus = EventBus()

# 预定义事件常量
EVENT_JAVA_SCAN_FINISH = "java_scan_finish"
EVENT_JAVA_DOWNLOAD_PROGRESS = "java_download_progress"
EVENT_KERNEL_LIST_READY = "kernel_list_ready"
EVENT_KERNEL_DOWNLOAD_PROGRESS = "kernel_download_progress"
EVENT_DEPLOY_SUCCESS = "deploy_success"
EVENT_DEPLOY_FAILED = "deploy_failed"
EVENT_LOG_INFO = "log_info"