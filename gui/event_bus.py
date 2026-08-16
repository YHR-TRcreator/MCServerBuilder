# -*- coding: utf-8 -*-
from PySide6.QtCore import QObject, Signal


class GuiEventBus(QObject):
    """全局UI事件总线，页面之间发消息，不互相import"""
    log_out = Signal(str)          # 输出一行日志
    switch_cli_request = Signal()  # 请求切到CLI模式


event_bus = GuiEventBus()
