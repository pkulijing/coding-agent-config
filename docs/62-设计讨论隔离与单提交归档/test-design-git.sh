#!/usr/bin/env bash
# 验证 design 规则所依赖的 Git 操作；不是自然语言技能的自动执行器。
set -euo pipefail
trap 'printf "FAIL: line %s\n" "${LINENO}" >&2' ERR
sandbox=$(mktemp -d "${TMPDIR:-/tmp}/design-git.XXXXXX")
trap 'rm -rf "${sandbox}"' EXIT
mkdir -p "${sandbox}/home"
# 从独立 HOME 重启，防止读取用户配置或凭据；所有远端都是本地 bare 仓库。
if [ "${DESIGN_TEST_ISOLATED:-0}" != 1 ]; then
    env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE \
        HOME="${sandbox}/home" DESIGN_TEST_ISOLATED=1 \
        GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
        GIT_AUTHOR_NAME=Test GIT_AUTHOR_EMAIL=test@example.invalid \
        GIT_COMMITTER_NAME=Test GIT_COMMITTER_EMAIL=test@example.invalid \
        GIT_AUTHOR_DATE=2026-01-01T00:00:00Z \
        GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
        LC_ALL=C LANGUAGE= bash "$0"
    exit 0
fi
repo="${sandbox}/repo"
wt="${sandbox}/topic"
other_wt="${sandbox}/other"
remote="${sandbox}/remote.git"
topic='docs/design/主题'
branch=codex/design-topic
checks=0
ok() { checks=$((checks + 1)); printf 'PASS %s\n' "$1"; }
git init -q --bare "${remote}"
git init -q -b main "${repo}"
git -C "${repo}" config core.hooksPath /dev/null
printf 'base\n' > "${repo}/base"
printf 'stage\n' > "${repo}/staged"
git -C "${repo}" add base staged
git -C "${repo}" commit -qm base
base_sha=$(git -C "${repo}" rev-parse HEAD)
git -C "${repo}" remote add origin "${remote}"
git -C "${repo}" push -q origin main

# 1. 主树三类脏文件与 index 原样保留。
printf 'dirty\n' >> "${repo}/base"
printf 'staged change\n' >> "${repo}/staged"
git -C "${repo}" add staged
printf 'untracked\n' > "${repo}/loose"
git -C "${repo}" status --porcelain -z > "${sandbox}/status-before"
git -C "${repo}" diff --binary > "${sandbox}/diff-before"
git -C "${repo}" diff --cached --binary > "${sandbox}/index-before"
git -C "${repo}" worktree add -q --no-track -b "${branch}" "${wt}" main
mkdir -p "${wt}/${topic}"
printf 'v1\n' > "${wt}/${topic}/DESIGN.md"
printf 'discussion 1\n' > "${wt}/${topic}/DISCUSSION.md"
git -C "${wt}" add -- "${topic}/DESIGN.md" "${topic}/DISCUSSION.md"
git -C "${wt}" commit -qm 'docs(design): 主题方案' -m "Design-Topic: ${topic}"
for state in v2 finalized shelved; do
    printf '%s\n' "${state}" > "${wt}/${topic}/DESIGN.md"
    printf '%s\n' "${state}" >> "${wt}/${topic}/DISCUSSION.md"
    git -C "${wt}" add -- "${topic}/DESIGN.md" "${topic}/DISCUSSION.md"
    git -C "${wt}" commit -q --amend --no-edit
    test "$(git -C "${wt}" rev-list --count "${base_sha}..HEAD")" = 1
done
git -C "${repo}" status --porcelain -z > "${sandbox}/status-after"
git -C "${repo}" diff --binary > "${sandbox}/diff-after"
git -C "${repo}" diff --cached --binary > "${sandbox}/index-after"
cmp "${sandbox}/status-before" "${sandbox}/status-after"
cmp "${sandbox}/diff-before" "${sandbox}/diff-after"
cmp "${sandbox}/index-before" "${sandbox}/index-after"
test "$(cat "${repo}/loose")" = untracked
test ! -e "${repo}/${topic}"
ok '多次 amend 保持单提交，主树三类脏区与 index 不变'

