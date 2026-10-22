"""安装迁移沙盘：全部 HOME、Git 配置与调度器副作用隔离。"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import tomllib

REPO = Path(__file__).resolve().parents[2]


class InstallMigrationTest(unittest.TestCase):
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
                    'XDG_CONFIG_HOME': str(self.home / '.config'), 'LC_ALL': 'C'}

    def install(self):
        subprocess.run(['bash', str(self.repo / 'install.sh')], env=self.env,
                       check=True, capture_output=True, text=True)

    def test_fresh_codex_without_claude(self):
        self.install()
        self.assertFalse((self.home / '.claude').exists())
        for name in ('scripts', 'templates', 'skills', 'playbooks', 'hooks', 'agents', 'global-repo'):
            self.assertTrue((self.home / '.coding-agent' / name).is_symlink(), name)
        self.assertTrue((self.home / '.agents/skills/start').is_symlink())
        self.assertTrue((self.home / '.codex/AGENTS.md').is_symlink())
        config = tomllib.loads((self.home / '.codex/config.toml').read_text())
        handler = config['hooks']['PostToolUse'][0]['hooks'][0]
        self.assertEqual(handler['type'], 'command')
        self.assertIn('.coding-agent/hooks/', handler['command'])

    def test_custom_codex_home_and_third_party_skill(self):
        self.env['CODEX_HOME'] = str(self.home / 'custom-codex')
        legacy = self.home / 'custom-codex/skills'
        legacy.mkdir(parents=True)
        (legacy / 'start').symlink_to(self.repo / 'skills/start')
        third = legacy / 'other'
        third.mkdir()
        self.install()
        self.assertFalse((legacy / 'start').exists())
        self.assertTrue(third.is_dir())
        self.assertTrue((self.home / 'custom-codex/AGENTS.md').is_symlink())

    def test_reinstall_after_source_checkout_rename(self):
        self.install()
        old = self.repo
        self.repo = self.root / 'coding-agent-config'
        old.rename(self.repo)
        self.install()
        skill = self.home / '.agents/skills/start'
        self.assertTrue(skill.is_dir(), str(skill.readlink()))
        self.assertTrue(skill.samefile(self.repo / 'skills/start'))

    def test_migrate_renamed_legacy_install_without_registry(self):
        agent = self.home / '.codex'
        (agent / 'skills').mkdir(parents=True)
        (agent / 'scripts').mkdir()
        (agent / 'global-repo').symlink_to(self.repo)
        (agent / 'AGENTS.md').symlink_to(self.repo / 'GLOBAL_AGENTS.md')
        (agent / 'skills/start').symlink_to(self.repo / 'skills/start')
        (agent / 'scripts/platform_issue.py').symlink_to(self.repo / 'scripts/platform_issue.py')
        old = self.repo
        self.repo = self.root / 'coding-agent-config'
        old.rename(self.repo)
        self.install()
        self.assertFalse((agent / 'skills/start').is_symlink())
        self.assertTrue((self.home / '.agents/skills/start').is_dir())
        self.assertTrue((agent / 'scripts/platform_issue.py').is_file())
        self.assertTrue((agent / 'global-repo').samefile(self.repo))

    def test_linked_worktree_cannot_deploy_global_links(self):
        def git(*args):
            subprocess.run(['git', '-C', str(self.repo), *args], env=self.env,
                           check=True, capture_output=True)
        git('init')
        git('add', 'install.sh')
        git('-c', 'user.name=Sandbox', '-c', 'user.email=sandbox@example.invalid',
            'commit', '-m', 'fixture')
        linked = self.root / 'linked'
        git('worktree', 'add', '-b', 'sandbox', str(linked))
        result = subprocess.run(['bash', str(linked / 'install.sh')], env=self.env,
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / '.coding-agent').exists())

    def test_auto_update_locates_repo_through_shared_directory_link(self):
        self.install()
        env = dict(self.env, GIT_AUTHOR_NAME='Sandbox',
                   GIT_AUTHOR_EMAIL='sandbox@example.invalid', GIT_COMMITTER_NAME='Sandbox',
                   GIT_COMMITTER_EMAIL='sandbox@example.invalid')
        for args in (['init', '-b', 'master'], ['add', 'install.sh'], ['commit', '-m', 'fixture']):
            subprocess.run(['git', '-C', str(self.repo), *args], env=env,
                           capture_output=True, check=True)
        subprocess.run(['bash', str(self.home / '.coding-agent/scripts/auto-update.sh')],
                       env=env, check=True, capture_output=True)
        log = (self.home / '.coding-agent/logs/auto-update.log').read_text()
        self.assertIn('skip: no origin remote configured', log)

    def test_third_party_skill_name_collision_is_preserved(self):
        custom = self.home / '.agents/skills/start'
        custom.mkdir(parents=True)
        (custom / 'SKILL.md').write_text('third-party')
        self.install()
        self.assertFalse(custom.is_symlink())
        self.assertEqual((custom / 'SKILL.md').read_text(), 'third-party')

    def test_migrate_preferences_without_losing_user_values(self):
        old = self.home / '.claude-code-global/config.env'
        old.parent.mkdir()
        old.write_text('GIT_INIT_DEFAULT_BRANCH=main\nCUSTOM=keep\n')
        self.install()
        new = self.home / '.coding-agent/config.env'
        self.assertEqual(old.read_text(), new.read_text())
        new.write_text('GIT_INIT_DEFAULT_BRANCH=\nNEW=keep\n')
        self.install()
        self.assertIn('GIT_INIT_DEFAULT_BRANCH=\n', new.read_text())
        self.assertIn('CUSTOM=keep', new.read_text())
        self.assertTrue(old.exists())

    def test_preserve_explicit_document_budget(self):
        dst = self.home / '.codex/config.toml'
        dst.parent.mkdir()
        dst.write_text('project_doc_max_bytes = 12345\n[projects]\n')
        self.install()
        self.assertEqual(tomllib.loads(dst.read_text())['project_doc_max_bytes'], 12345)

    def test_replace_old_managed_hooks_preserve_user_config(self):
        dst = self.home / '.codex/config.toml'
        dst.parent.mkdir()
        dst.write_text('model = "user-model"\n# >>> claude-code-global managed >>>\n'
                       '[[hooks.PostToolUse]]\nmatcher="Wrong"\ncommand="old"\n'
                       '# <<< claude-code-global managed <<<\n')
        self.install()
        parsed = tomllib.loads(dst.read_text())
        self.assertEqual(parsed['model'], 'user-model')
        self.assertEqual(parsed['project_doc_max_bytes'], 65536)
        self.assertEqual(len(parsed['hooks']['PostToolUse']), 1)
        self.assertIn('hooks', parsed['hooks']['PostToolUse'][0])
        before = dst.read_text()
        self.install()
        self.assertEqual(before, dst.read_text())


if __name__ == '__main__':
    unittest.main()
