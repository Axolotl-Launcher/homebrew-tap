# 维护指南 / Maintenance

[使用指南 / Usage](README.md) · **维护指南 / Maintenance**

[中文](#中文) | [English](#english)

## 中文

### 自动化

- **Cask CI** 检查 Ruby 语法、Homebrew 审计和更新脚本测试。
- **Update Casks** 每天在新加坡／中国时间 00:00、06:00、12:00、18:00 检查，也支持手动运行及 `main` 分支的 Cask 推送触发。GitHub 定时运行可能延迟。
- 更新脚本通过 `livecheck` 发现正式版本，核对 GitHub Release、下载地址和 SHA256；拒绝草稿、预发布、仓库变化和校验值不匹配。
- 只读任务准备并严格审计更新，再通过 artifact 交给写权限任务。发布任务只复制允许的 Cask／README 数据并核对实际 PR，不执行 Cask Ruby。无变化不创建 PR；验证失败时工作流不执行自动合并，人工合并是否被阻止由仓库规则决定。

在 **Settings → Actions → General → Workflow permissions** 中允许 Actions 创建 PR。使用内置 `GITHUB_TOKEN`，无需额外密钥；它创建的 PR 可能不触发 PR CI，因此更新工作流会自行验证实际提交。

如需验证后自动 squash 合并，可设置仓库 Actions 变量 `AUTO_MERGE_UPDATES=true`；默认不自动合并，也不会绕过分支保护。自动更新仅在 `Axolotl-Launcher/homebrew-tap` 运行，Fork 中的 CI 仍可运行。

版本与校验值由 `Casks/axolotl-launcher.rb` 定义。脚本支持单一数字版本、单一 SHA256 和随版本变化的 GitHub Releases URL；遇到不支持的格式会保持原样并报告原因。发布或网络错误会中止更新。审计不代替实际运行测试。

### 自动合并与运行边界

启用自动合并前，由维护者为 `main` 配置必需状态检查并要求 PR 分支保持最新，同时确保检查对应实际 PR 头部提交。工作流会在合并前再检查基础分支是否变化，并用 `--match-head-commit` 锁定 PR 提交；这些检查不能代替 GitHub 的服务端分支保护。

开启自动合并时，发布任务使用 `actions: write` 显式触发更新分支的只读 **Cask CI**，等待对应 PR 提交检查通过后再尝试合并。查找运行最多等待 2 分钟，CI 最多等待 10 分钟；失败或超时保留 PR。分支保护仍须由维护者配置；不要把默认分支的检查当成 PR 头部检查。人工合并模式下可手动触发 CI。

子进程默认超时 600 秒；下载连接超时 20 秒、单次传输最多 300 秒、重试时间预算 480 秒，仍受子进程总时限约束。CI 和更新任务最多运行 20 分钟。

CI 更新由 `concurrency` 串行化，各次运行使用独立检出目录。本地不要同时对同一副本启动多个更新器。文件采用原子替换，普通异常、中断和 SIGTERM 会尝试回滚已写入的更改；发现期间发生的外部编辑会报错并保留它。该检查不能完全消除并发竞争，仍应使用独立副本。强制终止或断电可能留下部分改动，重新运行前检查差异。失败的准备任务不会进入发布任务。

所有 Actions 固定到完整提交 SHA；升级时核对上游提交并重新运行 CI，不直接改回可变标签。

### Homebrew 与工作流命令

更新脚本需要 Python 3、Homebrew 和 GitHub CLI。除标注为 CI 专用的命令外，从仓库根目录运行；远端操作需相应权限。

Homebrew 命令读取的是 `brew --repository Axolotl-Launcher/tap` 指向的副本，而不是自动读取当前开发目录。测试未合并的分支可使用 Fork CI 或隔离测试副本；不要将日常 tap 链接到开发目录。下面的 `readme` 和 `update` 命令用 `--root` 明确指定注册的 tap 副本，并会修改其中的文件，建议只在专用测试环境运行。

CI 专用命令依赖 runner 提供的环境变量；`verify-cask-update.py` 是工作流在检出 PR 前保存的可信脚本副本，不是另一个仓库文件。安装、卸载及远端工作流命令具有实际副作用，不属于只读检查。

| 用途 | 命令 | 前提与影响 |
|---|---|---|
| 更新脚本回归测试 | `python3 -B -m unittest discover -s tests -v` | 运行本仓库的更新防御和 PR 内容校验测试，不安装应用或创建 PR |
| Actions 配置校验 | `actionlint -shellcheck='' .github/workflows/ci.yml .github/workflows/update.yml` | 需 Actionlint；检查本仓库两个工作流，关闭可选 ShellCheck |
| 添加官方 tap | `brew tap Axolotl-Launcher/tap` | 克隆独立副本；未合并的代码不会出现在官方 main |
| 查看 tap 路径 | `brew --repository Axolotl-Launcher/tap` | 只读；确认 Homebrew 实际读取哪个副本 |
| 授权测试 Cask | `brew trust --cask Axolotl-Launcher/tap/axolotl-launcher` | 保存单 Cask 信任，不安装应用 |
| 读取安装定义 | `brew info --cask --json=v2 Axolotl-Launcher/tap/axolotl-launcher` | 读取注册的 tap 副本，不一定是当前开发目录 |
| 检查上游新版 | `brew livecheck --cask --json Axolotl-Launcher/tap/axolotl-launcher` | 联网，只读；脚本使用相同的 JSON 接口 |
| Homebrew 格式 | `brew style --cask Axolotl-Launcher/tap/axolotl-launcher` | 检查注册 tap 中的 Cask |
| 自动修正格式 | `brew style --fix --cask Axolotl-Launcher/tap/axolotl-launcher` | 修改注册 tap 副本中的 Cask，之后检查差异 |
| 严格在线审计 | `brew audit --cask --strict --online Axolotl-Launcher/tap/axolotl-launcher` | 联网，可能下载并解包；不安装应用 |
| 查看脚本参数 | `python3 -B scripts/update_casks.py --help` | 只读；列出 update、readme、export、apply、verify |
| 重新生成应用表 | `python3 -B scripts/update_casks.py readme --root "$(brew --repository Axolotl-Launcher/tap)"` | 修改注册 tap 副本的 README；建议专用测试环境 |
| 本地检查并更新 | `python3 -B scripts/update_casks.py update --root "$(brew --repository Axolotl-Launcher/tap)"` | 修改该副本的 Cask 和 README；需 gh 登录；不创建 PR |
| 导出已审计提案 | `python3 -B scripts/update_casks.py export --proposal "$RUNNER_TEMP/cask-proposal"` | CI 只读任务；保存清单及更新文件供上传，不复制脚本 |
| 应用提案数据 | `python3 -B scripts/update_casks.py apply --proposal "$RUNNER_TEMP/cask-proposal"` | CI 发布任务；核对基础提交、路径和内容，不执行 Cask Ruby |
| 验证实际 PR 内容 | `python3 -B "$RUNNER_TEMP/verify-cask-update.py" verify --root "$GITHUB_WORKSPACE" --proposal "$RUNNER_TEMP/cask-proposal"` | CI 专用；使用可信脚本副本，直接读取下载提案中的清单 |
| 查看运行记录 | `gh run list --repo Axolotl-Launcher/homebrew-tap --limit 10` | 只读；Fork 验证时将仓库换成自己的 Fork |
| 查看失败日志 | `gh run view RUN_ID --repo Axolotl-Launcher/homebrew-tap --log-failed` | 只读；将 RUN_ID 替换为实际编号 |
| 手动运行 CI | `gh workflow run ci.yml --repo Axolotl-Launcher/homebrew-tap --ref main` | 需工作流运行权限，且文件已合并到 main |
| 检查更新 PR 分支 | `gh workflow run ci.yml --repo Axolotl-Launcher/homebrew-tap --ref automation/update-casks` | 维护者操作；在更新 PR 的实际分支上运行 CI，不用 main 的结果代替 |
| 手动检查更新 | `gh workflow run update.yml --repo Axolotl-Launcher/homebrew-tap --ref main` | 维护者操作；可能创建更新 PR；开启自动合并时也可能合并 |
| 启用自动合并 | `gh variable set AUTO_MERGE_UPDATES --body true --repo Axolotl-Launcher/homebrew-tap` | 需仓库变量管理权限；改变后续更新行为 |
| 关闭自动合并 | `gh variable set AUTO_MERGE_UPDATES --body false --repo Axolotl-Launcher/homebrew-tap` | 维护者操作；之后保留 PR 等待人工合并 |
| 安装验证 | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` | 会安装应用；只在无现有安装的专用测试环境运行 |
| 卸载验证 | `brew uninstall --cask Axolotl-Launcher/tap/axolotl-launcher` | 会删除应用；仅清理上一步的测试安装 |

## English

### Automation

- **Cask CI** runs Ruby syntax checks, Homebrew audits, and updater tests.
- **Update Casks** runs four times daily at 00:00, 06:00, 12:00, and 18:00 (UTC+8), manually, and on Cask pushes to `main`. GitHub schedules may be delayed.
- The updater uses `livecheck`, verifies stable GitHub release assets and SHA256 checksums, and rejects drafts, prereleases, repository changes, and checksum mismatches.
- A read-only job prepares and audits updates, then passes an artifact to the publishing job. The write-enabled job copies only allowed Cask/README data and verifies the actual PR without evaluating Cask Ruby. No changes means no PR. Failed validation prevents this workflow from automatically merging; repository rules control manual merges.

Allow Actions to create PRs under **Settings → Actions → General → Workflow permissions**. No extra secrets are needed. PRs created with `GITHUB_TOKEN` may not trigger PR CI, so the update workflow validates the actual commit itself.

To enable automatic squash merging after validation, set the repository Actions variable `AUTO_MERGE_UPDATES=true`. Automatic merging is off by default and never bypasses branch protection. Updates run only in `Axolotl-Launcher/homebrew-tap`; CI can still run in forks.

`Casks/axolotl-launcher.rb` defines the version and checksum. The updater supports one numeric version, one SHA256, and a version-dependent GitHub Releases URL. Unsupported formats remain unchanged with a warning; release or network errors abort the update. Audits do not replace runtime testing.

### Automatic merging and execution limits

Before enabling automatic merging, maintainers must configure required status checks for `main`, require PR branches to be up to date, and ensure checks are attached to the actual PR head commit. The workflow rechecks the base immediately before merging and pins the PR head with `--match-head-commit`; these checks do not replace server-side branch protection.

When automatic merging is enabled, the publishing job uses `actions: write` to dispatch read-only **Cask CI** on the update branch and waits for the matching PR commit to pass before attempting a merge. Run discovery is limited to two minutes and CI waiting to ten minutes; failures or timeouts leave the PR open. Maintainers must still configure branch protection. Checks on the default branch are not checks on the PR head. In manual merging mode, CI can be dispatched manually.

Subprocesses default to a 600-second timeout. Downloads use a 20-second connection timeout, a 300-second per-transfer limit and a 480-second retry budget, bounded by the subprocess deadline. CI and update jobs have a 20-minute limit.

Workflow concurrency serializes updates and each run has an isolated checkout. Do not run multiple local updaters against the same checkout. Files are replaced atomically; normal exceptions, interrupts and SIGTERM attempt to roll back completed writes. Detected external edits abort the update and are preserved. These checks cannot eliminate all concurrent races, so use isolated checkouts. A hard kill or power loss can still leave partial changes; review the working tree before rerunning. A failed preparation job cannot proceed to publishing.

Actions are pinned to full commit SHAs. Verify upstream commits and rerun CI when updating pins; do not replace them with mutable tags.

### Homebrew and workflow commands

The updater requires Python 3, Homebrew, and GitHub CLI. Run commands from the repository root unless marked CI-only; remote operations require the appropriate permissions.

Homebrew reads the checkout returned by `brew --repository Axolotl-Launcher/tap`, not automatically the current development directory. Test unmerged branches in fork CI or an isolated checkout; do not link the everyday tap to the development directory. The `readme` and `update` commands below explicitly target the registered tap with `--root` and modify files there, so use a dedicated test environment.

CI-only commands depend on runner environment variables. `verify-cask-update.py` is a trusted copy saved before the PR checkout, not an additional repository file. Installation, uninstallation, and remote workflow commands have real effects and are not read-only checks.

| Purpose | Command | Prerequisites and effects |
|---|---|---|
| Updater regression tests | `python3 -B -m unittest discover -s tests -v` | Tests this repository's update guards and PR verification without installing apps or creating PRs |
| Actions configuration lint | `actionlint -shellcheck='' .github/workflows/ci.yml .github/workflows/update.yml` | Requires Actionlint; checks both workflows with optional ShellCheck disabled |
| Add official tap | `brew tap Axolotl-Launcher/tap` | Clones a separate checkout; unmerged code is absent from official main |
| Locate tap checkout | `brew --repository Axolotl-Launcher/tap` | Read-only; identifies the checkout Homebrew loads |
| Trust the Cask | `brew trust --cask Axolotl-Launcher/tap/axolotl-launcher` | Stores item-level trust without installing the app |
| Inspect Cask metadata | `brew info --cask --json=v2 Axolotl-Launcher/tap/axolotl-launcher` | Reads the registered tap, not necessarily the development checkout |
| Check upstream version | `brew livecheck --cask --json Axolotl-Launcher/tap/axolotl-launcher` | Network access; read-only JSON used by the updater |
| Homebrew style | `brew style --cask Axolotl-Launcher/tap/axolotl-launcher` | Checks the Cask in the registered tap |
| Fix Homebrew style | `brew style --fix --cask Axolotl-Launcher/tap/axolotl-launcher` | Modifies that checkout; review the diff afterward |
| Strict online audit | `brew audit --cask --strict --online Axolotl-Launcher/tap/axolotl-launcher` | May download and extract assets without installing the app |
| Updater help | `python3 -B scripts/update_casks.py --help` | Read-only; lists update, readme, export, apply, and verify |
| Regenerate application tables | `python3 -B scripts/update_casks.py readme --root "$(brew --repository Axolotl-Launcher/tap)"` | Modifies the registered tap README; use a dedicated test environment |
| Run updater locally | `python3 -B scripts/update_casks.py update --root "$(brew --repository Axolotl-Launcher/tap)"` | Modifies its Casks and README; requires gh login; creates no PR |
| Export audited proposal | `python3 -B scripts/update_casks.py export --proposal "$RUNNER_TEMP/cask-proposal"` | Read-only CI job; exports the manifest and changed files, not scripts |
| Apply proposal data | `python3 -B scripts/update_casks.py apply --proposal "$RUNNER_TEMP/cask-proposal"` | Publishing job; checks base, paths and contents without evaluating Cask Ruby |
| Verify actual PR contents | `python3 -B "$RUNNER_TEMP/verify-cask-update.py" verify --root "$GITHUB_WORKSPACE" --proposal "$RUNNER_TEMP/cask-proposal"` | CI only; uses the trusted verifier and the manifest in the downloaded proposal |
| List workflow runs | `gh run list --repo Axolotl-Launcher/homebrew-tap --limit 10` | Read-only; use your fork repository when checking fork CI |
| Read failed-run logs | `gh run view RUN_ID --repo Axolotl-Launcher/homebrew-tap --log-failed` | Read-only; replace RUN_ID with the actual run ID |
| Dispatch CI | `gh workflow run ci.yml --repo Axolotl-Launcher/homebrew-tap --ref main` | Requires workflow permissions and the workflow on main |
| Check the update PR branch | `gh workflow run ci.yml --repo Axolotl-Launcher/homebrew-tap --ref automation/update-casks` | Maintainer operation; runs CI on the actual update branch rather than main |
| Dispatch update check | `gh workflow run update.yml --repo Axolotl-Launcher/homebrew-tap --ref main` | Maintainer operation; may create a PR and merge it if automatic merging is enabled |
| Enable automatic merging | `gh variable set AUTO_MERGE_UPDATES --body true --repo Axolotl-Launcher/homebrew-tap` | Requires repository variable permissions; changes subsequent update behavior |
| Disable automatic merging | `gh variable set AUTO_MERGE_UPDATES --body false --repo Axolotl-Launcher/homebrew-tap` | Maintainer operation; subsequent PRs await manual merging |
| Installation test | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` | Installs the app; use a dedicated environment without an existing installation |
| Uninstallation test | `brew uninstall --cask Axolotl-Launcher/tap/axolotl-launcher` | Removes the app; only clean up the preceding test installation |