# 2. 两个主题交替、跨会话恢复：候选分支从 Git 路径事实验证。
git -C "${repo}" worktree add -q --no-track -b codex/design-other "${other_wt}" main
mkdir -p "${other_wt}/docs/design/另一主题"
printf 'other\n' > "${other_wt}/docs/design/另一主题/DESIGN.md"
git -C "${other_wt}" add docs/design
git -C "${other_wt}" commit -qm 'docs(design): 另一主题'
other_sha=$(git -C "${other_wt}" rev-parse HEAD)
printf 'resumed\n' >> "${wt}/${topic}/DISCUSSION.md"
git -C "${wt}" add -- "${topic}/DISCUSSION.md"
git -C "${wt}" commit -q --amend --no-edit
test "$(git -C "${other_wt}" rev-parse HEAD)" = "${other_sha}"
test ! -e "${wt}/docs/design/另一主题"
test ! -e "${other_wt}/${topic}"
archive=$(git -C "${wt}" rev-parse HEAD)
git -C "${repo}" worktree remove "${wt}"
git -C "${repo}" cat-file -e "${branch}:${topic}/DESIGN.md"
git -C "${repo}" worktree add -q "${wt}" "${branch}"
test "$(git -C "${wt}" rev-parse HEAD)" = "${archive}"
ok '交替主题互不污染；工作树移除后由原分支恢复'

# 3. index 夹带可由完整清单检出；核对不能清空或代提交夹带项。
printf 'unrelated\n' > "${wt}/unrelated"
git -C "${wt}" add unrelated
staged_paths=$(git -C "${wt}" diff --cached --name-only)
test "${staged_paths}" = unrelated
test "$(git -C "${wt}" rev-parse HEAD)" = "${archive}"
git -C "${wt}" restore --staged unrelated
rm "${wt}/unrelated"
ok '可检出非主题暂存项，归档提交保持不变'

# 4. 已发布主题 amend 后普通 push 拒绝；lease 阻止覆盖并发远端更新。
git -C "${wt}" push -q origin "${branch}"
lease_sha=$(git -C "${wt}" rev-parse HEAD)
printf 'published update\n' >> "${wt}/${topic}/DISCUSSION.md"
git -C "${wt}" add -- "${topic}/DISCUSSION.md"
git -C "${wt}" commit -q --amend --no-edit
if git -C "${wt}" push origin "${branch}" > "${sandbox}/push.log" 2>&1; then
    printf 'FAIL: 普通 push 意外接受已改写分支\n' >&2; exit 1
fi
peer="${sandbox}/peer"
git clone -q --branch "${branch}" "${remote}" "${peer}"
git -C "${peer}" config core.hooksPath /dev/null
printf 'peer update\n' >> "${peer}/${topic}/DISCUSSION.md"
git -C "${peer}" add -- "${topic}/DISCUSSION.md"
git -C "${peer}" commit -qm 'docs(design): peer'
git -C "${peer}" push -q origin "${branch}"
peer_sha=$(git -C "${peer}" rev-parse HEAD)
if git -C "${wt}" push "--force-with-lease=refs/heads/${branch}:${lease_sha}" origin \
    "HEAD:refs/heads/${branch}" > "${sandbox}/lease.log" 2>&1; then
    printf 'FAIL: 过期 lease 意外覆盖远端\n' >&2; exit 1
fi
test "$(git --git-dir="${remote}" rev-parse "refs/heads/${branch}")" = "${peer_sha}"
ok '普通 push 拒绝改写；显式 SHA lease 保留他人并发更新'

