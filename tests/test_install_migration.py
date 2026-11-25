"""安装迁移沙盘：全部 HOME、Git 配置与调度器副作用隔离。"""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import tomllib

REPO = Path(__file__).resolve().parents[1]


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
                     'scripts', 'skills', 'templates', 'playbooks', 'agents'):
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
        for name in ('scripts', 'templates', 'skills', 'playbooks', 'agents', 'global-repo'):
            self.assertTrue((self.home / '.coding-agent' / name).is_symlink(), name)
        self.assertFalse(os.path.lexists(self.home / '.coding-agent/hooks'))
        self.assertTrue((self.home / '.agents/skills/start').is_symlink())
        self.assertFalse(os.path.lexists(self.home / '.agents/skills/devtree'))
        self.assertTrue((self.repo / 'skills/devtree/SKILL.md').is_file())
        self.assertTrue((self.home / '.codex/AGENTS.md').is_symlink())
        config = tomllib.loads((self.home / '.codex/config.toml').read_text())
        self.assertNotIn('hooks', config)
        self.assertEqual(config['project_doc_max_bytes'], 65536)

    def test_remove_legacy_json_hooks_preserve_custom_handlers(self):
        for marker in ('claude-code-global', 'coding-agent-config'):
            with self.subTest(marker=marker):
                agent = self.home / 'custom-codex'
                agent.mkdir(exist_ok=True)
                self.env['CODEX_HOME'] = str(agent)
                dst = agent / 'hooks.json'
                custom = {'type': 'command', 'command': 'echo custom'}
                group = {'matcher': 'Edit|MultiEdit|Write', 'hooks': [
                    {'type': 'command', 'command': f'bash old # @{marker}:fix-after-edit'},
                    custom]}
                original = {'description': 'keep', 'hooks': {'PostToolUse': [group]}}
                dst.write_text(json.dumps(original))
                self.install()
                result = json.loads(dst.read_text())
                self.assertEqual(result, {'description': 'keep', 'hooks': {
                    'PostToolUse': [{'matcher': group['matcher'], 'hooks': [custom]}]}})
                backups = list(agent.glob('hooks.json.bak.*'))
                self.assertTrue(backups)
                self.assertTrue(any(json.loads(p.read_text()) == original for p in backups))
                before = dst.read_bytes()
                self.install()
                self.assertEqual(before, dst.read_bytes())
                self.assertEqual(backups, list(agent.glob('hooks.json.bak.*')))

    def test_remove_old_flat_toml_hook_without_losing_user_tables(self):
        dst = self.home / '.codex/config.toml'
        dst.parent.mkdir()
        dst.write_text('model = "user-model"\n'
                       '[[hooks.PostToolUse]]\nmatcher = "Edit|MultiEdit|Write"\n'
                       'command = "bash $HOME/.codex/hooks/fix-after-edit.sh"\ntimeout = 30\n'
                       '[desktop]\nfollowUpQueueMode = "steer"\n'
                       '[[hooks.PostToolUse]]\nmatcher = "Bash"\n'
                       '[[hooks.PostToolUse.hooks]]\ntype = "command"\ncommand = "echo custom"\n')
        self.install()
        parsed = tomllib.loads(dst.read_text())
        self.assertEqual(parsed['model'], 'user-model')
        self.assertEqual(parsed['desktop']['followUpQueueMode'], 'steer')
        groups = parsed['hooks']['PostToolUse']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['hooks'][0]['command'], 'echo custom')
        before = dst.read_bytes()
        self.install()
        self.assertEqual(before, dst.read_bytes())

    def test_json_only_managed_group_removed_other_events_and_empty_groups_kept(self):
        dst = self.home / '.codex/hooks.json'
        dst.parent.mkdir()
        custom = {'matcher': 'Bash', 'hooks': []}
        other = [{'hooks': [{'type': 'command', 'command': 'echo stop'}]}]
        dst.write_text(json.dumps({'hooks': {'Stop': other, 'PostToolUse': [custom, {
            'matcher': 'Edit|MultiEdit|Write', 'hooks': [{
                'type': 'command', 'command': 'bash old # @claude-code-global:fix-after-edit'}]}]}}))
        self.install()
        self.assertEqual(json.loads(dst.read_text()), {
            'hooks': {'Stop': other, 'PostToolUse': [custom]}})

    def test_unmarked_user_json_hook_and_custom_flat_toml_preserved(self):
        agent = self.home / '.codex'
        agent.mkdir()
        custom = {'hooks': {'PostToolUse': [{'matcher': 'Edit|MultiEdit|Write', 'hooks': [
            {'type': 'command', 'command': 'bash $HOME/.codex/hooks/fix-after-edit.sh'}]}]}}
        dst = agent / 'hooks.json'
        dst.write_text(json.dumps(custom))
        (agent / 'config.toml').write_text(
            '[[hooks.PostToolUse]]\nmatcher = "Edit|MultiEdit|Write"\n'
            'command = "bash $HOME/.codex/hooks/fix-after-edit.sh"\ntimeout = 60\n')
        self.install()
        self.assertEqual(json.loads(dst.read_text()), custom)
        groups = tomllib.loads((agent / 'config.toml').read_text())['hooks']['PostToolUse']
        self.assertEqual(groups[0]['timeout'], 60)
        self.assertEqual(len(groups), 1)

    def test_malformed_legacy_json_aborts_without_overwriting(self):
        dst = self.home / '.codex/hooks.json'
        dst.parent.mkdir()
        dst.write_text('{ broken')
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assertEqual(dst.read_text(), '{ broken')

    def test_old_flat_hook_inside_managed_markers_keeps_following_user_table(self):
        dst = self.home / '.codex/config.toml'
        dst.parent.mkdir()
        dst.write_text('model = "user-model"\n# >>> claude-code-global managed >>>\n'
                       '[[hooks.PostToolUse]]\nmatcher = "Edit|MultiEdit|Write"\n'
                       'command = "bash $HOME/.codex/hooks/fix-after-edit.sh"\ntimeout = 30\n'
                       '# <<< claude-code-global managed <<<\n'
                       '[desktop]\nfollowUpQueueMode = "steer"\n')
        self.install()
        parsed = tomllib.loads(dst.read_text())
        self.assertEqual(parsed['desktop']['followUpQueueMode'], 'steer')
        self.assertNotIn('hooks', parsed)
        backups = list((self.home / '.codex').glob('config.toml.bak.*'))
        self.assertTrue(backups)
        before = dst.read_text()
        self.install()
        self.assertEqual(before, dst.read_text())
        self.assertEqual(backups, list((self.home / '.codex').glob('config.toml.bak.*')))

    def test_legacy_flat_group_with_custom_child_table_is_preserved(self):
        dst = self.home / '.codex/config.toml'
        dst.parent.mkdir()
        original = ('[[hooks.PostToolUse]]\nmatcher = "Edit|MultiEdit|Write"\n'
                    'command = "bash $HOME/.codex/hooks/fix-after-edit.sh"\ntimeout = 30\n'
                    '[[hooks.PostToolUse.hooks]]\ntype = "command"\ncommand = "echo custom"\n')
        expected = tomllib.loads(original)['hooks']['PostToolUse'][0]
        dst.write_text(original)
        self.install()
        groups = tomllib.loads(dst.read_text())['hooks']['PostToolUse']
        self.assertEqual(groups, [expected])

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

    def test_remove_old_managed_hooks_block_preserve_user_config(self):
        for marker in ('claude-code-global', 'coding-agent-config'):
            with self.subTest(marker=marker):
                agent = self.home / f'codex-{marker}'
                agent.mkdir(exist_ok=True)
                self.env['CODEX_HOME'] = str(agent)
                dst = agent / 'config.toml'
                dst.write_text(
                    'model = "user-model"\n'
                    '[[hooks.PostToolUse]]\nmatcher = "Bash"\n'
                    '[[hooks.PostToolUse.hooks]]\ntype = "command"\ncommand = "echo custom"\n'
                    f'# >>> {marker} managed >>>\n'
                    '[[hooks.PostToolUse]]\nmatcher = "^apply_patch$"\n'
                    '[[hooks.PostToolUse.hooks]]\ntype = "command"\n'
                    f'command = \'bash "$HOME/.coding-agent/hooks/fix-after-edit.sh" # @{marker}:fix-after-edit\'\n'
                    'timeout = 30\n'
                    f'# <<< {marker} managed <<<\n'
                )
                self.install()
                parsed = tomllib.loads(dst.read_text())
                self.assertEqual(parsed['model'], 'user-model')
                self.assertEqual(parsed['project_doc_max_bytes'], 65536)
                self.assertEqual(len(parsed['hooks']['PostToolUse']), 1)
                self.assertEqual(parsed['hooks']['PostToolUse'][0]['hooks'][0]['command'], 'echo custom')
                backups = list(agent.glob('config.toml.bak.*'))
                self.assertTrue(backups)
                before = dst.read_text()
                self.install()
                self.assertEqual(before, dst.read_text())
                self.assertEqual(backups, list(agent.glob('config.toml.bak.*')))

    def test_claude_fresh_and_upgrade_retires_managed_hook_preserves_custom(self):
        claude = self.home / '.claude'
        claude.mkdir()
        self.install()
        settings = json.loads((claude / 'settings.json').read_text())
        self.assertNotIn('hooks', settings)
        self.assertTrue((claude / 'skills/start').is_symlink())
        self.assertFalse(os.path.lexists(claude / 'skills/devtree'))

        # Upgrade with managed hook only -> hooks key removed cleanly and idempotently
        for marker in ('claude-code-global', 'coding-agent-config'):
            with self.subTest(case='managed-only', marker=marker):
                dst = claude / 'settings.json'
                dst.write_text(json.dumps({
                    'hooks': {'PostToolUse': [{'matcher': 'Edit|MultiEdit|Write', 'hooks': [{
                        'type': 'command',
                        'command': f'bash $HOME/.coding-agent/hooks/fix-after-edit.sh # @{marker}:fix-after-edit',
                        'timeout': 30,
                    }]}]},
                    'permissions': {'allow': ['Skill(*)'], 'deny': []},
                }))
                self.install()
                upgraded = json.loads(dst.read_text())
                self.assertNotIn('hooks', upgraded)
                backups = list(claude.glob('settings.json.bak.*'))
                self.assertTrue(backups)
                before = dst.read_bytes()
                self.install()
                self.assertEqual(before, dst.read_bytes())
                self.assertEqual(backups, list(claude.glob('settings.json.bak.*')))

        # Upgrade with managed hook + custom hook -> only custom hook survives
        dst = claude / 'settings.json'
        custom_hook = {'type': 'command', 'command': 'echo user-hook'}
        dst.write_text(json.dumps({
            'hooks': {'PostToolUse': [{'matcher': 'Edit|MultiEdit|Write', 'hooks': [
                {'type': 'command', 'command': 'bash $HOME/.coding-agent/hooks/fix-after-edit.sh # @coding-agent-config:fix-after-edit'},
                custom_hook,
            ]}]},
            'permissions': {'allow': ['Skill(*)'], 'deny': []},
        }))
        self.install()
        upgraded = json.loads(dst.read_text())
        self.assertEqual(upgraded['hooks'], {'PostToolUse': [{'matcher': 'Edit|MultiEdit|Write', 'hooks': [custom_hook]}]})
        before = dst.read_bytes()
        self.install()
        self.assertEqual(before, dst.read_bytes())

    def test_upgrade_cleans_legacy_hooks_symlinks_and_preserves_user_hooks(self):
        shared = self.home / '.coding-agent'
        shared.mkdir()
        (shared / 'hooks').symlink_to(self.repo / 'hooks')
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'hooks').symlink_to(self.repo / 'hooks')
        claude_hooks = self.home / '.claude/hooks'
        claude_hooks.mkdir(parents=True)
        (claude_hooks / 'fix-after-edit.sh').symlink_to(shared / 'hooks/fix-after-edit.sh')
        custom_script = claude_hooks / 'custom.sh'
        custom_script.write_text('#!/bin/bash\necho keep\n')

        self.install()

        self.assertFalse(os.path.lexists(shared / 'hooks'))
        self.assertFalse(os.path.lexists(codex / 'hooks'))
        self.assertFalse(os.path.lexists(claude_hooks / 'fix-after-edit.sh'))
        self.assertTrue(custom_script.is_file())
        self.assertEqual(custom_script.read_text(), '#!/bin/bash\necho keep\n')

        # User-created real directory at ~/.coding-agent/hooks is never removed
        (shared / 'hooks').mkdir()
        (shared / 'hooks/mine.sh').write_text('keep')
        self.install()
        self.assertTrue((shared / 'hooks/mine.sh').is_file())

    def test_relative_hooks_symlinks_are_preserved_regardless_of_cwd(self):
        codex = self.home / '.codex'
        codex.mkdir()
        (self.home / 'hooks').mkdir()
        (codex / 'hooks').symlink_to('../hooks')
        claude_hooks = self.home / '.claude/hooks'
        claude_hooks.mkdir(parents=True)
        (claude_hooks / 'fix-after-edit.sh').symlink_to('./hooks/fix-after-edit.sh')

        subdir = self.repo / 'scripts'
        subprocess.run(['bash', '../install.sh'], cwd=subdir, env=self.env,
                       check=True, capture_output=True, text=True)
        self.assertTrue((codex / 'hooks').is_symlink())
        self.assertEqual(os.readlink(codex / 'hooks'), '../hooks')

        subprocess.run(['bash', 'install.sh'], cwd=self.repo, env=self.env,
                       check=True, capture_output=True, text=True)
        self.assertTrue((claude_hooks / 'fix-after-edit.sh').is_symlink())
        self.assertEqual(os.readlink(claude_hooks / 'fix-after-edit.sh'), './hooks/fix-after-edit.sh')


if __name__ == '__main__':
    unittest.main()
