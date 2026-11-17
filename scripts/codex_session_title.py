#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1"]
# ///
"""通过现有 Codex App Server 更新当前会话标题；不启动服务或修改数据库。"""

import argparse
import asyncio
import json
import math
import os
import signal
import sys
import unicodedata
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from websockets.asyncio.client import unix_connect
from websockets.exceptions import WebSocketException


class TitleError(Exception):
    """可直接展示且不含聊天内容的诊断。"""


class RpcError(TitleError):
    """服务明确返回请求错误，区别于请求发出后失联。"""


def nonnegative_integer(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("轮次必须是非负整数")
    return number


def positive_timeout(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("超时必须是有限正数")
    return number


def description_text(value):
    text = value.strip()
    if not text or any(unicodedata.category(char).startswith("C") for char in value):
        raise argparse.ArgumentTypeError("描述不能为空或包含控制字符")
    if len(text) > 200:
        raise argparse.ArgumentTypeError("描述不能超过 200 字符")
    return text


def current_thread_id():
    value = os.environ.get("CODEX_THREAD_ID", "")
    try:
        if str(UUID(value)) != value:
            raise ValueError
    except ValueError as error:
        raise TitleError(
            "缺少有效的 CODEX_THREAD_ID；请在目标 Codex 会话内运行"
        ) from error
    return value


def socket_path(value):
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise TitleError("缺少有效的绝对 socket 路径；可显式传入 --socket")
    return value


async def discover_socket():
    process = await asyncio.create_subprocess_exec(
        "codex",
        "app-server",
        "daemon",
        "version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    completed = False
    try:
        stdout, _ = await process.communicate()
        completed = True
    finally:
        # 包装器可能已退出，但其后代仍持有管道。清理本次启动的进程组。
        if not completed:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.communicate()
    if process.returncode != 0:
        raise TitleError("codex app-server daemon version 执行失败；未启动或修改服务")
    try:
        info = json.loads(stdout)
    except (ValueError, UnicodeDecodeError) as error:
        raise TitleError("服务发现输出不是有效 JSON") from error
    if not isinstance(info, dict) or info.get("status") != "running":
        raise TitleError("未发现运行中的 Codex App Server")
    return socket_path(info.get("socketPath"))


class TitleClient:
    def __init__(self, thread_id, title):
        self.thread_id = thread_id
        self.title = title
        self.request_id = 0
        self.unverified_write = False

    async def rpc(self, connection, method, params):
        self.request_id += 1
        request_id = self.request_id
        await connection.send(
            json.dumps({"id": request_id, "method": method, "params": params})
        )
        while True:
            try:
                message = json.loads(await connection.recv())
            except (ValueError, UnicodeDecodeError) as error:
                raise TitleError("服务返回无效 JSON") from error
            if not isinstance(message, dict):
                raise TitleError("服务响应必须是 JSON 对象")
            if "method" in message:
                if "id" in message:
                    raise TitleError("服务要求本工具不支持的客户端操作")
                continue
            if type(message.get("id")) is not int or message["id"] != request_id:
                continue
            if "error" in message:
                raise RpcError(f"RPC {method} 返回错误；请检查服务版本及当前会话可用性")
            if not isinstance(message.get("result"), dict):
                raise TitleError(f"RPC {method} 缺少有效 result")
            return message["result"]

    async def read_name(self, connection):
        result = await self.rpc(
            connection,
            "thread/read",
            {"threadId": self.thread_id, "includeTurns": False},
        )
        thread = result.get("thread")
        if not isinstance(thread, dict) or thread.get("id") != self.thread_id:
            raise TitleError("服务返回的会话 ID 不匹配；未选择其他聊天")
        if "name" not in thread or (
            thread["name"] is not None and not isinstance(thread["name"], str)
        ):
            raise TitleError("服务缺少受支持的 name 字段")
        return thread["name"]

    async def update(self, path):
        async with unix_connect(
            path, open_timeout=None, close_timeout=0.1, ping_interval=None
        ) as connection:
            await self.rpc(
                connection,
                "initialize",
                {
                    "clientInfo": {
                        "name": "coding_agent_session_title",
                        "version": "1.0",
                    }
                },
            )
            await connection.send(json.dumps({"method": "initialized", "params": {}}))
            if await self.read_name(connection) == self.title:
                return False
            # 发送开始后任何传输/读回失败均视为结果未知，避免误报未写入或成功。
            self.unverified_write = True
            try:
                await self.rpc(
                    connection,
                    "thread/name/set",
                    {"threadId": self.thread_id, "name": self.title},
                )
            except RpcError:
                self.unverified_write = False
                raise
            if await self.read_name(connection) != self.title:
                raise TitleError("标题读回不一致；请核对当前会话")
            self.unverified_write = False
            return True


async def execute(client, args):
    async with asyncio.timeout(args.timeout):
        path = (
            socket_path(args.socket)
            if args.socket is not None
            else await discover_socket()
        )
        return await client.update(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "complete"))
    parser.add_argument("--round", type=nonnegative_integer, required=True)
    parser.add_argument("--description", type=description_text, required=True)
    parser.add_argument(
        "--socket", help="当前主机已运行 App Server 的 Unix socket 绝对路径"
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout,
        default=10.0,
        help="操作总超时秒数（不含 uv 准备依赖；默认 10）",
    )
    args = parser.parse_args(argv)
    client = None
    try:
        thread_id = current_thread_id()
        if os.name != "posix":
            raise TitleError("本工具需要 Unix socket；当前操作系统未适配")
        title = f"r{args.round}-{args.description}" + (
            "-已完成" if args.action == "complete" else ""
        )
        client = TitleClient(thread_id, title)
        changed = asyncio.run(execute(client, args))
    except (TitleError, OSError, TimeoutError, WebSocketException) as error:
        unknown = client is not None and client.unverified_write
        if isinstance(error, TimeoutError):
            detail = "连接或 RPC 操作超时"
        elif isinstance(error, TitleError):
            detail = str(error)
        elif isinstance(error, OSError):
            detail = f"无法访问 CLI 或控制 socket（{type(error).__name__}）；请检查本机运行前提"
        else:
            detail = "WebSocket 连接或握手失败；请检查服务及协议版本"
        if unknown:
            detail += "；改名可能已经生效，结果未知，请核对标题后重试"
        print(
            json.dumps(
                {"status": "unknown" if unknown else "failed", "error": detail},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3 if unknown else 1
    print(
        json.dumps(
            {
                "status": "verified",
                "thread_id": thread_id,
                "title": title,
                "changed": changed,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
