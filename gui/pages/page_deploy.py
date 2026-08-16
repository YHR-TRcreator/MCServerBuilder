# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog)
from PySide6.QtCore import Qt
from qfluentwidgets import (CardWidget, PushButton, ComboBox, SpinBox,
                            LineEdit, BodyLabel, ProgressBar, MessageBox)
from qasync import asyncSlot
from pathlib import Path

from service.mc_server_service import MCServerService


class DeployPage(QWidget):
    def __init__(self, service: MCServerService, parent=None):
        super().__init__(parent)
        self.setObjectName("DeployPage")
        self.service = service
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24,24,24,24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        base_card = CardWidget()
        base_layout = QVBoxLayout(base_card)
        base_layout.setContentsMargins(20,16,20,16)
        base_layout.setSpacing(12)

        base_layout.addWidget(BodyLabel("新建 Minecraft 服务端"))

        # 实例名称
        row_name = QHBoxLayout()
        row_name.addWidget(BodyLabel("实例名称："), 1)
        self.edit_server_name = LineEdit()
        self.edit_server_name.setPlaceholderText("例如 MyServer")
        row_name.addWidget(self.edit_server_name, 4)
        base_layout.addLayout(row_name)

        # 实例保存目录
        row_dir = QHBoxLayout()
        row_dir.addWidget(BodyLabel("实例存放目录："),1)
        self.edit_server_dir = LineEdit()
        self.edit_server_dir.setPlaceholderText("留空使用默认 runtime/servers")
        row_dir.addWidget(self.edit_server_dir,4)
        self.btn_browse_dir = PushButton("选择文件夹")
        row_dir.addWidget(self.btn_browse_dir)
        base_layout.addLayout(row_dir)

        # MC游戏版本
        row_ver = QHBoxLayout()
        row_ver.addWidget(BodyLabel("MC游戏版本："),1)
        self.combo_mc_ver = ComboBox()
        self.combo_mc_ver.setPlaceholderText("点击刷新版本列表")
        row_ver.addWidget(self.combo_mc_ver,4)
        base_layout.addLayout(row_ver)

        # 服务端内核
        row_kernel = QHBoxLayout()
        row_kernel.addWidget(BodyLabel("服务端内核："),1)
        self.combo_kernel = ComboBox()
        self.combo_kernel.addItems(["Vanilla原版", "Paper", "Forge"])
        row_kernel.addWidget(self.combo_kernel,4)
        base_layout.addLayout(row_kernel)

        # 最大内存
        row_mem = QHBoxLayout()
        row_mem.addWidget(BodyLabel("最大内存(GB)："),1)
        self.spin_max_mem = SpinBox()
        self.spin_max_mem.setRange(2,64)
        self.spin_max_mem.setValue(4)
        row_mem.addWidget(self.spin_max_mem)
        base_layout.addLayout(row_mem)

        # Java路径
        row_java = QHBoxLayout()
        row_java.addWidget(BodyLabel("Java路径："),1)
        self.edit_java = LineEdit()
        self.edit_java.setPlaceholderText("留空自动检测Java")
        row_java.addWidget(self.edit_java,4)
        base_layout.addLayout(row_java)

        layout.addWidget(base_card, stretch=0)

        # 进度卡片
        progress_card = CardWidget()
        prog_layout = QVBoxLayout(progress_card)
        prog_layout.setContentsMargins(20,14,20,14)
        self.label_status = BodyLabel("就绪，等待开始部署")
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.label_status)
        prog_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_card, stretch=0)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_refresh_version = PushButton("刷新版本列表")
        self.btn_start_deploy = PushButton("开始部署服务端")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_refresh_version)
        btn_layout.addWidget(self.btn_start_deploy)
        layout.addLayout(btn_layout)

        # 信号绑定
        self.btn_browse_dir.clicked.connect(self._on_browse_dir)
        self.btn_refresh_version.clicked.connect(self._on_refresh_version)
        self.btn_start_deploy.clicked.connect(self._on_start_deploy)

    def _on_browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择实例存放目录")
        if folder:
            self.edit_server_dir.setText(folder)

    def _on_refresh_version(self):
        """刷新MC版本列表，多阶段进度更新"""
        self.label_status.setText("正在拉取版本列表...")
        self.progress_bar.setValue(5)
        try:
            ver_list = self.service.get_mc_version_list()
            self.progress_bar.setValue(60)
            self.combo_mc_ver.clear()
            self.combo_mc_ver.addItems(ver_list)
            self.progress_bar.setValue(100)
            self.label_status.setText(f"版本加载完成，共 {len(ver_list)} 个版本")
        except Exception as e:
            box = MessageBox("错误", f"拉取版本失败：{str(e)}", self)
            box.exec()
            self.label_status.setText("版本拉取失败")
            self.progress_bar.setValue(0)

    @asyncSlot()
    async def _on_start_deploy(self):
        name = self.edit_server_name.text().strip()
        custom_dir = self.edit_server_dir.text().strip()
        mc_ver = self.combo_mc_ver.currentText().strip()
        kernel_type = self.combo_kernel.currentText()
        max_mem = self.spin_max_mem.value()
        java_path = self.edit_java.text().strip()

        paths = self.service.get_project_paths()
        SERVERS_DIR = paths["SERVERS_DIR"]

        if not name:
            box = MessageBox("输入校验", "请填写实例名称！", self)
            box.exec()
            return
        if not mc_ver:
            box = MessageBox("输入校验", "请先刷新并选择MC游戏版本！", self)
            box.exec()
            return

        confirm_box = MessageBox(
            "确认部署",
            f"实例名称：{name}\n"
            f"存放目录：{custom_dir if custom_dir else '默认目录'}\n"
            f"MC版本：{mc_ver}\n"
            f"内核：{kernel_type}\n"
            f"最大内存：{max_mem}GB\n\n确定开始部署？",
            self
        )
        ok = confirm_box.exec()
        if not ok:
            return

        self.progress_bar.setValue(0)
        self.label_status.setText("准备部署环境...")

        try:
            self.progress_bar.setValue(10)

            # ========== 和CLI保持一致：分支处理 ==========
            if kernel_type == "Forge":
                # Forge流程：对齐CLI菜单2
                if custom_dir:
                    server_path = custom_dir
                else:
                    server_path = str(Path(SERVERS_DIR) / name)
                java_exe = java_path if java_path else "java"

                self.label_status.setText("正在安装Forge服务端核心...")
                self.progress_bar.setValue(20)

                # 获取最新构建号
                build_list = self.service.get_forge_builds(mc_ver)
                if not build_list:
                    raise Exception("该版本没有可用Forge构建")
                target_build = build_list[0]["version"]

                ok_install, msg = await self.service.install_forge(
                    server_path, mc_ver, target_build, java_exe, force_reinstall=False
                )
                self.progress_bar.setValue(70)

                if not ok_install:
                    if "已部署完整Forge服务端" in msg:
                        box_force = MessageBox("目录已存在", "检测目录已有服务端，是否强制覆盖重装？", self)
                        if box_force.exec():
                            ok_install, msg = await self.service.install_forge(
                                server_path, mc_ver, target_build, java_exe, force_reinstall=True
                            )
                        else:
                            self.label_status.setText("用户取消安装")
                            return
                    else:
                        raise Exception(msg)

                # 安装成功后生成配置，复制CLI逻辑
                hw = self.service.get_hardware_info()
                rec_memory_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                rec_memory_gb = round(rec_memory_mb / 1024)
                default_cfg = self.service.create_default_config(name, server_path, java_exe, rec_memory_gb)
                self.service.save_config(server_path, default_cfg)
                self.service.sync_jvm_args_txt(server_path, default_cfg)
                self.service.sync_memory_bat(server_path, default_cfg)

            else:
                # Vanilla / Paper / Fabric，调用 deploy_vanilla_server，只传4个参数！
                self.label_status.setText("正在下载服务端核心文件...")
                await self.service.deploy_vanilla_server(
                    server_name=name,
                    mc_version=mc_ver,
                    kernel=kernel_type.lower(),
                    memory_gb=max_mem
                )
                server_path = str(Path(SERVERS_DIR) / name)
                hw = self.service.get_hardware_info()
                rec_memory_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                rec_memory_gb = round(rec_memory_mb / 1024)
                final_memory = max(max_mem, rec_memory_gb)
                default_cfg = self.service.create_default_config(name, server_path, "java", final_memory)
                self.service.save_config(server_path, default_cfg)

            self.progress_bar.setValue(100)
            self.label_status.setText("✅部署任务执行完成")
            MessageBox("完成","部署任务执行完成",self).exec()

        except Exception as err:
            import traceback
            traceback.print_exc()
            box = MessageBox("部署异常", f"部署出错：{str(err)}", self)
            box.exec()
            self.label_status.setText("部署失败")
            self.progress_bar.setValue(0)
