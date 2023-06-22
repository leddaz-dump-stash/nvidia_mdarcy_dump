#!/vendor/bin/sh
if ! applypatch --check EMMC:/dev/block/platform/sdhci-tegra.3/by-name/SOS$(getprop ro.boot.slot_suffix):28835840:f1e9cd0163e4c953bd7d5f3a08c380c728bd0e4a; then
  applypatch  \
          --patch /vendor/recovery-from-boot.p \
          --source EMMC:/dev/block/platform/sdhci-tegra.3/by-name/LNX$(getprop ro.boot.slot_suffix):26738688:4cacdb77a5735e60fb64c73feac2e0cec59af1dc \
          --target EMMC:/dev/block/platform/sdhci-tegra.3/by-name/SOS$(getprop ro.boot.slot_suffix):28835840:f1e9cd0163e4c953bd7d5f3a08c380c728bd0e4a && \
      log -t recovery "Installing new recovery image: succeeded" || \
      log -t recovery "Installing new recovery image: failed"
else
  log -t recovery "Recovery image already installed"
fi
