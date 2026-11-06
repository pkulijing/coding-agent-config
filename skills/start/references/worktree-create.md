# worktree 创建细则（`/start` 通用流程第 4 步展开）

> `/start` 通用流程第 4 步读本文。**args 含 `--no-worktree` 时整节跳过**，在当前分支直接开发、docs 目录落在当前工作树；`/finish` 收尾时检测到非 worktree 会跳过 worktree 收尾，对称无悬空分支。

默认每轮开发在独立 git worktree 内进行，让多轮可并行、互不污染主工作树：

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（只剥掉 `origin/` 前缀）；失败则本地探测 `main` / `master`。不要只取远端 ref 的末段（主分支可能含 `/`），应仅剥掉 `origin/` 前缀。（「远端对齐」小节的 `<主分支>` 与这里是同一次探测，探一次两处复用。）
- **防嵌套**：若当前已在某个 linked worktree 内（`git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套创建 worktree**。
- **确保 worktree 目录被忽略**：优先复用已有忽略规则和 `.worktrees/.gitignore`，不覆盖已有文件。缺少忽略规则时在主 checkout 的 `.worktrees/.gitignore` 写入 `*`，自身也忽略，避免开轮时给主树留下未跟踪文件；该本地忽略文件不额外提交。若项目已跟踪此文件，沿用其规则。不要把子目录规则加到项目根 `.gitignore`。
- **创建方式按路径要求选择**：本技能的默认路径就是项目内 `.worktrees/`。使用原生 `git worktree add` 明确指定路径；Codex 桌面的托管 `create_worktree` 没有目标路径入参，不用于本技能默认创建。普通 Git 工作树不自动注册为桌面托管工作树；清理时也不调用仅适用于托管工作树的 archive 工具。用户显式要求托管时才采用该工具，并告知实际路径与生命周期差异。
- **建之前先确认这个 N 没被别人占走**（第 2 步的信号可能已滞后）：

  ```bash
  git branch    --list "round<N>" --list "round<N>-*"                # 本地
  git branch -r --list "origin/round<N>" --list "origin/round<N>-*"  # 远端，吃第 1 步那次 fetch
  ```

  **两条都要跑，别图省事合成一条 `git branch -a`** —— `-a` 配不带 `origin/` 前缀的 pattern **匹配不到远端分支**，分别核对本地与远端命名空间。

  任一条有输出 → **重算 N 取下一个空位，别靠换个描述词绕开**。这步不能省：描述不同的 `round<N>-a` / `round<N>-b` 会各自建成功、git 不会拦，撞号一路潜伏到合并时才炸。

- **创建**：worktree 目录名与分支名统一为 `round<N>-<英文短描述>`，**整串纯 ASCII**：

  ```bash
  git worktree add .worktrees/round<N>-<英文短描述> -b round<N>-<英文短描述> <主分支>
  ```

  **短描述规格（照做，别自由发挥）**：字符集 `[a-z0-9-]`（小写字母 / 数字 / 连字符）；**短描述本身 ≤ 20 字符**（不含 `round<N>-` 前缀）、2–4 个词；与第 3 步的中文描述同义即可（`开轮远端对齐` → `remote-align`、`review 成本与思考深度调优` → `review-cost-tuning`）。没有自然英文对应的专名用拼音。**实在起不出好名字就退回裸 `round<N>`** —— 那是合法命名，别为了凑名字硬造缩写。

- **锚定工作目录**：此后所有工具调用显式使用新 worktree 的绝对路径：shell 设置 `workdir`，git 使用 `git -C <worktree>`，文件编辑与读取用绝对路径。不要假定某次 `cd` 会跨工具调用保留，也不要假定聊天所在项目会自动切换。
- **告知**：打印一行 worktree 路径与分支名，提示用户可在 IDE 中打开该目录并行开发。

新 worktree 不带忽略的依赖、缓存或本地配置。运行前检查所需项；两种通用应对，按依赖性质二选一：

1. **软链主 checkout**（重依赖、目录级，如 `node_modules/`）：`ln -s <主checkout>/<path> <worktree>/<path>`，**跑完即删、切勿 commit**——`node_modules/` 这类带尾斜杠的 gitignore 模式只匹配目录、**不匹配软链**，软链会以 untracked 身份冒进 `git status`。（也可选择在 worktree 内重新准备一份，如 `npm install`，代价是磁盘与时间。）
2. **回退主 checkout 路径**（只读小文件，如 `.env.local` / 凭证）：在脚本 / 工具里显式「优先 worktree 根的该文件、缺则回退主 checkout 同名文件」，比软链更轻、无残留风险。

涉及前端依赖时另按 `playbooks/frontend.md` 的工具约定执行。

## 迁移既有工作树

先检查 `git worktree list --porcelain` 和目标路径是否被占用。旧 `.claude/worktrees/` 下的普通 linked worktree 使用 `git worktree move <旧路径> <项目根>/.worktrees/<目录名>` 迁移，保留分支、未提交和未跟踪文件；不能直接 `mv` 或删目录重建。已有活动会话先停止文件操作再迁移。迁移后用 `git -C <新路径> status`、`git worktree list` 验证。托管工作树只按所属应用的生命周期处理，不擅自搬动。
