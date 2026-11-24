# worktree 创建细则（`/start` 通用流程第 4 步展开）

> `/start` 通用流程第 4 步读本文。**args 含 `--no-worktree` 时整节跳过**，在当前分支直接开发、批准版 PLAN.md 落在当前工作树；`/finish` 收尾时检测到非 worktree 会跳过 worktree 收尾，对称无悬空分支。

默认每轮开发在独立 git worktree 内进行，让多轮可并行、互不污染主工作树：

- **探测主分支**：`git symbolic-ref --short refs/remotes/origin/HEAD`（只剥掉 `origin/` 前缀）；失败则本地探测 `main` / `master`。不要只取远端 ref 的末段（主分支可能含 `/`），应仅剥掉 `origin/` 前缀。（「远端对齐」小节的 `<主分支>` 与这里是同一次探测，探一次两处复用。）
- **防嵌套**：若当前已在某个 linked worktree 内（`git rev-parse --git-dir` ≠ `git rev-parse --git-common-dir`）→ 停下提示用户「已在 worktree 内」，问是接续当前轮还是退出，**不嵌套创建 worktree**。
- **确保 worktree 目录被忽略**：优先复用已有忽略规则和 `.worktrees/.gitignore`，不覆盖已有文件。缺少忽略规则时在主 checkout 的 `.worktrees/.gitignore` 写入 `*`，自身也忽略，避免开轮时给主树留下未跟踪文件；该本地忽略文件不额外提交。若项目已跟踪此文件，沿用其规则。不要把子目录规则加到项目根 `.gitignore`。
- **创建方式**：Codex 桌面使用 `create_worktree` 创建托管工作树，显式传入主 checkout 为 `sourceRoot`、已核实的基线为 `ref`、本轮名称为 `name`；异步返回时等创建完成，取得真实路径后按下方「项目内入口」建立软链接。不移动真实目录。其他环境使用原生 `git worktree add` 直接在项目 `.worktrees/` 下创建；普通工作树不冒充应用托管工作树。
- **建之前先确认这个 N 没被别人占走**（第 2 步的信号可能已滞后）：

  ```bash
  git branch    --list "round<N>" "round<N>-*" "codex/round<N>" "codex/round<N>-*"
  git branch -r --list "origin/round<N>" "origin/round<N>-*" "origin/codex/round<N>" "origin/codex/round<N>-*"
  ```

  **两条都要跑，别图省事合成一条 `git branch -a`** —— `-a` 配不带 `origin/` 前缀的 pattern **匹配不到远端分支**，分别核对本地与远端命名空间。

  任一条有输出 → **重算 N 取下一个空位，别靠换个描述词绕开**。这步不能省：描述不同的 `round<N>-a` / `round<N>-b` 会各自建成功、git 不会拦，撞号一路潜伏到合并时才炸。

- **创建与命名**：项目内入口名为 `round<N>-<英文短描述>`，分支名为 `round<N>-<英文短描述>`（Codex 使用 `codex/` 前缀），**整串纯 ASCII**。原生 Git 创建方式：

  ```bash
  git worktree add .worktrees/round<N>-<英文短描述> -b round<N>-<英文短描述> <主分支>
  ```

  Codex 托管创建默认是 detached HEAD，须在返回的真实工作树中用 `git switch -c <本轮分支>` 建立分支，再开始开发；不改动主 checkout 的分支。

  **短描述规格（照做，别自由发挥）**：字符集 `[a-z0-9-]`（小写字母 / 数字 / 连字符）；**短描述本身 ≤ 20 字符**（不含 `round<N>-` 前缀）、2–4 个词；与第 3 步的中文描述同义即可（`开轮远端对齐` → `remote-align`、`review 成本与思考深度调优` → `review-cost-tuning`）。没有自然英文对应的专名用拼音。**实在起不出好名字就退回裸 `round<N>`** —— 那是合法命名，别为了凑名字硬造缩写。

- **锚定工作目录**：此后所有工具调用显式使用新 worktree 的真实绝对路径：shell 设置 `workdir`，git 使用 `git -C <worktree>`，文件编辑与读取用绝对路径。项目内软链接用于查找和 IDE 打开，不作为另一个工作树注册。不要假定某次 `cd` 会跨工具调用保留，也不要假定聊天所在项目会自动切换。
- **告知**：打印项目内入口、真实路径与分支名，提示用户可从项目 `.worktrees/` 打开。

## 项目内入口（托管工作树创建、复用与恢复时均执行）

1. 用 `git worktree list --porcelain` 核实主 checkout 和目标工作树，并结合应用附件核实托管身份，不只凭目录名判断。入口固定为 `<主checkout>/.worktrees/<本轮或主题名称>`；先按上文建立目录级忽略。
2. 目标真实路径已经位于该入口时无需软链接。否则创建指向真实绝对路径的目录软链接。创建前检查入口是否存在（含断链）：已指向同一目标则复用；目录、文件或指向其他目标的链接均保留并报告冲突，不覆盖、不自动换名。断链也不能未经归属核验就替换。
3. 建立后核对链接目标，并通过入口运行 `git rev-parse --show-toplevel`，确认解析为预期真实工作树；链接失败或验证失败须明确报告「项目内入口未就绪」，不把创建成功当作入口成功。
4. 托管工作树仍由应用 archive / restore 管理，不用 `git worktree move/remove` 或递归删除处理真实目录。经授权归档成功后，仅移除已核实属于本任务且仍指向该真实路径的软链接本身；恢复后重新核实实际返回路径，再建立或修复本任务的入口。应用自动清理可能留下断链，后续发现时核实归属后处理，不批量删其他入口。

新 worktree 不带忽略的依赖、缓存或本地配置。运行前检查所需项；两种通用应对，按依赖性质二选一：

1. **软链主 checkout**（重依赖、目录级，如 `node_modules/`）：`ln -s <主checkout>/<path> <worktree>/<path>`，**跑完即删、切勿 commit**——`node_modules/` 这类带尾斜杠的 gitignore 模式只匹配目录、**不匹配软链**，软链会以 untracked 身份冒进 `git status`。（也可选择在 worktree 内重新准备一份，如 `npm install`，代价是磁盘与时间。）
2. **回退主 checkout 路径**（只读小文件，如 `.env.local` / 凭证）：在脚本 / 工具里显式「优先 worktree 根的该文件、缺则回退主 checkout 同名文件」，比软链更轻、无残留风险。

涉及前端依赖时另按 `playbooks/frontend.md` 的工具约定执行。

## 迁移既有工作树

先检查 `git worktree list --porcelain` 和目标路径是否被占用。旧 `.claude/worktrees/` 下的普通 linked worktree 使用 `git worktree move <旧路径> <项目根>/.worktrees/<目录名>` 迁移，保留分支、未提交和未跟踪文件；不能直接 `mv` 或删目录重建。已有活动会话先停止文件操作再迁移。迁移后用 `git -C <新路径> status`、`git worktree list` 验证。托管工作树只按所属应用的生命周期处理，不擅自搬动。
