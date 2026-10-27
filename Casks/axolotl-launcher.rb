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

  depends_on macos: ">= :ventura"

  app "Axolotl Launcher.app"
end
