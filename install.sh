#!/usr/bin/env bash
set -euo pipefail

# 自动检测仓库根目录
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }

# 由本仓库管理的 hook 条目，command 末尾必须带这条 bash 注释作为身份标记。
# 完整格式（严格匹配）：# @claude-code-global:<hook-name>
# 例如：bash $HOME/.claude/hooks/fix-after-edit.sh # @claude-code-global:fix-after-edit
#
# 模型：把 settings.json 里所有带此标记的 hook 条目看作"由本仓库管理的 hook 集合"，
# 用 hook-name 唯一标识。每次 install 做集合差分：
#   - 旧 ∩ 新（同名）  → 用基线版本替换（字段变化也覆盖）
#   - 旧 \ 新（仅旧有）→ 删除
#   - 新 \ 旧（仅新有）→ 新增
# 实现上等价于：剔除所有 managed 条目 → 合并基线 → 集合天然就等于基线 managed 集合。
# 用户手动添加的 hook（不带此标记）始终保留。
MANAGED_MARKER_REGEX="# *@(claude-code-global|coding-agent-config):[A-Za-z0-9_-]+"

# Codex config.toml 的托管块由一对 marker 注释包裹，整块由 install.sh 重写。
TOML_MARKER_BEGIN="# >>> coding-agent-config managed >>>"
TOML_MARKER_END="# <<< coding-agent-config managed <<<"

