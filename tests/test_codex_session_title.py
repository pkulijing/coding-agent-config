"""用隔离 CLI 和原生 Unix WebSocket fixture 验证会话标题工具。"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import unix_serve

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/codex_session_title.py"
THREAD_ID = "01a1e7d9-d57b-7102-9b63-f2ffbaa51299"
OTHER_ID = "01a1e7d9-d57b-7102-9b63-f2ffbaa51300"


class AppServer:
    def __init__(self, mode="normal", name=None):
        self.mode = mode
        self.name = name
        self.requests = []
        self.writes = []

    def handle(self, connection):
        try:
            for raw in connection:
                request = json.loads(raw)
                self.requests.append(request)
                method = request["method"]
                if method == "initialized":
                    continue
                request_id = request["id"]
                if self.mode == "timeout":
                    continue
                if self.mode == "malformed":
                    connection.send("[]")
                    continue
                if self.mode == "rpc-error" and method == "thread/name/set":
                    connection.send(
                        json.dumps(
                            {
                                "id": request_id,
                                "error": {"code": -32602, "message": "rejected"},
                            }
                        )
                    )
                    continue
                if method == "initialize":
                    result = {"userAgent": "fixture"}
                elif method == "thread/read":
                    assert request["params"] == {
                        "threadId": THREAD_ID,
                        "includeTurns": False,
                    }
                    if self.mode == "readback-error" and self.writes:
                        connection.send(
                            json.dumps(
                                {
                                    "id": request_id,
                                    "error": {"code": -32000, "message": "read failed"},
                                }
                            )
                        )
                        continue
                    result = {
                        "thread": {
                            "id": OTHER_ID
                            if self.mode == "wrong-thread"
                            else THREAD_ID,
                            "name": self.name,
                        }
                    }
                    if self.mode == "missing-name":
                        del result["thread"]["name"]
                elif method == "thread/name/set":
                    assert set(request["params"]) == {"threadId", "name"}
                    assert request["params"]["threadId"] == THREAD_ID
                    self.writes.append(request["params"])
                    if self.mode != "mismatch":
                        self.name = request["params"]["name"]
                    if self.mode == "disconnect-after-write":
                        connection.close()
                        return
                    result = {}
                else:
                    raise AssertionError(f"unexpected method: {method}")
                # 通知和其他请求的响应不能冒充本请求成功。
                connection.send(
                    json.dumps({"method": "thread/status/changed", "params": {}})
                )
                connection.send(json.dumps({"id": 999, "result": {}}))
                connection.send(json.dumps({"id": request_id, "result": result}))
        except ConnectionClosed:
            pass


@contextmanager
def server(mode="normal", name=None):
    # Unix socket 有路径长度限制，独立短目录也不继承宿主 HOME。
    with tempfile.TemporaryDirectory(prefix="cst-") as directory:
        path = Path(directory) / "rpc.sock"
        fixture = AppServer(mode, name)
        with unix_serve(fixture.handle, str(path), close_timeout=0.1) as listener:
            thread = threading.Thread(target=listener.serve_forever, daemon=True)
            thread.start()
            try:
                yield fixture, path
            finally:
                listener.shutdown()
                thread.join(timeout=2)
                assert not thread.is_alive()


@pytest.fixture
def isolated(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    record = tmp_path / "discovery.json"
    stub = bin_dir / "codex"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, subprocess, sys, time\n"
        "if os.environ.get('DISCOVERY_FORK'):\n"
        "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)'])\n"
        "pathlib.Path(os.environ['DISCOVERY_RECORD']).write_text(json.dumps({'argv': sys.argv[1:], 'pid': os.getpid()}))\n"
        "time.sleep(float(os.environ.get('DISCOVERY_DELAY', '0')))\n"
        "print(os.environ.get('DISCOVERY_OUTPUT', '{}'))\n"
        "sys.exit(int(os.environ.get('DISCOVERY_EXIT', '0')))\n"
    )
    stub.chmod(0o755)
    env = {
        "HOME": str(home),
        "CODEX_HOME": str(home / "codex"),
        "PATH": str(bin_dir) + os.pathsep + os.defpath,
        "CODEX_THREAD_ID": THREAD_ID,
        "DISCOVERY_RECORD": str(record),
        "LC_ALL": "C.UTF-8",
    }

    def run(*args, env_changes=None):
        child_env = env.copy()
        for key, value in (env_changes or {}).items():
            if value is None:
                child_env.pop(key, None)
            else:
                child_env[key] = value
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            cwd=home,
            env=child_env,
            text=True,
            capture_output=True,
            timeout=5,
        )

    return run, env, record


def test_main_discovers_and_updates_current_thread(isolated):
    run, env, record = isolated
    with server() as (rpc, socket):
        env["DISCOVERY_OUTPUT"] = json.dumps(
            {"status": "running", "socketPath": str(socket)}
        )
        result = run("start", "--round", "31", "--description", "修复视频卡顿")
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "status": "verified",
            "thread_id": THREAD_ID,
            "title": "r31-修复视频卡顿",
            "changed": True,
        }
        assert rpc.name == "r31-修复视频卡顿"
        assert len(rpc.writes) == 1
        assert [r["method"] for r in rpc.requests] == [
            "initialize",
            "initialized",
            "thread/read",
            "thread/name/set",
            "thread/read",
        ]
        assert json.loads(record.read_text())["argv"] == [
            "app-server",
            "daemon",
            "version",
        ]


def test_complete_is_idempotent_and_preserves_text(isolated):
    run, _, record = isolated
    description = '修复 "视频" 卡顿 $(echo data)'
    title = f"r0-{description}-已完成"
    with server() as (rpc, socket):
        args = (
            "complete",
            "--round",
            "0",
            "--description",
            description,
            "--socket",
            str(socket),
        )
        for changed in (True, False):
            result = run(*args)
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["title"] == title
            assert json.loads(result.stdout)["changed"] is changed
        assert rpc.name == title
        assert len(rpc.writes) == 1
        assert not record.exists()


@pytest.mark.parametrize(
    "mode,exit_code",
    [
        ("wrong-thread", 1),
        ("missing-name", 1),
        ("rpc-error", 1),
        ("malformed", 1),
        ("mismatch", 3),
        ("readback-error", 3),
        ("disconnect-after-write", 3),
        ("timeout", 1),
    ],
)
def test_protocol_failures_are_not_success(isolated, mode, exit_code):
    run, _, _ = isolated
    with server(mode) as (rpc, socket):
        result = run(
            "start",
            "--round",
            "31",
            "--description",
            "修复卡顿",
            "--socket",
            str(socket),
            "--timeout",
            "0.3",
        )
        assert result.returncode == exit_code, result.stderr
        assert not result.stdout
        error = json.loads(result.stderr)
        assert error["status"] == ("unknown" if exit_code == 3 else "failed")
        if mode in {
            "wrong-thread",
            "missing-name",
            "rpc-error",
            "malformed",
            "timeout",
        }:
            assert not rpc.writes


@pytest.mark.parametrize(
    "changes",
    [
        {"CODEX_THREAD_ID": None},
        {"CODEX_THREAD_ID": ""},
        {"CODEX_THREAD_ID": "not-a-session-id"},
    ],
)
def test_missing_or_invalid_thread_fails_before_discovery(isolated, changes):
    run, _, record = isolated
    result = run(
        "start", "--round", "31", "--description", "修复卡顿", env_changes=changes
    )
    assert result.returncode != 0
    assert "CODEX_THREAD_ID" in result.stderr
    assert not record.exists()


@pytest.mark.parametrize(
    "option,value",
    [
        ("--round", "-1"),
        ("--round", "abc"),
        ("--description", " "),
        ("--description", "bad\nname"),
        ("--timeout", "0"),
        ("--timeout", "nan"),
        ("--timeout", "inf"),
    ],
)
def test_invalid_arguments_do_not_discover_service(isolated, option, value):
    run, _, record = isolated
    args = {"--round": "31", "--description": "修复卡顿", "--timeout": "1"}
    args[option] = value
    result = run("start", *(part for pair in args.items() for part in pair))
    assert result.returncode != 0
    assert not record.exists()


@pytest.mark.parametrize(
    "output,exit_code",
    [
        ("not json", "0"),
        ("[]", "0"),
        ('{"status":"stopped"}', "0"),
        ('{"status":"running"}', "0"),
        ('{"status":"running","socketPath":"relative.sock"}', "0"),
        ('{"status":"running","socketPath":"/missing.sock"}', "1"),
    ],
)
def test_failed_discovery_does_not_report_success(isolated, output, exit_code):
    run, _, _ = isolated
    result = run(
        "start",
        "--round",
        "31",
        "--description",
        "修复卡顿",
        env_changes={"DISCOVERY_OUTPUT": output, "DISCOVERY_EXIT": exit_code},
    )
    assert result.returncode == 1
    assert not result.stdout
    assert json.loads(result.stderr)["status"] == "failed"


def test_discovery_timeout_reaps_its_process(isolated):
    run, _, record = isolated
    started = time.monotonic()
    result = run(
        "start",
        "--round",
        "31",
        "--description",
        "修复卡顿",
        "--timeout",
        "0.2",
        env_changes={"DISCOVERY_DELAY": "3"},
    )
    assert result.returncode == 1
    assert time.monotonic() - started < 2
    pid = json.loads(record.read_text())["pid"]
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("delay", ["0", "3"])
def test_discovery_timeout_does_not_wait_for_wrapper_descendant(isolated, delay):
    run, _, _ = isolated
    started = time.monotonic()
    result = run(
        "start",
        "--round",
        "31",
        "--description",
        "修复卡顿",
        "--timeout",
        "0.2",
        env_changes={"DISCOVERY_DELAY": delay, "DISCOVERY_FORK": "1"},
    )
    assert result.returncode == 1
    assert time.monotonic() - started < 2


def test_missing_socket_is_failed_before_write(isolated, tmp_path):
    run, _, _ = isolated
    result = run(
        "start",
        "--round",
        "31",
        "--description",
        "修复卡顿",
        "--socket",
        str(tmp_path / "absent"),
    )
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "failed"


def test_absent_cli_fails_without_starting_service(isolated):
    run, _, record = isolated
    result = run(
        "start",
        "--round",
        "31",
        "--description",
        "修复卡顿",
        env_changes={"PATH": "/nonexistent"},
    )
    assert result.returncode == 1
    assert json.loads(result.stderr)["status"] == "failed"
    assert not record.exists()


def test_unsupported_platform_is_explicit(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("codex_session_title", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with monkeypatch.context() as context:
        context.setenv("CODEX_THREAD_ID", THREAD_ID)
        context.setattr(module.os, "name", "nt")
        result = module.main(["start", "--round", "31", "--description", "修复卡顿"])
    assert result == 1
    assert "当前操作系统未适配" in capsys.readouterr().err
