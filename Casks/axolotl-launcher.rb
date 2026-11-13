cask "axolotl-launcher" do
  version "1.11.0"
  sha256 "985e81b73f0c6ba47cb5532a7bb0c3546b2fa0672cedaa14d4f379487cfd1b6e"

  url "https://github.com/Axolotl-Launcher/Axolotl/releases/download/v#{version}/Axolotl.Launcher_#{version}_universal.dmg"
  name "Axolotl Launcher"
  desc "Free and open-source Minecraft launcher"
  homepage "https://github.com/Axolotl-Launcher/Axolotl"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates true
  # v1.10.1 declares 10.13 (Intel) / 11.0 (ARM); an explicit minimum is redundant.
  depends_on :macos

  app "Axolotl Launcher.app"
end
