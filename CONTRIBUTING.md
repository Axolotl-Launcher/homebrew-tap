# 维护指南 / Maintenance

[使用指南 / Usage](README.md) · **维护指南 / Maintenance**

[中文](#中文) | [English](#english)

## 中文

### 自动化

- **Cask CI** 检查 Ruby 语法、Homebrew 审计和更新脚本测试。
- **Update Casks** 每天检查两次，也支持手动运行及 `main` 分支的 Cask 推送触发。GitHub 定时运行可能延迟。
- 更新脚本通过 `livecheck` 发现正式版本，核对 GitHub Release、下载地址和 SHA256；拒绝草稿、预发布、仓库变化和校验值不匹配。
- 更新通过 PR 提出，实际 PR 提交通过内容核对和严格在线审计后由维护者合并。无变化不创建 PR，验证失败不合并。

在 **Settings → Actions → General → Workflow permissions** 中允许 Actions 创建 PR。使用内置 `GITHUB_TOKEN`，无需额外密钥；它创建的 PR 可能不触发 PR CI，因此更新工作流会自行验证实际提交。

如需验证后自动 squash 合并，可设置仓库 Actions 变量 `AUTO_MERGE_UPDATES=true`；默认不自动合并，也不会绕过分支保护。自动更新仅在 `Axolotl-Launcher/homebrew-tap` 运行，Fork 中的 CI 仍可运行。

版本与校验值由 `Casks/axolotl-launcher.rb` 定义。脚本支持单一数字版本、单一 SHA256 和随版本变化的 GitHub Releases URL；遇到不支持的格式会保持原样并报告原因。发布或网络错误会中止更新。审计不代替实际运行测试。

### 本地检查

```bash
python3 -B -m unittest discover -s tests -v
ruby -c Casks/axolotl-launcher.rb
git diff --check
```

CI 会在独立 runner 中注册当前检出内容，并执行 Homebrew 格式和审计检查。本地开发仓库无需与日常使用的 tap 目录绑定。

## English

### Automation

- **Cask CI** runs Ruby syntax checks, Homebrew audits, and updater tests.
- **Update Casks** runs twice daily, manually, and on Cask pushes to `main`. GitHub schedules may be delayed.
- The updater uses `livecheck`, verifies stable GitHub release assets and SHA256 checksums, and rejects drafts, prereleases, repository changes, and checksum mismatches.
- Updates are proposed through PRs. The actual PR commit is checked against the expected contents and audited online before maintainer review. No changes means no PR; failed validation prevents merging.

Allow Actions to create PRs under **Settings → Actions → General → Workflow permissions**. No extra secrets are needed. PRs created with `GITHUB_TOKEN` may not trigger PR CI, so the update workflow validates the actual commit itself.

To enable automatic squash merging after validation, set the repository Actions variable `AUTO_MERGE_UPDATES=true`. Automatic merging is off by default and never bypasses branch protection. Updates run only in `Axolotl-Launcher/homebrew-tap`; CI can still run in forks.

`Casks/axolotl-launcher.rb` defines the version and checksum. The updater supports one numeric version, one SHA256, and a version-dependent GitHub Releases URL. Unsupported formats remain unchanged with a warning; release or network errors abort the update. Audits do not replace runtime testing.

### Local checks

```bash
python3 -B -m unittest discover -s tests -v
ruby -c Casks/axolotl-launcher.rb
git diff --check
```

CI registers the checked-out contents in an isolated runner for Homebrew style and audit checks. The development checkout does not need to be linked to the tap used for normal installations.
