# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QDialog,
                               QLabel, QLineEdit, QPushButton, QFormLayout, QListWidgetItem, QTextEdit)
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import CardWidget, PushButton, ListWidget, BodyLabel, MessageBox, InfoBadge
from qasync import asyncSlot


class ConfigEditDialog(QDialog):
    """实例配置编辑独立对话框窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("实例配置编辑")
        self.resize(520, 420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.edit_server_name = QLineEdit()
        self.edit_java_path = QLineEdit()
        self.edit_min_mem = QLineEdit()
        self.edit_max_mem = QLineEdit()
        self.edit_port = QLineEdit()
        self.edit_jvm_args = QLineEdit()

        form.addRow("服务名称：", self.edit_server_name)
        form.addRow("Java路径：", self.edit_java_path)
        form.addRow("最小内存GB：", self.edit_min_mem)
        form.addRow("最大内存GB：", self.edit_max_mem)
        form.addRow("服务端口：", self.edit_port)
        form.addRow("JVM附加参数：", self.edit_jvm_args)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("保存配置")
        self.btn_cancel = QPushButton("取消")
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def load_config(self, cfg: Dict):
        """把配置字典填入对话框控件"""
        self.edit_server_name.setText(cfg.get("server_name", ""))
        self.edit_java_path.setText(cfg.get("java_path", ""))
        self.edit_min_mem.setText(str(cfg.get("min_memory_gb", 2)))
        self.edit_max_mem.setText(str(cfg.get("max_memory_gb", 4)))
        self.edit_port.setText(str(cfg.get("server_port", 25565)))
        self.edit_jvm_args.setText(cfg.get("jvm_args", ""))

    def get_config_dict(self) -> Dict:
        """读取对话框控件输出配置字典"""
        return {
            "server_name": self.edit_server_name.text().strip(),
            "java_path": self.edit_java_path.text().strip(),
            "min_memory_gb": int(self.edit_min_mem.text().strip()),
            "max_memory_gb": int(self.edit_max_mem.text().strip()),
            "server_port": int(self.edit_port.text().strip()),
            "jvm_args": self.edit_jvm_args.text().strip()
        }


class InstancePage(QWidget):
    log_signal = Signal(str)
    status_text_signal = Signal(str)   # 接收底层状态字符串: running / stopped / crashed

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("InstancePage")
        self.service = service   # 使用主窗口传进来的全局service，不要自己new

        self._instance_map: Dict[str, str] = {}
        self._watcher = None
        self.setup_ui()

        # 绑定信号
        self.log_signal.connect(self._append_log)
        self.status_text_signal.connect(self._update_run_status)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24,24,24,24)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.addWidget(BodyLabel("已部署服务实例管理"))
        self.status_badge = InfoBadge("【未运行】")
        top_row.addStretch()
        top_row.addWidget(self.status_badge)
        layout.addLayout(top_row)

        list_card = CardWidget()
        card_layout = QVBoxLayout(list_card)
        card_layout.setContentsMargins(20,20,20,20)
        card_layout.setSpacing(12)

        self.instance_list = ListWidget()
        card_layout.addWidget(self.instance_list, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_refresh_list = PushButton("刷新实例列表")
        self.btn_start_server = PushButton("启动选中实例")
        self.btn_stop_server = PushButton("停止选中实例")
        self.btn_open_config = PushButton("打开配置编辑窗口")
        btn_row.addWidget(self.btn_refresh_list)
        btn_row.addWidget(self.btn_start_server)
        btn_row.addWidget(self.btn_stop_server)
        btn_row.addWidget(self.btn_open_config)
        card_layout.addLayout(btn_row)

        layout.addWidget(list_card, stretch=1)

        # ============控制台区域============
        console_card = CardWidget()
        console_layout = QVBoxLayout(console_card)
        console_layout.setContentsMargins(20,20,20,20)
        console_layout.setSpacing(10)

        console_layout.addWidget(BodyLabel("服务控制台"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        console_layout.addWidget(self.log_text, stretch=1)

        cmd_row = QHBoxLayout()
        self.input_cmd = QLineEdit()
        self.input_cmd.setPlaceholderText("输入服务端命令，例如 stop / say hello")
        self.btn_send_cmd = PushButton("发送命令")
        cmd_row.addWidget(self.input_cmd, stretch=1)
        cmd_row.addWidget(self.btn_send_cmd)
        console_layout.addLayout(cmd_row)

        layout.addWidget(console_card, stretch=1)

        # 按钮信号绑定
        self.btn_refresh_list.clicked.connect(self._refresh_list)
        self.btn_start_server.clicked.connect(self._start_server)
        self.btn_stop_server.clicked.connect(self._stop_server)
        self.btn_open_config.clicked.connect(self._open_config_window)
        self.btn_send_cmd.clicked.connect(self._send_command)

    def _refresh_list(self):
        """读取全部已部署实例，填充ListWidget"""
        self.instance_list.clear()
        self._instance_map.clear()
        try:
            server_dict = self.service.get_all_servers()
            for name, path in server_dict.items():
                item = QListWidgetItem(f"{name} | {path}")
                self.instance_list.addItem(item)
                self._instance_map[name] = path
        except Exception as e:
            MessageBox("读取实例失败", f"读取服务列表异常：{str(e)}", self).exec()

    def _get_selected_instance_path(self) -> Optional[str]:
        """获取当前选中实例的完整路径，没有选中返回None"""
        selected_item = self.instance_list.currentItem()
        if not selected_item:
            MessageBox("提示", "请先选中一个服务实例", self).exec()
            return None
        text = selected_item.text()
        name_part = text.split(" | ")[0]
        return self._instance_map.get(name_part)

    @asyncSlot()
    async def _open_config_window(self):
        """打开配置编辑弹窗"""
        server_path = self._get_selected_instance_path()
        if server_path is None:
            return

        try:
            cfg = self.service.load_config(server_path)
            if cfg is None:
                hw_info = self.service.get_hardware_info()
                rec_mb = self.service.suggest_memory(hw_info["total_memory_gb"])
                rec_gb = round(rec_mb / 1024)
                server_name = Path(server_path).name
                cfg = self.service.create_default_config(server_name, server_path, "java", rec_gb)
                self.service.save_config(server_path, cfg)

            dlg = ConfigEditDialog(self)
            dlg.load_config(cfg)
            ret = dlg.exec()
            if ret:
                new_cfg = dlg.get_config_dict()

                if new_cfg["min_memory_gb"] <= 0 or new_cfg["max_memory_gb"] <=0:
                    raise ValueError("内存必须大于0")
                if not (1 <= new_cfg["server_port"] <= 65535):
                    raise ValueError("端口范围必须1~65535")
                if new_cfg["min_memory_gb"] > new_cfg["max_memory_gb"]:
                    new_cfg["min_memory_gb"] = max(2, new_cfg["max_memory_gb"] // 2)

                self.service.save_config(server_path, new_cfg)

                sync_msg = []
                txt_file = Path(server_path) / "user_jvm_args.txt"
                if txt_file.exists():
                    self.service.sync_jvm_args_txt(server_path, new_cfg)
                    sync_msg.append("user_jvm_args.txt")
                bat_file = Path(server_path) / "run.bat"
                if bat_file.exists():
                    self.service.sync_memory_bat(server_path, new_cfg)
                    sync_msg.append("run.bat")

                msg_text = "✅配置保存成功"
                if sync_msg:
                    msg_text += f"\n已同步：{'、'.join(sync_msg)}"
                MessageBox("保存完成", msg_text, self).exec()
                self._refresh_list()

        except ValueError as ve:
            MessageBox("输入校验错误", str(ve), self).exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            MessageBox("配置操作异常", f"错误：{str(e)}", self).exec()

    def _append_log(self, text:str):
        """UI线程追加日志，自动滚动到底部"""
        self.log_text.append(text)
        scroll_bar = self.log_text.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def _update_run_status(self, status:str):
        """接收 running / stopped / crashed，更新UI徽章"""
        if status == "running":
            self.status_badge.setText("【运行中】")
        elif status == "stopped":
            self.status_badge.setText("【已停止】")
        elif status == "crashed":
            self.status_badge.setText("【已崩溃】")
        else:
            self.status_badge.setText("【未知】")

    @asyncSlot()
    async def _start_server(self):
        if self._watcher is not None:
            MessageBox("提示","服务已经在运行",self).exec()
            return
        server_path = self._get_selected_instance_path()
        if not server_path:
            return

        try:
            cfg = self.service.load_config(server_path)
            if cfg is None:
                MessageBox("错误","该实例缺少server_config.json，请先打开配置保存一次",self).exec()
                return

            # 回调闭包：asyncio后台线程 → Qt信号，线程安全
            def log_callback_sync(line: str):
                self.log_signal.emit(line)

            def status_callback_sync(new_status: str):
                self.status_text_signal.emit(new_status)

            self._watcher = await self.service.start_server(
                server_dir=server_path,
                config=cfg,
                log_callback=log_callback_sync,
                status_callback=status_callback_sync
            )
            self.log_signal.emit("=====服务已启动=====")

        except Exception as e:
            import traceback
            traceback.print_exc()
            MessageBox("启动失败", f"{str(e)}", self).exec()

    @asyncSlot()
    async def _stop_server(self):
        if self._watcher is None:
            MessageBox("提示","没有正在运行的服务",self).exec()
            return
        try:
            await self.service.stop_server(self._watcher)
            self.log_signal.emit("=====服务已停止=====")
        except Exception as e:
            MessageBox("停止异常", str(e), self).exec()
        finally:
            self._watcher = None

    @asyncSlot()
    async def _send_command(self):
        cmd = self.input_cmd.text().strip()
        if not cmd:
            return
        if self._watcher is None:
            MessageBox("提示","服务未启动，不能发送命令",self).exec()
            return
        try:
            await self.service.send_server_command(self._watcher, cmd)
            self.log_signal.emit(f"> {cmd}")
            self.input_cmd.clear()
        except Exception as e:
            MessageBox("发送命令失败", str(e), self).exec()
