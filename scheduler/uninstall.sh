#!/usr/bin/env bash
# 取消 OS 调度器注册(逃生舱)。

set -uo pipefail

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }

OS="$(uname -s)"

case "$OS" in
    Darwin)
        for label in com.coding-agent-config.auto-update com.claude-code-global.auto-update; do
            plist="$HOME/Library/LaunchAgents/${label}.plist"
            if [ -f "$plist" ]; then
                launchctl unload "$plist" 2>/dev/null || true
                rm -f "$plist"
            fi
            # 旧 job 自迁移后可能只有内存注册，没有磁盘 plist。
            if launchctl list "$label" >/dev/null 2>&1; then
                launchctl remove "$label" 2>/dev/null || true
            fi
            if launchctl list "$label" >/dev/null 2>&1; then
                warn "调度器仍已加载：$label"
                exit 1
            fi
        done
        success "已移除 launchd 调度器"
        ;;
    Linux)
        if command -v systemctl >/dev/null 2>&1; then
            for prefix in coding-agent-config claude-code-global; do
                systemctl --user disable --now "${prefix}-auto-update.timer" 2>/dev/null || true
                rm -f "$HOME/.config/systemd/user/${prefix}-auto-update.timer"
                rm -f "$HOME/.config/systemd/user/${prefix}-auto-update.service"
            done
            systemctl --user daemon-reload 2>/dev/null || true
            success "已移除 systemd user timer"
        else
            warn "未检测到 systemd,无操作"
        fi
        ;;
    *) warn "不支持的 OS: $OS" ;;
esac
