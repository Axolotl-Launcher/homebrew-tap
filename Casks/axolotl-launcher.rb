cask "axolotl-launcher" do
  version "1.10.1"
  sha256 "7a3c306db728f48488ee0b2317bab436fdbc471d5aba717e8eb15ef450b593b8"

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

  # Preserve instances, saves, servers, backups, and the launcher database.
  zap trash: [
    "~/Library/Application Support/red.ghs.axolotl/app-window-state.json",
    "~/Library/Application Support/red.ghs.axolotl/launcher_logs",
    "~/Library/Caches/red.ghs.axolotl",
    "~/Library/HTTPStorages/red.ghs.axolotl.binarycookies",
    "~/Library/Preferences/red.ghs.axolotl.plist",
    "~/Library/WebKit/red.ghs.axolotl",
  ]
end
