# -*- coding: utf-8 -*-
"""
core/server_runtime/rcon_client.py
Minecraft RCON 远程控制台客户端
通过 TCP 协议向服务端发送指令，不依赖 stdin 管道，Windows 下稳定可用
"""
import socket
import struct
import threading
import time
from typing import Optional
from common.logger import logger

# RCON 包类型
RCON_TYPE_LOGIN = 3
RCON_TYPE_COMMAND = 2
RCON_TYPE_RESPONSE = 0


class RconClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 25575, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self.sock: Optional[socket.socket] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._connected = False

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_packet(self, req_id: int, packet_type: int, payload: str):
        """发送 RCON 数据包"""
        data = struct.pack("<ii", req_id, packet_type) + payload.encode("utf-8") + b"\x00\x00"
        length = struct.pack("<i", len(data))
        self.sock.sendall(length + data)

    def _recv_packet(self) -> tuple:
        """接收 RCON 数据包，返回 (request_id, response_type, payload)"""
        # 先读4字节长度
        length_data = self._recv_exact(4)
        if not length_data:
            return None
        length = struct.unpack("<i", length_data)[0]
        # 再读剩余内容
        packet_data = self._recv_exact(length)
        if not packet_data:
            return None
        req_id, resp_type = struct.unpack("<ii", packet_data[:8])
        payload = packet_data[8:-2].decode("utf-8", errors="replace")
        return req_id, resp_type, payload

    def _recv_exact(self, size: int) -> Optional[bytes]:
        """精确读取指定字节数"""
        data = b""
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def connect(self) -> bool:
        """连接 RCON 并认证"""
        if self._connected:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            # 发送认证
            req_id = self._next_id()
            self._send_packet(req_id, RCON_TYPE_LOGIN, self.password)
            # 接收认证响应
            resp = self._recv_packet()
            if resp is None:
                logger.error("RCON 认证失败：无响应")
                self.sock.close()
                return False
            resp_id, _, _ = resp
            if resp_id == -1:
                logger.error("RCON 认证失败：密码错误")
                self.sock.close()
                return False
            self._connected = True
            logger.info("✅ RCON 连接成功")
            return True
        except Exception as e:
            logger.error(f"RCON 连接失败: {e}")
            if self.sock:
                self.sock.close()
            return False

    def send_command(self, command: str) -> str:
        """
        发送指令并返回执行结果
        :param command: 指令内容（不带斜杠）
        :return: 服务端返回的执行结果文本
        """
        if not self._connected:
            logger.warning("RCON 未连接，无法发送指令")
            return ""
        with self._lock:
            try:
                req_id = self._next_id()
                self._send_packet(req_id, RCON_TYPE_COMMAND, command)
                # 接收响应
                resp = self._recv_packet()
                if resp is None:
                    return ""
                _, _, payload = resp
                return payload
            except Exception as e:
                logger.error(f"RCON 发送指令失败: {e}")
                self._connected = False
                return ""

    def disconnect(self):
        """断开连接"""
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def is_connected(self) -> bool:
        return self._connected