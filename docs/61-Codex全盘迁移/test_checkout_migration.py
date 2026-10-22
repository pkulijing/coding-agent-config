"""验证目录改名和 linked worktree 搬迁保留用户未提交内容。"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class CheckoutMigrationTest(unittest.TestCase):
    def test_move_and_rename_preserve_git_and_untracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / 'home'
            home.mkdir()
            old = root / 'old repo'
            old.mkdir()
            env = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(home / '.gitconfig')}
            def git(cwd, *args):
                return subprocess.run(['git', '-C', str(cwd), *args], env=env, check=True, text=True, capture_output=True).stdout
            git(old, 'init', '-b', 'master')
            (old / 'tracked').write_text('base')
            git(old, 'add', 'tracked')
            git(old, '-c', 'user.name=Sandbox', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
            legacy = old / '.claude/worktrees/round1'
            git(old, 'worktree', 'add', '-b', 'round1', str(legacy))
            (legacy / 'tracked').write_text('dirty')
            (legacy / 'untracked').write_text('keep')
            target = old / '.worktrees/round1'
            target.parent.mkdir()
            git(old, 'worktree', 'move', str(legacy), str(target))
            new = root / 'coding-agent-config'
            old.rename(new)
            relocated = new / '.worktrees/round1'
            git(new, 'worktree', 'repair', str(relocated))
            self.assertEqual(git(relocated, 'branch', '--show-current').strip(), 'round1')
            self.assertEqual((relocated / 'tracked').read_text(), 'dirty')
            self.assertEqual((relocated / 'untracked').read_text(), 'keep')
            self.assertIn(str(relocated), git(new, 'worktree', 'list', '--porcelain'))
            self.assertIn('M tracked', git(relocated, 'status', '--short'))


if __name__ == '__main__':
    unittest.main()
