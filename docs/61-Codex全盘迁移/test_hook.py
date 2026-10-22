"""在隔离 HOME 和工具桩中验证两端编辑事件确实调用格式化工具。"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.log = self.home / 'calls'
        for name in ('uv', 'prettier'):
            tool = self.bin / name
            tool.write_text('#!/bin/bash\nprintf "%s\\n" "$@" >> "$CALLS"\n')
            tool.chmod(0o755)
        self.env = {'PATH': f'{self.bin}:/opt/homebrew/bin:/usr/bin:/bin', 'HOME': str(self.home), 'CALLS': str(self.log), 'LC_ALL': 'C'}
        self.work = self.home / 'space repo'
        self.work.mkdir()

    def run_hook(self, payload):
        result = subprocess.run(['/bin/bash', str(ROOT / 'hooks/fix-after-edit.sh')], input=json.dumps(payload), text=True, cwd=self.home, env=self.env, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_cc_file_path(self):
        file = self.work / '中文 test.py'
        file.touch()
        calls = self.run_hook({'tool_name': 'Edit', 'cwd': str(self.work), 'tool_input': {'file_path': str(file)}})
        self.assertEqual(calls.count(str(file)), 2)
        self.assertIn('F401', calls)

    def test_codex_patch_multiple_relative_files(self):
        py = self.work / 'module.py'
        md = self.work / 'read me.md'
        py.touch()
        md.touch()
        patch = '*** Begin Patch\n*** Update File: module.py\n@@\n+x\n*** Add File: read me.md\n+x\n*** Delete File: removed.py\n*** End Patch'
        calls = self.run_hook({'tool_name': 'apply_patch', 'cwd': str(self.work), 'tool_input': {'command': patch}})
        self.assertEqual(calls.count(str(py)), 2)
        self.assertEqual(calls.count(str(md)), 1)
        self.assertNotIn(str(self.work / 'removed.py'), calls)

    def test_codex_move_formats_destination(self):
        file = self.work / 'destination.py'
        file.touch()
        calls = self.run_hook({'tool_name': 'apply_patch', 'cwd': str(self.work), 'tool_input': {'command': '*** Update File: source.py\n*** Move to: destination.py\n'}})
        self.assertEqual(calls.count(str(file)), 2)

    def test_shell_payload_is_not_executed(self):
        marker = self.home / 'executed'
        calls = self.run_hook({'tool_name': 'Bash', 'cwd': str(self.work), 'tool_input': {'command': f'touch {marker}\n*** Update File: module.py'}})
        self.assertEqual(calls, [])
        self.assertFalse(marker.exists())

    def test_unknown_payload_is_best_effort(self):
        self.assertEqual(self.run_hook({}), [])


if __name__ == '__main__':
    unittest.main()
