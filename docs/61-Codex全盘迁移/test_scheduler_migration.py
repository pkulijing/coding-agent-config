"""调度名称迁移的跨平台沙盘；不接触真实 launchd/systemd。"""
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
OLD = 'com.claude-code-global.auto-update'
NEW = 'com.coding-agent-config.auto-update'


class SchedulerMigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.state = self.root / 'state'
        self.state.mkdir()
        for name in ('dirname', 'mkdir', 'sed', 'ps', 'awk', 'tr', 'cmp', 'mktemp', 'mv', 'rm', 'cat'):
            (self.bin / name).symlink_to(shutil.which(name))
        (self.bin / 'ps').unlink()
        self.write('ps', '#!/bin/bash\necho 424242\n')
        self.write('uname', '#!/bin/bash\necho "$FAKE_OS"\n')
        self.write('launchctl', '''#!/bin/bash
printf '%s\\n' "$*" >> "$FAKE_STATE/calls"
case "$1" in
 list)
  [ -f "$FAKE_STATE/$2" ] || exit 113
  echo '{'
  if [ -f "$FAKE_STATE/pid-$2" ]; then printf '"PID" = %s;\\n' "$(cat "$FAKE_STATE/pid-$2")"; fi
  echo '}' ;;
 load) : > "$FAKE_STATE/com.coding-agent-config.auto-update" ;;
 unload) rm -f "$FAKE_STATE/$(basename "$2" .plist)" ;;
 remove) rm -f "$FAKE_STATE/$2" ;;
esac
''')
        (self.bin / 'basename').symlink_to(shutil.which('basename'))
        self.env = {'HOME': str(self.home), 'PATH': str(self.bin), 'LC_ALL': 'C',
                    'FAKE_STATE': str(self.state), 'FAKE_OS': 'Darwin'}
        self.old = self.home / f'Library/LaunchAgents/{OLD}.plist'
        self.new = self.home / f'Library/LaunchAgents/{NEW}.plist'

    def write(self, name, body):
        p = self.bin / name
        p.write_text(body)
        p.chmod(0o755)

    def run_install(self):
        subprocess.run(['/bin/bash', str(REPO / 'scheduler/install.sh')], env=self.env,
                       capture_output=True, text=True, check=True)

    def old_installed(self, running=False):
        self.old.parent.mkdir(parents=True)
        self.old.write_text('old')
        (self.state / OLD).touch()
        if running:
            (self.state / f'pid-{OLD}').write_text('424242')

    def test_macos_migrate_old_job(self):
        self.old_installed()
        self.run_install()
        self.assertFalse(self.old.exists())
        self.assertFalse((self.state / OLD).exists())
        parsed = plistlib.loads(self.new.read_bytes())
        self.assertEqual(parsed['Label'], NEW)
        self.assertEqual(parsed['EnvironmentVariables']['AGENT_HOME'], str(self.home / '.coding-agent'))

    def test_old_job_cannot_kill_itself(self):
        self.old_installed(running=True)
        self.run_install()
        self.assertFalse(self.old.exists())
        self.assertTrue(self.new.exists())
        self.assertTrue((self.state / OLD).exists())
        calls = (self.state / 'calls').read_text()
        self.assertNotIn('unload', calls)
        self.assertNotIn('load -w', calls)

    def test_manual_install_after_deferred_self_migration_removes_old_job(self):
        self.old_installed(running=True)
        self.run_install()
        (self.state / f'pid-{OLD}').unlink()
        self.run_install()
        self.assertFalse((self.state / OLD).exists())
        self.assertTrue((self.state / NEW).exists())

    def test_uninstall_removes_deferred_job_without_plist(self):
        self.old_installed(running=True)
        self.run_install()
        (self.state / f'pid-{OLD}').unlink()
        subprocess.run(['/bin/bash', str(REPO / 'scheduler/uninstall.sh')], env=self.env, check=True, capture_output=True)
        self.assertFalse((self.state / OLD).exists())
        self.assertFalse((self.state / NEW).exists())

    def test_linux_migrate_timer(self):
        self.env['FAKE_OS'] = 'Linux'
        self.write('systemctl', '#!/bin/bash\nprintf "%s\\n" "$*" >> "$FAKE_STATE/systemctl"\n')
        unit = self.home / '.config/systemd/user'
        unit.mkdir(parents=True)
        for suffix in ('timer', 'service'):
            (unit / f'claude-code-global-auto-update.{suffix}').write_text('old')
        self.run_install()
        self.assertFalse((unit / 'claude-code-global-auto-update.timer').exists())
        for suffix in ('timer', 'service'):
            text = (unit / f'coding-agent-config-auto-update.{suffix}').read_text()
            for line in text.splitlines():
                self.assertTrue(not line or line.startswith('[') or '=' in line, line)
        calls = (self.state / 'systemctl').read_text()
        self.assertIn('disable --now claude-code-global-auto-update.timer', calls)
        self.assertIn('enable --now coding-agent-config-auto-update.timer', calls)


if __name__ == '__main__':
    unittest.main()
