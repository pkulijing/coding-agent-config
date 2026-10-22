"""复用历史调度用例，显式更新任务名与进程桩，不修改历史文件。"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('legacy_scheduler', ROOT / 'docs/58-调度器自杀式重注册/test_scheduler_install.py')
legacy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(legacy)
legacy.LABEL = 'com.coding-agent-config.auto-update'
original_setup = legacy.SchedulerInstallTest.setUp


def isolated_setup(self):
    original_setup(self)
    (self.bin / 'ps').unlink()
    self._write_exec(self.bin / 'ps', '''#!/bin/bash
pid=$(cat "$FAKE_STATE_DIR/pid" 2>/dev/null) || exit 1
[ "$pid" != 99999999 ] || exit 1
printf '%s\\n' "$pid"
''')
    # 历史桩只模拟单个 label，新迁移逻辑会同时查询旧/新 label，需区分真实注册对象。
    fake = legacy.FAKE_LAUNCHCTL.replace('LABEL_PLACEHOLDER', legacy.LABEL)
    fake = fake.replace('label="${1:-}"', 'label="${1:-}"\n    [ -z "$label" ] || [ "$label" = "' + legacy.LABEL + '" ] || exit 113')
    self._write_exec(self.bin / 'launchctl', fake)


if __name__ == '__main__':
    legacy.SchedulerInstallTest.setUp = isolated_setup
    suite = unittest.defaultTestLoader.loadTestsFromModule(legacy)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