# 从 settings JSON 提取所有 managed hook 的 name 列表（去重排序），输出空格分隔字符串
# 用法: list_managed_names <json-file>
list_managed_names() {
    local file="$1"
    [ -f "$file" ] || { echo ""; return; }
    jq -r '
      [
        .hooks // {} | to_entries[].value[]?.hooks[]?
        | (.command // "")
        | select(test("# *@(claude-code-global|coding-agent-config):[A-Za-z0-9_-]+"))
        | capture("# *@(claude-code-global|coding-agent-config):(?<n>[A-Za-z0-9_-]+)").n
      ] | unique | join(" ")
    ' "$file" 2>/dev/null || echo ""
}

# 合并基线 JSON 配置进本地配置文件（非破坏性）
# 策略：
#   1. 计算 managed name 集合差分（旧/新 → added/removed/replaced），打印日志
#   2. 剔除 dst 中所有 .hooks.<event>[].hooks[] 中 command 匹配 MANAGED_MARKER_REGEX 的条目
#      连带空掉的 matcher 和 event 一并清理
#   3. 与基线递归合并：object 递归 / array 并集去重 / 标量仓库胜出 / null 视为未设置
#      合并后 managed 集合天然等于基线
# 用法: merge_settings <基线JSON> <目标JSON>
merge_settings() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    # 依赖 jq
    if ! command -v jq >/dev/null 2>&1; then
        warn "未找到 jq，跳过合并 ${name}（macOS 自带；其他系统请用包管理器安装）"
        return
    fi

    # 本地没有：直接复制（不是软链接，本机需自行编辑）
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        success "已创建 ${name}（从 $(basename "$src") 初始化）"
        info "  managed hooks 新增: $(list_managed_names "$src")"
        return
    fi

    # Step 1: 计算 managed name 集合差分并打印
    local old_names new_names
    old_names="$(list_managed_names "$dst")"
    new_names="$(list_managed_names "$src")"
    if [ -n "$old_names" ] || [ -n "$new_names" ]; then
        local added removed replaced
        added="$(comm -13 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        removed="$(comm -23 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        replaced="$(comm -12 <(echo "$old_names" | tr ' ' '\n' | sort -u) <(echo "$new_names" | tr ' ' '\n' | sort -u) | tr '\n' ' ' | sed 's/ *$//')"
        info "managed hooks 集合差分："
        [ -n "$replaced" ] && info "  替换（同名覆盖）: $replaced"
        [ -n "$added"    ] && info "  新增: $added"
        [ -n "$removed"  ] && info "  删除: $removed"
    fi

    # Step 2: 剔除 dst 中所有 managed 条目（command 匹配 MANAGED_MARKER_REGEX）
    local pruned
    pruned="$(jq --arg re "$MANAGED_MARKER_REGEX" '
      if .hooks then
        .hooks |= (
          with_entries(
            .value |= (
              map(.hooks |= map(select(((.command // "") | test($re)) | not)))
              | map(select((.hooks // []) | length > 0))
            )
          )
          | with_entries(select(.value | length > 0))
        )
      else . end
    ' "$dst")"

    # Step 3: 把 pruned 与基线递归合并
    # 注意：jq 函数参数是"滤镜表达式"，调用处会重新对当前 . 求值——
    # 在 reduce 内部 . 会变成累加器，导致 a[$k] 被解成"索引累加器"而报错。
    # 所以先用 `a as $a | b as $b` 把两侧绑定成真值再递归。
    local merged
    merged="$(jq -n --argjson a "$pruned" --slurpfile b "$src" '
      def merge(a; b):
        a as $a | b as $b |
        if   ($a|type)=="object" and ($b|type)=="object" then
          reduce (($a|keys_unsorted)+($b|keys_unsorted)|unique)[] as $k
            ({}; .[$k] = merge($a[$k]; $b[$k]))
        elif ($a|type)=="array"  and ($b|type)=="array"  then
          ($a + $b) | unique
        elif $b == null then $a
        else $b
        end;
      merge($a; $b[0])
    ')"

    # 等价性检查：把当前文件也过一遍 jq 规范化，再和合并结果比较，避免因空白差异误报变化
    local current
    current="$(jq '.' "$dst")"
    if [ "$merged" = "$current" ]; then
        info "已跳过 ${name}（内容已包含基线）"
        return
    fi

    # 真的变了：备份后写入
    local ts
    ts="$(date +%Y%m%d-%H%M%S)"
    cp "$dst" "${dst}.bak.${ts}"
    printf '%s\n' "$merged" > "$dst"
    success "已合并 ${name}（备份：${name}.bak.${ts}）"
}

# 从一个文件中提取 marker 块（含首尾 marker 行本身），输出到 stdout
# 用法: extract_toml_block <file>
extract_toml_block() {
    awk -v b="$TOML_MARKER_BEGIN" -v e="$TOML_MARKER_END" '
        $0 == b || $0 == "# >>> claude-code-global managed >>>" { inblk = 1 }
        inblk   { print }
        $0 == e || $0 == "# <<< claude-code-global managed <<<" { inblk = 0 }
    ' "$1"
}

# 合并基线 TOML 配置进本地 config.toml（非破坏性）
# 策略（与 merge_settings 等价，但 TOML 无 jq，改用 marker 块整体重写）：
#   - dst 不存在 → 整份复制基线（含 marker 块外的推荐策略）
#   - dst 存在且无 marker 块 → 末尾追加基线的 marker 块
#   - dst 存在且有旧 marker 块 → 用基线的块整体替换旧块
#   - 块内容与现有一致 → 跳过（不产生空备份）
# marker 块只含 [[hooks.*]] 数组表，可安全追加到任意 TOML 文件末尾；
# 用户在 marker 块外手写的内容（含 approval_policy / [projects] 等）一律保留。
# 用法: merge_toml <基线TOML> <目标TOML>
merge_toml() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    # 本地没有：整份复制
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        success "已创建 ${name}（从 $(basename "$src") 初始化）"
        return
    fi

    # 提取基线的 marker 块
    local block
    block="$(extract_toml_block "$src")"
    if [ -z "$block" ]; then
        warn "基线 $(basename "$src") 无 marker 块，跳过合并 ${name}"
        return
    fi

    local ts
    if grep -qE "^# >>> (claude-code-global|coding-agent-config) managed >>>$" "$dst"; then
        # 已有 marker 块：比较是否需要更新
        local current_block
        current_block="$(extract_toml_block "$dst")"
        if [ "$current_block" = "$block" ]; then
            info "已跳过 ${name}（marker 块已是最新）"
            return
        fi
        # 整体替换旧块：备份后用 awk 删旧块插新块
        ts="$(date +%Y%m%d-%H%M%S)"
        cp "$dst" "${dst}.bak.${ts}"
        local block_file merged_file
        block_file="$(mktemp)"
        merged_file="$(mktemp)"
        printf '%s\n' "$block" > "$block_file"
        awk -v b="$TOML_MARKER_BEGIN" -v e="$TOML_MARKER_END" -v nf="$block_file" '
            $0 == b || $0 == "# >>> claude-code-global managed >>>" {
                inblk = 1
                while ((getline line < nf) > 0) print line
                close(nf)
                next
            }
            inblk && ($0 == e || $0 == "# <<< claude-code-global managed <<<") { inblk = 0; next }
            inblk { next }
            { print }
        ' "$dst" > "$merged_file"
        mv "$merged_file" "$dst"
        rm -f "$block_file"
        success "已更新 ${name} 的 marker 块（备份：${name}.bak.${ts}）"
    else
        # 无 marker 块：末尾追加
        ts="$(date +%Y%m%d-%H%M%S)"
        cp "$dst" "${dst}.bak.${ts}"
        printf '\n%s\n' "$block" >> "$dst"
        success "已向 ${name} 追加 marker 块（备份：${name}.bak.${ts}）"
    fi
}

# 以 user-wins 语义把推荐的系统级 uv 配置 seed 到 ~/.config/uv/uv.toml
# 策略（与 scripts/user-config.sh 的 ccg_seed_user_config 一致：缺省才填、绝不覆盖）：
#   - 目标不存在 → 建父目录 + 整份复制基线
#   - 目标已存在 → 一律不碰（用户自管），仅打印一行提示
# 不做字段级 merge：uv.toml 的 python-preference 是标量键，
# 在用户已设同键时 marker-block 追加会触发 TOML 重复键错误，得不偿失。
# 用法: seed_uv_config <基线TOML>
seed_uv_config() {
    local src="$1"
    local dst="${XDG_CONFIG_HOME:-$HOME/.config}/uv/uv.toml"

    if [ ! -f "$src" ]; then
        warn "未找到 $(basename "$src")，跳过系统级 uv 配置 seed"
        return
    fi

    if [ -f "$dst" ]; then
        info "已跳过 ${dst}（已存在，用户自管）"
        info "  如需机器级 only-managed，可手动加：python-preference = \"only-managed\""
        return
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    success "已创建 ${dst}（从 $(basename "$src") 初始化系统级 uv 配置）"
}

# 创建一个符号链接，处理已存在的情况
# 用法: link_item <源路径> <目标路径>
link_item() {
    local src="$1"
    local dst="$2"
    local name
    name="$(basename "$dst")"

    if [ -L "$dst" ]; then
        local current_target
        current_target="$(readlink "$dst")"
        if [ "$current_target" = "$src" ]; then
            info "已跳过 ${name}（软链接已正确）"
            return
        else
            rm "$dst"
            ln -s "$src" "$dst"
            success "已更新 ${name}（旧链接指向 ${current_target}）"
        fi
    elif [ -e "$dst" ]; then
        mv "$dst" "${dst}.bak"
        ln -s "$src" "$dst"
        warn "已备份 ${name} → ${name}.bak，并创建软链接"
    else
        ln -s "$src" "$dst"
        success "已链接 $name"
    fi
}

# 改名后旧源码根可能已不存在；更新任何入口前，记录旧安装的成对身份链接。
# 不靠目录名或技能名认亲，避免误接管同名第三方内容。
CCG_MANAGED_ROOTS=""
ccg_is_managed_root() {
    [ -f "$1/GLOBAL_AGENTS.md" ] && [ -f "$1/install.sh" ] && return 0
    printf '%s\n' "$CCG_MANAGED_ROOTS" | grep -Fxq -- "$1"
}

ccg_discover_managed_roots() {
    local home root doc
    CCG_MANAGED_ROOTS="$REPO_DIR"
    for home in "$HOME/.codex" "${CODEX_HOME:-$HOME/.codex}" "$HOME/.claude" "$HOME/.coding-agent"; do
        [ -L "$home/global-repo" ] || continue
        root="$(readlink "$home/global-repo")"
        case "$root" in /*) ;; *) continue ;; esac
        for doc in "$home/AGENTS.md" "$home/CLAUDE.md" "$home/skills"; do
            [ -L "$doc" ] || continue
            case "$(readlink "$doc")" in
                "$root/GLOBAL_AGENTS.md"|"$root/skills")
                    CCG_MANAGED_ROOTS="$CCG_MANAGED_ROOTS
$root"
                    break ;;
            esac
        done
    done
}

# 旧版本曾逐文件部署 scripts/hooks、目录部署模板等；只修复已认亲的旧投影。
# 保留真实目录及第三方文件，已迁入口都转向中性稳定路径以承受源码目录改名。
ccg_repair_legacy_resources() {
    local home="$1" rel link target owner file
    for rel in scripts hooks templates playbooks global-repo; do
        link="$home/$rel"
        if [ -L "$link" ]; then
            target="$(readlink "$link")"
            if [ "$rel" = global-repo ]; then owner="$target"; else owner="${target%/"$rel"}"; fi
            if ccg_is_managed_root "$owner"; then
                link_item "$HOME/.coding-agent/$rel" "$link"
            fi
        elif [ -d "$link" ] && { [ "$rel" = scripts ] || [ "$rel" = hooks ]; }; then
            for file in "$link"/*; do
                [ -L "$file" ] || continue
                target="$(readlink "$file")"
                owner="${target%/"$rel"/"$(basename "$file")"}"
                [ "$owner" != "$target" ] || continue
                ccg_is_managed_root "$owner" || continue
                link_item "$HOME/.coding-agent/$rel/$(basename "$file")" "$file"
            done
        fi
    done
}

# 清理本仓改名 / 迁移后留在 agent 端的旧软链。
# 用法: unlink_legacy_dir <链接路径> [软链目标相对仓库根的路径，默认 rules]
#
# 背景：本仓曾把 rules/ 软链到 <agent_home>/rules，而 rules 是 Claude Code 的**保留目录名**——
# 放进去的 .md 会被当作用户级 memory 全文注入每一个会话的系统提示（与「按需读」的设计意图正相反）。
# 改用中性目录名 playbooks/ 后，老机器上的旧软链必须清掉，否则那八份文档继续常驻、收益归零，
# 而且是静默的：install 全绿、日志漂亮，没人会发现。
# round 54 把 skills/routine-docs 改名为 skills/routine-dev，留下的是同一类断链，故把目标
# 路径参数化——改名这件事以后还会发生，第二次就不该再复制一遍函数。
#
# 认亲方式：软链目标形如 <某目录>/<rel>，且 <某目录> 带本仓标志文件。**不比对当次 $REPO_DIR
# 的精确路径**——一台机器上可能有多个 checkout（主工作树 + 若干 worktree），旧软链指向哪一个
# 都得认得出来；比对精确路径会在「从 worktree 跑 install」时漏删。
#
# 安全边界：非软链（用户自建的真实目录）不碰；目标末段不是 <rel> 的不碰；父目录不带本仓标志
# 文件的不碰。注意用 -L / readlink 而非 -e / readlink -f——目录改名后旧软链已是断链，后者
# 在断链上不工作，会造成静默漏删。
unlink_legacy_dir() {
    local link="$1"
    local rel="${2:-rules}"
    [ -L "$link" ] || return 0

    local target parent
    target="$(readlink "$link")"
    # 只认绝对路径：相对目标下面的认亲检查会相对 CWD 解析，而本脚本通常正是从某个
    # checkout 根跑起来的，标志文件就在手边，容易把不相干的相对软链误判成自家的。
    # 本仓建的软链一律是绝对路径，直接拒掉相对路径即可，不做花哨解析。
    case "$target" in
    /*/"$rel") ;;
    *) return 0 ;;
    esac
    parent="${target%/"$rel"}"
    ccg_is_managed_root "$parent" || return 0

    rm -f "$link"
    info "已清理旧的 ${link}（指向 ${rel}，已改名或迁移）"
}

# 共享资源只有一份；Agent 原生目录仅提供各自要求的发现入口。
deploy_shared() {
    local shared="$HOME/.coding-agent" name
    mkdir -p "$shared"
    for name in scripts templates playbooks skills hooks agents; do
        [ -d "$REPO_DIR/$name" ] || continue
        link_item "$REPO_DIR/$name" "$shared/$name"
    done
    link_item "$REPO_DIR" "$shared/global-repo"
}

# 只移除能认出属于本仓的旧技能软链，不触碰第三方技能或真实目录。
deploy_skills() {
    local dst="$1" legacy="${2:-}" skill_dir skill_name
    mkdir -p "$dst"
    if [ -n "$legacy" ]; then
        for skill_dir in "$legacy"/*; do
            [ -L "$skill_dir" ] || continue
            unlink_legacy_dir "$skill_dir" "skills/$(basename "$skill_dir")"
        done
    fi
    for skill_dir in "$REPO_DIR/skills"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name="$(basename "$skill_dir")"
        local existing="$dst/$skill_name" target owner
        if [ -e "$existing" ] || [ -L "$existing" ]; then
            target="$(readlink "$existing" 2>/dev/null || true)"
            owner="${target%/skills/"$skill_name"}"
            if [ ! -L "$existing" ] || { [ "$target" != "$HOME/.coding-agent/skills/$skill_name" ] &&
               { [ "$owner" = "$target" ] || ! ccg_is_managed_root "$owner"; }; }; then
                warn "保留非本仓管理的同名技能：$existing"
                continue
            fi
        fi
        link_item "$HOME/.coding-agent/skills/$skill_name" "$dst/$skill_name"
    done
}

# 全局与项目规则相加可能超过 Codex 默认读取上限；仅补缺，用户值优先。
seed_codex_doc_budget() {
    local dst="$1" tmp
    grep -qE '^[[:space:]]*project_doc_max_bytes[[:space:]]*=' "$dst" && return 0
    tmp="$(mktemp)"
    printf 'project_doc_max_bytes = 65536\n' > "$tmp"
    cat "$dst" >> "$tmp"
    cp "$dst" "${dst}.bak.$(date +%Y%m%d-%H%M%S).doc-budget"
    mv "$tmp" "$dst"
}

deploy_codex() {
    local agent_home="${CODEX_HOME:-$HOME/.codex}"
    mkdir -p "$agent_home"
    link_item "$REPO_DIR/GLOBAL_AGENTS.md" "$agent_home/AGENTS.md"
    deploy_skills "$HOME/.agents/skills" "$agent_home/skills"
    unlink_legacy_dir "$agent_home/rules"
    merge_toml "$REPO_DIR/codex.config.base.toml" "$agent_home/config.toml"
    seed_codex_doc_budget "$agent_home/config.toml"
}

# Claude Code 仅在已有安装时保留兼容入口，不是 Codex 的运行前提。
deploy_claude_compat() {
    local agent_home="$HOME/.claude"
    [ -d "$agent_home" ] || return 0
    link_item "$REPO_DIR/GLOBAL_AGENTS.md" "$agent_home/CLAUDE.md"
    deploy_skills "$agent_home/skills"
    unlink_legacy_dir "$agent_home/rules"
    unlink_legacy_dir "$agent_home/skills/routine-docs" "skills/routine-docs"
    [ ! -d "$REPO_DIR/agents" ] || link_item "$REPO_DIR/agents" "$agent_home/agents"
    merge_settings "$REPO_DIR/settings.base.json" "$agent_home/settings.json"
}

# 判断目录是否位于 git linked worktree 内（主 checkout、非 git 目录都返回非 0）。
# 比较 git-dir 与 git-common-dir 的物理路径：二者在 rev-parse 输出里可能是相对路径，
# 故各自 cd 进去取 pwd -P，不依赖较新 git 才有的 --path-format。
ccg_is_linked_worktree() {
    local dir="$1" rel_git rel_common git_dir common_dir
    # 先单独取值并判空：rev-parse 失败时输出空串，而 cd "" 会成功，不拦就会误判为同一目录
    rel_git="$(cd "$dir" 2>/dev/null && git rev-parse --git-dir 2>/dev/null)" || return 1
    rel_common="$(cd "$dir" && git rev-parse --git-common-dir 2>/dev/null)" || return 1
    [ -n "$rel_git" ] && [ -n "$rel_common" ] || return 1
    git_dir="$(cd "$dir" && cd "$rel_git" && pwd -P)" || return 1
    common_dir="$(cd "$dir" && cd "$rel_common" && pwd -P)" || return 1
    [ "$git_dir" != "$common_dir" ]
}

# 测试可 source 本脚本只取函数定义、不跑安装主流程（见 docs/51-rules按需加载/test-unlink-legacy.sh）。
#
# 只在 source 语境下生效：直接执行时，哪怕环境里意外带了这个变量也照常安装。否则
# `CCG_INSTALL_LIB_ONLY=1 bash install.sh` 会零输出 + 退出码 0 地静默 no-op，伪装成
# 一次成功的安装——而定时跑 install.sh 的正是 scripts/auto-update.sh，这种失败不会
# 有任何人察觉（与本轮 unlink_legacy_dir 漏删是同一类病：全绿、无感、收益归零）。
if [ "${CCG_INSTALL_LIB_ONLY:-0}" = "1" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
    return 0
fi

# 拒绝在 linked worktree 内运行：REPO_DIR 取自脚本所在目录，从 worktree 跑会把两端全局软链
# 整体改指到 worktree，worktree 一删全成死链。这个坑在 round 31 / 51 / 52 / 53 / 54 / 60
# 里反复出现，文档提醒防不住，故在入口硬拦、不留开关。验证未合入的改动请用
# CCG_INSTALL_LIB_ONLY 沙盘测函数（见 docs/51、docs/53），或合入后从主 checkout 跑。
if ccg_is_linked_worktree "$REPO_DIR"; then
    main_checkout="$(git -C "$REPO_DIR" worktree list --porcelain | sed -n '1s/^worktree //p')"
    echo "[ERROR] install.sh 不能在 git worktree 内运行（当前: ${REPO_DIR}）" >&2
    echo "        从 worktree 安装会把全局软链指向 worktree，删除后全部断链。" >&2
    echo "        请合入后在主 checkout 执行：" >&2
    echo "  bash ${main_checkout}/install.sh" >&2
    exit 1
fi

echo "=============================="
echo " Coding Agent 全局配置安装"
echo "=============================="
echo ""
info "仓库目录: $REPO_DIR"

ccg_discover_managed_roots
deploy_shared
deploy_codex
deploy_claude_compat
ccg_repair_legacy_resources "${CODEX_HOME:-$HOME/.codex}"
[ "${CODEX_HOME:-$HOME/.codex}" = "$HOME/.codex" ] || ccg_repair_legacy_resources "$HOME/.codex"
[ ! -d "$HOME/.claude" ] || ccg_repair_legacy_resources "$HOME/.claude"

# 用户可配置项：seed 真实配置 + 应用偏好（全局一次，与具体 agent 端无关）
# 机制见 scripts/user-config.sh 与 docs/27-用户可配置项机制/DESIGN.md
if [ -f "$REPO_DIR/scripts/user-config.sh" ]; then
    echo ""
    echo "------------------------------"
    info "用户可配置项"
    echo "------------------------------"
    # shellcheck disable=SC1091
    source "$REPO_DIR/scripts/user-config.sh"
    ccg_seed_user_config "$REPO_DIR/user.config.example.env" || warn "用户配置 seed 失败（不阻塞）"
    ccg_apply_git_default_branch || warn "应用 git 默认分支失败（不阻塞）"
else
    warn "未找到 scripts/user-config.sh，跳过用户可配置项处理"
fi

# 系统级 uv 配置：seed ~/.config/uv/uv.toml（机器级 only-managed + 清华源默认）
# user-wins：缺失才创建，已存在不动。与具体 agent 端无关，故全局只跑一次。
if [ -f "$REPO_DIR/uv.config.base.toml" ]; then
    echo ""
    echo "------------------------------"
    info "系统级 uv 配置"
    echo "------------------------------"
    seed_uv_config "$REPO_DIR/uv.config.base.toml"
else
    warn "未找到 uv.config.base.toml，跳过系统级 uv 配置 seed"
fi

# 注册 OS 自动同步调度器（launchd / systemd user timer）
# 让 scripts/auto-update.sh 自动跑「登录 + 每小时」
# 失败 warn 不阻塞主 install
if [ -x "$REPO_DIR/scheduler/install.sh" ]; then
    echo ""
    bash "$REPO_DIR/scheduler/install.sh" || warn "调度器注册失败，可手动：bash $REPO_DIR/scheduler/install.sh"
fi

echo ""
echo "=============================="
echo " 安装完成"
echo "=============================="

echo ""
warn "Codex hooks 需在 Codex 的 /hooks 中审阅并信任当前定义后才会生效。"
