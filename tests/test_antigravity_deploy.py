"""Antigravity 部署函数级沙盘：只经 CCG_INSTALL_LIB_ONLY 入口加载函数，全部副作用隔离在临时 HOME。

不跑安装主流程：AGENTS.md 要求安装测试先用 `CCG_INSTALL_LIB_ONLY=1` 隔离入口。
运行：uv run --frozen pytest tests/test_antigravity_deploy.py
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIB_ONLY = 'source "$1/install.sh"; deploy_shared; deploy_antigravity'


class AntigravityDeployTest(unittest.TestCase):
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
                     'scripts', 'skills', 'hooks', 'templates', 'playbooks', 'agents'):
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
        return subprocess.run(['bash', '-c', snippet, 'ag-deploy-test', str(self.repo)],
                              env=env, check=True, capture_output=True, text=True)

    def deploy(self, **extra):
        return self.run_lib(LIB_ONLY, **extra)

    def config_dir(self):
        return self.home / '.gemini' / 'config'

    def test_skips_without_antigravity_dirs(self):
        self.deploy()
        self.assertFalse((self.home / '.gemini').exists())

    def test_deploys_when_antigravity_app_dir_present(self):
        (self.home / '.gemini' / 'antigravity').mkdir(parents=True)
        self.deploy()
        rules = self.config_dir() / 'AGENTS.md'
        skill = self.config_dir() / 'skills' / 'commit'
        self.assertTrue(rules.is_symlink())
        self.assertEqual(Path(os.readlink(rules)), self.repo / 'GLOBAL_AGENTS.md')
        self.assertTrue(skill.is_symlink())
        self.assertEqual(Path(os.readlink(skill)), self.home / '.coding-agent' / 'skills' / 'commit')

    def test_deploys_when_antigravity_cli_dir_present(self):
        (self.home / '.gemini' / 'antigravity-cli').mkdir(parents=True)
        self.deploy()
        self.assertTrue((self.config_dir() / 'AGENTS.md').is_symlink())
        self.assertTrue((self.config_dir() / 'skills' / 'start').is_symlink())

    def test_deploys_when_config_dir_present(self):
        self.config_dir().mkdir(parents=True)
        self.deploy()
        self.assertTrue((self.config_dir() / 'AGENTS.md').is_symlink())
        self.assertTrue((self.config_dir() / 'skills' / 'review-loop').is_symlink())

    def test_second_run_keeps_same_dentry(self):
        (self.home / '.gemini' / 'antigravity').mkdir(parents=True)
        self.deploy()
        rules = self.config_dir() / 'AGENTS.md'
        first = os.lstat(rules)
        self.deploy()
        second = os.lstat(rules)
        self.assertEqual(first.st_ino, second.st_ino)
        self.assertEqual(first.st_ctime_ns, second.st_ctime_ns)

    def test_preserves_user_rules_as_backup_and_third_party_skills(self):
        cfg = self.config_dir()
        cfg.mkdir(parents=True)
        (cfg / 'AGENTS.md').write_text('my custom rules\n')
        third_party = cfg / 'skills' / 'start'
        third_party.mkdir(parents=True)
        (third_party / 'SKILL.md').write_text('third-party skill\n')

        self.deploy()

        backup = cfg / 'AGENTS.md.bak'
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(), 'my custom rules\n')
        self.assertTrue((cfg / 'AGENTS.md').is_symlink())
        self.assertFalse(third_party.is_symlink())
        self.assertEqual((third_party / 'SKILL.md').read_text(), 'third-party skill\n')
        self.assertTrue((cfg / 'skills' / 'commit').is_symlink())

    def test_custom_config_and_home_overrides(self):
        ag_home = self.root / 'custom-ag'
        ag_home.mkdir()
        custom_cfg = self.root / 'custom-config'
        self.deploy(ANTIGRAVITY_HOME=str(ag_home), ANTIGRAVITY_CONFIG_HOME=str(custom_cfg))
        self.assertTrue((custom_cfg / 'AGENTS.md').is_symlink())
        self.assertTrue((custom_cfg / 'skills' / 'commit').is_symlink())
        self.assertFalse((self.home / '.gemini').exists())


if __name__ == '__main__':
    unittest.main()
