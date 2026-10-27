# Axolotl Homebrew Tap

**使用指南 / Usage** · [维护指南 / Maintenance](CONTRIBUTING.md)

[中文](#中文) | [English](#english)

## 中文

[Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) 的官方 Homebrew tap。

1.10.1 发布包声明最低 macOS 为 Intel 10.13、Apple Silicon 11.0；使用本 tap 还需满足 Homebrew 的系统要求。尚未验证旧系统运行兼容性。

### 安装与更新

```bash
brew install --cask Axolotl-Launcher/tap/axolotl-launcher
```

安装命令会自动添加 tap，也可以先运行 `brew tap Axolotl-Launcher/tap`。

更新启动器：

```bash
brew update
brew upgrade --cask Axolotl-Launcher/tap/axolotl-launcher
```

也可使用 `brew upgrade` 更新全部由 Homebrew 管理的软件。应用支持自更新，保留 `auto_updates true` 标记；若旧版 Homebrew 或当前配置跳过了它，可运行 `brew upgrade --cask --greedy Axolotl-Launcher/tap/axolotl-launcher`，或用 `brew outdated --cask --greedy` 检查。

如果应用由 DMG 手动安装、尚未由 Homebrew 管理，可以接管现有应用：

```bash
brew install --cask --adopt Axolotl-Launcher/tap/axolotl-launcher
```

接管前，用 `brew info --cask Axolotl-Launcher/tap/axolotl-launcher` 查看 Cask 版本，并与应用内显示的版本比较。本地版本较旧时先更新应用，较新时等待 tap 更新。`--adopt` 不会升级应用；版本一致仍无法接管时，请核对来源和安装位置，不要强制覆盖。

### 信任检查

本 tap 由 Axolotl 组织维护，但不属于 Homebrew 官方仓库。Cask 是可执行的 Ruby 安装定义，因此 Homebrew 要求明确授权后才能加载。

上方完整的安装命令会自动授权该 Cask。如果先运行 `brew info`、`brew livecheck` 或 `brew audit`，遇到 `untrusted tap` 提示，请确认仓库来自 `Axolotl-Launcher/homebrew-tap`，再执行：

```bash
brew tap Axolotl-Launcher/tap
brew trust --cask Axolotl-Launcher/tap/axolotl-launcher
```

然后重试原命令。这仅授权 Axolotl Cask，不会授权整个 tap 或安装应用；授权也不代表 Homebrew 对软件安全性的认证。详见 [Homebrew 信任机制](https://docs.brew.sh/Tap-Trust)。

### 应用

<!-- casks:zh:start -->
| 应用 | 简介 | 安装命令 |
|---|---|---|
| [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) | Free and open-source Minecraft launcher | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` |
<!-- casks:zh:end -->

## English

The official Homebrew tap for [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl).

The 1.10.1 release declares macOS 10.13 for Intel and 11.0 for Apple Silicon. Homebrew's own system requirements also apply; runtime compatibility on older systems has not been tested.

### Installation and updates

```bash
brew install --cask Axolotl-Launcher/tap/axolotl-launcher
```

The command adds the tap automatically. You can also run `brew tap Axolotl-Launcher/tap` first.

Update the launcher:

```bash
brew update
brew upgrade --cask Axolotl-Launcher/tap/axolotl-launcher
```

Use `brew upgrade` to update all software managed by Homebrew. The app supports self-updating, so the Cask keeps `auto_updates true`. If an older Homebrew version or your configuration skips it, use `brew upgrade --cask --greedy Axolotl-Launcher/tap/axolotl-launcher`, or check with `brew outdated --cask --greedy`.

For an app installed manually from a DMG and not yet managed by Homebrew:

```bash
brew install --cask --adopt Axolotl-Launcher/tap/axolotl-launcher
```

Compare `brew info --cask Axolotl-Launcher/tap/axolotl-launcher` with the version shown in the app. Update an older app first, or wait for the tap to catch up with a newer app. Adoption does not upgrade the app. If matching versions still fail, check the source and installation location rather than forcing an overwrite.

### Trust checks

This tap is maintained by Axolotl, but is outside Homebrew's official repositories. Casks are executable Ruby installation definitions, so Homebrew requires permission to load them.

The fully qualified installation command above grants permission for this Cask automatically. If you run `brew info`, `brew livecheck`, or `brew audit` first and see `untrusted tap`, verify that the repository is `Axolotl-Launcher/homebrew-tap`, then run:

```bash
brew tap Axolotl-Launcher/tap
brew trust --cask Axolotl-Launcher/tap/axolotl-launcher
```

Retry the original command. This trusts only the Axolotl Cask, without trusting the entire tap or installing the app. Trust is not a Homebrew security certification. See [Homebrew Tap Trust](https://docs.brew.sh/Tap-Trust).

### Applications

<!-- casks:en:start -->
| Application | Description | Installation |
|---|---|---|
| [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) | Free and open-source Minecraft launcher | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` |
<!-- casks:en:end -->
