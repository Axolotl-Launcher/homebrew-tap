cask "axolotl-launcher" do
  version "1.10.1"
  sha256 "7a3c306db728f48488ee0b2317bab436fdbc471d5aba717e8eb15ef450b593b8"

  url "https://github.com/Axolotl-Launcher/Axolotl/releases/download/v#{version}/Axolotl.Launcher_#{version}_universal.dmg"
  name "Axolotl Launcher"
  desc "Minecraft launcher"
  homepage "https://github.com/Axolotl-Launcher/Axolotl"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates true
  depends_on :macos

  app "Axolotl Launcher.app"
end
