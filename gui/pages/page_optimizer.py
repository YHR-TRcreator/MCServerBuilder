# -*- coding: utf-8 -*-
"""
gui/pages/page_optimizer.py
硬件扫描 & 服务配置优化页面
修复：字典key错误 cpu → cpu_name，参数传递正确；实例下拉框为空问题
"""
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout
from PySide6.QtCore import Qt
from qfluentwidgets import (CardWidget, PushButton, BodyLabel, LineEdit,
                            SpinBox, MessageBox, ComboBox)
from qasync import asyncSlot


class OptimizerPage(QWidget):
    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service
        self._instance_map: Dict[str, str] = {}
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # =========硬件信息卡片=========
        hw_card = CardWidget()
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setContentsMargins(16,16,16,16)
        hw_layout.setSpacing(10)

        self.info_cpu = BodyLabel("CPU：--")
        self.info_mem_total = BodyLabel("总内存：-- GB")
        self.info_mem_recommend = BodyLabel("推荐分配最大内存：-- GB")

        self.btn_scan_hw = PushButton("重新扫描硬件")
        self.btn_scan_hw.clicked.connect(self._scan_hardware)

        hw_layout.addWidget(self.info_cpu)
        hw_layout.addWidget(self.info_mem_total)
        hw_layout.addWidget(self.info_mem_recommend)
        hw_layout.addWidget(self.btn_scan_hw)
        main_layout.addWidget(hw_card)

        # =========实例配置卡片=========
        cfg_card = CardWidget()
        cfg_layout = QFormLayout(cfg_card)
        cfg_layout.setContentsMargins(16,16,16,16)
        cfg_layout.setSpacing(12)

        self.combo_instance = ComboBox()
        self.combo_instance.setPlaceholderText("请选择一个服务实例")

        self.spin_min_mem = SpinBox()
        self.spin_min_mem.setRange(1, 64)
        self.spin_min_mem.setSuffix(" GB")

        self.spin_max_mem = SpinBox()
        self.spin_max_mem.setRange(1, 64)
        self.spin_max_mem.setSuffix(" GB")

        self.edit_jvm_args = LineEdit()
        self.edit_jvm_args.setPlaceholderText("JVM参数，留空使用系统推荐")

        btn_layout = QHBoxLayout()
        self.btn_load_cfg = PushButton("读取现有配置")
        self.btn_auto_opt = PushButton("一键智能优化配置")
        self.btn_save_cfg = PushButton("写入配置到实例")
        btn_layout.addWidget(self.btn_load_cfg)
        btn_layout.addWidget(self.btn_auto_opt)
        btn_layout.addWidget(self.btn_save_cfg)

        cfg_layout.addRow("选择服务实例", self.combo_instance)
        cfg_layout.addRow("最小内存", self.spin_min_mem)
        cfg_layout.addRow("最大内存", self.spin_max_mem)
        cfg_layout.addRow("JVM参数", self.edit_jvm_args)
        cfg_layout.addRow("", btn_layout)

        main_layout.addWidget(cfg_card)

        # 提示文本
        tip_label = BodyLabel("自动设置内存与GC参数，自动同步user_jvm_args.txt / run.bat")
        tip_label.setWordWrap(True)
        main_layout.addWidget(tip_label)

        # 绑定信号
        self.btn_load_cfg.clicked.connect(self._load_selected_config)
        self.btn_auto_opt.clicked.connect(self._auto_optimize)
        self.btn_save_cfg.clicked.connect(self._save_instance_config)

        # !!!! 删除这里的 self.refresh_instance_list()，不要在setup_ui阶段刷新！

    def showEvent(self, event):
        """每次切换打开该标签页，自动刷新实例下拉"""
        super().showEvent(event)
        self.refresh_instance_list()

    def refresh_instance_list(self):
        """刷新服务器实例下拉列表"""
        if not self.service:
            print("[OptimizerPage] service对象为空")
            return
        self.combo_instance.clear()
        self._instance_map.clear()
        try:
            server_dict = self.service.get_all_servers()
            print("[OptimizerPage] get_all_servers返回：", server_dict)
            if not server_dict:
                print("[OptimizerPage] 没有读取到任何服务实例")
                return
            for name, path in server_dict.items():
                self._instance_map[name] = path
                self.combo_instance.addItem(name)
        except Exception as e:
            print("[OptimizerPage] 刷新实例异常：", repr(e))

    def _get_selected_server_dir(self) -> Optional[str]:
        name = self.combo_instance.currentText()
        if not name or name not in self._instance_map:
            return None
        return self._instance_map[name]

    @asyncSlot()
    async def _scan_hardware(self):
        """调用service层扫描硬件【修复key：cpu_name】"""
        if not self.service:
            MessageBox("错误", "Service实例未初始化", self).exec()
            return
        try:
            hw = self.service.get_hardware_info()
            # 正确字典key：cpu_name total_memory_gb free_memory_gb
            rec_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
            rec_gb = round(rec_mb / 1024)

            self.info_cpu.setText(f"CPU：{hw['cpu_name']}")
            self.info_mem_total.setText(f"总内存：{hw['total_memory_gb']} GB")
            self.info_mem_recommend.setText(f"推荐分配最大内存：{rec_gb} GB")
        except Exception as e:
            MessageBox("硬件扫描失败", str(e), self).exec()

    @asyncSlot()
    async def _load_selected_config(self):
        server_dir = self._get_selected_server_dir()
        if not server_dir:
            MessageBox("提示", "请先选择服务实例", self).exec()
            return
        try:
            cfg = self.service.load_config(server_dir)
            if not cfg:
                MessageBox("警告", "读取配置为空", self).exec()
                return
            self.spin_min_mem.setValue(cfg.get("min_memory_gb",2))
            self.spin_max_mem.setValue(cfg.get("max_memory_gb",4))
            self.edit_jvm_args.setText(cfg.get("jvm_args",""))
        except Exception as e:
            MessageBox("读取失败", str(e), self).exec()

    @asyncSlot()
    async def _auto_optimize(self):
        """一键智能优化"""
        if not self.service:
            return
        try:
            hw = self.service.get_hardware_info()
            rec_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
            rec_gb = max(2, round(rec_mb / 1024))
            self.spin_max_mem.setValue(rec_gb)
            self.spin_min_mem.setValue(max(2, rec_gb//2))
            self.edit_jvm_args.setText("-XX:+UseG1GC -XX:+ParallelRefProcEnabled")
            MessageBox("完成","已根据硬件自动填充内存与GC参数",self).exec()
        except Exception as e:
            MessageBox("优化失败", str(e), self).exec()

    @asyncSlot()
    async def _save_instance_config(self):
        server_dir = self._get_selected_server_dir()
        if not server_dir:
            MessageBox("提示", "请先选择服务实例", self).exec()
            return
        try:
            cfg = self.service.load_config(server_dir)
            if not cfg:
                MessageBox("错误", "实例配置不存在", self).exec()
                return
            cfg["min_memory_gb"] = self.spin_min_mem.value()
            cfg["max_memory_gb"] = self.spin_max_mem.value()
            cfg["jvm_args"] = self.edit_jvm_args.text()

            self.service.save_config(server_dir, cfg)
            self.service.sync_jvm_args_txt(server_dir, cfg)
            self.service.sync_memory_bat(server_dir, cfg)
            MessageBox("成功", "配置已保存，已同步user_jvm_args.txt与run.bat", self).exec()
        except Exception as e:
            MessageBox("保存失败", str(e), self).exec()
