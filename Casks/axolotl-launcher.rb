cask "axolotl-launcher" do
  version "1.10.5"
  sha256 "af95e133d14c304b362ac3a83f74657e26c44ea2cae82cbb21adfcb0d8fe8708"

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