# 5. 仅远端保留主题时，从 fresh clone 恢复，不另造主题。
fresh="${sandbox}/fresh"
git clone -q --single-branch --branch main "${remote}" "${fresh}"
git -C "${fresh}" config core.hooksPath /dev/null
# 默认 fetch 仍只取 main，远端有主题却不会出现在 remote-tracking 清单中。
git -C "${fresh}" fetch -q origin
test -z "$(git -C "${fresh}" for-each-ref --format='%(refname)' "refs/remotes/origin/${branch}")"
git -C "${fresh}" ls-remote --heads origin > "${sandbox}/remote-heads"
grep -qF "refs/heads/${branch}" "${sandbox}/remote-heads"
git -C "${fresh}" fetch -q origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
git -C "${fresh}" cat-file -e "origin/${branch}:${topic}/DESIGN.md"
git -C "${fresh}" config --add remote.origin.fetch "+refs/heads/${branch}:refs/remotes/origin/${branch}"
git -C "${fresh}" worktree add -q --track -b "${branch}" "${sandbox}/remote-resume" "origin/${branch}"
test "$(git -C "${sandbox}/remote-resume" rev-parse HEAD)" = "${peer_sha}"
test "$(git -C "${sandbox}/remote-resume" rev-parse --symbolic-full-name '@{upstream}')" = "refs/remotes/origin/${branch}"
ok '窄 fetch refspec 下仍能列全远端并恢复主题原文档与提交'

# 6. 旧版交错提交收敛：在临时分支重排，其他补丁和 message 保留。
legacy="${sandbox}/legacy"
git -C "${repo}" worktree add -q --no-track -b legacy "${legacy}" main
mkdir -p "${legacy}/${topic}"
printf 'old 1\n' > "${legacy}/${topic}/DESIGN.md"
git -C "${legacy}" add docs/design
git -C "${legacy}" commit -qm 'docs(design): old 1'
a1=$(git -C "${legacy}" rev-parse HEAD)
printf 'code\n' > "${legacy}/code"
git -C "${legacy}" add code
git -C "${legacy}" commit -qm 'feat: 独立开发内容' -m '保留此说明'
code_sha=$(git -C "${legacy}" rev-parse HEAD)
printf 'old 2\n' >> "${legacy}/${topic}/DESIGN.md"
git -C "${legacy}" add docs/design
git -C "${legacy}" commit -qm 'docs(design): old 2'
a2=$(git -C "${legacy}" rev-parse HEAD)
old_tree=$(git -C "${legacy}" rev-parse 'HEAD^{tree}')
git -C "${legacy}" tag backup/legacy-test
# 先验证每个被归并提交的全部路径；混合提交必须排除自动整理。
test "$(git -C "${legacy}" -c core.quotepath=false diff-tree --no-commit-id --name-only -r "${a1}")" = "${topic}/DESIGN.md"
test "$(git -C "${legacy}" -c core.quotepath=false diff-tree --no-commit-id --name-only -r "${a2}")" = "${topic}/DESIGN.md"
git -C "${legacy}" switch -qc reorganize
printf 'pick %s\npick %s\nfixup %s\n' "${code_sha}" "${a1}" "${a2}" > "${sandbox}/todo"
cat > "${sandbox}/editor" <<'EDITOR'
#!/usr/bin/env bash
set -euo pipefail
cp "${DESIGN_TEST_TODO}" "$1"
EDITOR
chmod +x "${sandbox}/editor"
DESIGN_TEST_TODO="${sandbox}/todo" GIT_SEQUENCE_EDITOR="${sandbox}/editor" \
    git -C "${legacy}" rebase -i "${base_sha}" > "${sandbox}/rebase.log" 2>&1
test "$(git -C "${legacy}" rev-parse 'HEAD^{tree}')" = "${old_tree}"
test "$(git -C "${legacy}" rev-list --count "${base_sha}..HEAD")" = 2
git -C "${legacy}" show -s --format=%B "${code_sha}" > "${sandbox}/old-message"
git -C "${legacy}" show -s --format=%B HEAD~1 > "${sandbox}/new-message"
cmp "${sandbox}/old-message" "${sandbox}/new-message"
git -C "${legacy}" show "${code_sha}" --format= --binary | git patch-id --stable > "${sandbox}/old-patch"
git -C "${legacy}" show HEAD~1 --format= --binary | git patch-id --stable > "${sandbox}/new-patch"
cmp "${sandbox}/old-patch" "${sandbox}/new-patch"
test "$(git -C "${legacy}" rev-parse legacy)" = "${a2}"
test "$(git -C "${legacy}" rev-parse backup/legacy-test)" = "${a2}"
ok '临时分支收敛交错设计提交，文件树、其他补丁和 message 不变，原引用保留'

