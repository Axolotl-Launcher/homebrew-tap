# Axolotl Homebrew Tap

**使用指南 / Usage** · [维护指南 / Maintenance](CONTRIBUTING.md)

[中文](#中文) | [English](#english)

## 中文

[Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) 的官方 Homebrew tap。

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

也可使用 `brew upgrade` 更新全部由 Homebrew 管理的软件。

如果应用由 DMG 手动安装、尚未由 Homebrew 管理，可以接管现有应用：

```bash
brew install --cask --adopt Axolotl-Launcher/tap/axolotl-launcher
```

接管前，用 `brew info --cask Axolotl-Launcher/tap/axolotl-launcher` 查看 Cask 版本，并与应用内显示的版本比较。本地版本较旧时先更新应用，较新时等待 tap 更新。`--adopt` 不会升级应用；版本一致仍无法接管时，请核对来源和安装位置，不要强制覆盖。

### 应用

<!-- casks:zh:start -->
| 应用 | 简介 | 安装命令 |
|---|---|---|
| [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) | Minecraft launcher | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` |
<!-- casks:zh:end -->

## English

The official Homebrew tap for [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl).

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

Use `brew upgrade` to update all software managed by Homebrew.

For an app installed manually from a DMG and not yet managed by Homebrew:

```bash
brew install --cask --adopt Axolotl-Launcher/tap/axolotl-launcher
```

Compare `brew info --cask Axolotl-Launcher/tap/axolotl-launcher` with the version shown in the app. Update an older app first, or wait for the tap to catch up with a newer app. Adoption does not upgrade the app. If matching versions still fail, check the source and installation location rather than forcing an overwrite.

### Applications

<!-- casks:en:start -->
| Application | Description | Installation |
|---|---|---|
| [Axolotl Launcher](https://github.com/Axolotl-Launcher/Axolotl) | Minecraft launcher | `brew install --cask Axolotl-Launcher/tap/axolotl-launcher` |
<!-- casks:en:end -->
