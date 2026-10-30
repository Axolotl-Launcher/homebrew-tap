cask "axolotl-launcher" do
  version "1.10.4"
  sha256 "9f7d32561403a6e3239b664a9abc567b326d1cae5061f26f785511d2b7eecfc2"

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