# 7. 终态合入前主线前进，rebase 后 FF；只带入一个主题提交。
integration="${sandbox}/integration"
git -C "${repo}" worktree add -q --no-track -b integrate "${integration}" main
printf 'main advance\n' > "${integration}/advance"
git -C "${integration}" add advance
git -C "${integration}" commit -qm 'feat: 主线前进'
integrate_base=$(git -C "${integration}" rev-parse HEAD)
git -C "${wt}" tag backup/topic-before-rebase
git -C "${wt}" rebase "${integrate_base}" > "${sandbox}/terminal.log" 2>&1
git -C "${integration}" merge -q --ff-only "${branch}"
test "$(git -C "${integration}" rev-list --count "${integrate_base}..HEAD")" = 1
cmp "${wt}/${topic}/DESIGN.md" "${integration}/${topic}/DESIGN.md"
cmp "${wt}/${topic}/DISCUSSION.md" "${integration}/${topic}/DISCUSSION.md"
test -z "$(git -C "${wt}" status --porcelain)"
git -C "${wt}" merge-base --is-ancestor HEAD integrate
git -C "${repo}" worktree remove "${wt}"
git -C "${integration}" branch -d "${branch}" > "${sandbox}/delete.log" 2>&1
ok '主线前进后 rebase + FF 只合入一个主题提交，核验保全后清理'

# 8. 主题与其他路径混在一个旧提交中，必须能识别为非纯主题提交。
printf 'mixed\n' >> "${legacy}/${topic}/DESIGN.md"
printf 'mixed code\n' >> "${legacy}/code"
git -C "${legacy}" add -- "${topic}/DESIGN.md" code
git -C "${legacy}" commit -qm 'mixed'
mixed_paths=$(git -C "${legacy}" -c core.quotepath=false diff-tree --no-commit-id --name-only -r HEAD)
test "${mixed_paths}" != "${topic}/DESIGN.md"
test "$(git -C "${legacy}" diff-tree --no-commit-id --name-only -r HEAD | wc -l | tr -d ' ')" = 2
ok '混合提交的完整路径清单不能被当作纯主题提交'

# 9. 同路径冲突必须保留可恢复状态；abort 后文档与旧 tip 完整。
conflict="${sandbox}/conflict"
conflict_base="${sandbox}/conflict-base"
git -C "${repo}" worktree add -q --no-track -b conflict "${conflict}" integrate
git -C "${repo}" worktree add -q --no-track -b conflict-base "${conflict_base}" integrate
printf 'topic decision\n' > "${conflict}/${topic}/DESIGN.md"
git -C "${conflict}" add -- "${topic}/DESIGN.md"
git -C "${conflict}" commit -qm 'docs(design): 主题决策'
conflict_tip=$(git -C "${conflict}" rev-parse HEAD)
cp "${conflict}/${topic}/DESIGN.md" "${sandbox}/conflict-before"
git -C "${conflict}" tag backup/conflict-test
printf 'main decision\n' > "${conflict_base}/${topic}/DESIGN.md"
git -C "${conflict_base}" add -- "${topic}/DESIGN.md"
git -C "${conflict_base}" commit -qm 'docs(design): 主线另有决策'
if git -C "${conflict}" rebase conflict-base > "${sandbox}/conflict.log" 2>&1; then
    printf 'FAIL: 预期冲突未出现\n' >&2; exit 1
fi
test -n "$(git -C "${conflict}" ls-files -u)"
git -C "${conflict}" rebase --abort
test "$(git -C "${conflict}" rev-parse HEAD)" = "${conflict_tip}"
cmp "${conflict}/${topic}/DESIGN.md" "${sandbox}/conflict-before"
test -z "$(git -C "${conflict}" status --porcelain)"
test -d "${conflict}"
ok '合入前 rebase 冲突可 abort，旧提交、主题文档和工作树保全'
printf '通过 %s 组 Git 场景验证\n' "${checks}"
