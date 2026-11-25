"""DSH 部署函数级沙盘：只经 CCG_INSTALL_LIB_ONLY 入口加载函数，全部副作用隔离在临时 HOME。

不跑安装主流程：AGENTS.md 要求安装测试先用 `CCG_INSTALL_LIB_ONLY=1` 隔离入口。
运行：uv run --frozen pytest tests/test_dsh_deploy.py
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIB_ONLY = 'source "$1/install.sh"; deploy_dsh'
SOURCE_ONLY = 'source "$1/install.sh"'


class DshDeployTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        for name in ('install.sh', 'GLOBAL_AGENTS.md', 'codex.config.base.toml',
                     'settings.base.json', 'user.config.example.env', 'uv.config.base.toml',
                     'scripts', 'skills', 'templates', 'playbooks', 'agents'):
            src = REPO / name
            if src.is_dir():
                shutil.copytree(src, self.repo / name)
            else:
                shutil.copy2(src, self.repo / name)
        self.env = {'HOME': str(self.home), 'PATH': os.environ['PATH'],
                    'GIT_CONFIG_GLOBAL': str(self.home / '.gitconfig'),
                    'XDG_CONFIG_HOME': str(self.home / '.config'), 'LC_ALL': 'C',
                    'CCG_INSTALL_LIB_ONLY': '1'}

    def run_lib(self, snippet, **extra):
        env = dict(self.env)
        env.update(extra)
        return subprocess.run(['bash', '-c', snippet, 'dsh-deploy-test', str(self.repo)],
                              env=env, check=True, capture_output=True, text=True)

    def deploy(self, **extra):
        return self.run_lib(LIB_ONLY, **extra)

    def dsh_link(self):
        return self.home / '.agents' / 'AGENTS.md'

    def test_lib_only_entry_skips_main_flow(self):
        out = self.run_lib(SOURCE_ONLY)
        self.assertEqual(out.stdout, '')
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.coding-agent').exists())

    def test_skips_without_dsh_home(self):
        self.deploy()
        self.assertFalse(os.path.lexists(self.dsh_link()))

    def test_skips_when_configured_dsh_home_missing(self):
        self.deploy(DSH_HOME=str(self.root / 'no-dsh'))
        self.assertFalse(os.path.lexists(self.dsh_link()))

    def test_links_global_rules_when_dsh_present(self):
        (self.home / '.dsh').mkdir()
        self.deploy()
        self.assertTrue(self.dsh_link().is_symlink())
        self.assertEqual(Path(os.readlink(self.dsh_link())), self.repo / 'GLOBAL_AGENTS.md')

    def test_second_run_keeps_same_dentry(self):
        (self.home / '.dsh').mkdir()
        self.deploy()
        first = os.lstat(self.dsh_link())
        self.deploy()
        second = os.lstat(self.dsh_link())
        self.assertEqual(first.st_ino, second.st_ino)
        self.assertEqual(first.st_ctime_ns, second.st_ctime_ns)

    def test_preserves_user_file_as_backup(self):
        agents = self.home / '.agents'
        agents.mkdir()
        (agents / 'AGENTS.md').write_text('my own rules\n')
        (self.home / '.dsh').mkdir()
        self.deploy()
        backup = agents / 'AGENTS.md.bak'
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(), 'my own rules\n')
        self.assertTrue(self.dsh_link().is_symlink())

    def test_custom_agents_home_deploys_rules_and_skills(self):
        (self.home / '.dsh').mkdir()
        custom = self.root / 'custom-agents'
        first = self.deploy(DSH_AGENTS_HOME=str(custom))
        out = self.run_lib('source "$1/install.sh"; deploy_shared; deploy_dsh',
                           DSH_AGENTS_HOME=str(custom))
        self.assertTrue((custom / 'AGENTS.md').is_symlink())
        self.assertTrue((custom / 'skills' / 'commit').is_symlink())
        self.assertEqual(Path(os.readlink(custom / 'skills' / 'commit')),
                         self.home / '.coding-agent' / 'skills' / 'commit')
        self.assertFalse(os.path.lexists(custom / 'skills' / 'devtree'))
        self.assertFalse(os.path.lexists(self.dsh_link()))
        self.assertFalse((self.home / '.agents' / 'skills').exists())
        self.assertIn('已跳过 AGENTS.md', first.stdout + out.stdout)


if __name__ == '__main__':
    unittest.main()
