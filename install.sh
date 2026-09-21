#!/usr/bin/env bash
# Install Galaxy Book 10.6 speaker/jack audio support. Run as root: sudo ./install.sh
set -euo pipefail; cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || exec sudo "$0" "$@"
command -v hda-verb >/dev/null || { echo "hda-verb missing: pacman -S alsa-tools (Arch) / apt install alsa-tools (Debian)"; exit 1; }
install -d -m 755 /usr/local/lib/galaxybook-audio /etc/systemd/system-sleep
install -m 755 scripts/initializeALC298.py scripts/setHeadphone.py scripts/amp_replay.py /usr/local/lib/galaxybook-audio/
install -m 644 scripts/verbUI.py scripts/amp_ops.json /usr/local/lib/galaxybook-audio/
install -m 755 bin/galaxybook-audio-init bin/galaxybook-jack-watch /usr/local/bin/
install -m 644 systemd/galaxybook-audio.service systemd/galaxybook-jack-watch.service /etc/systemd/system/
install -m 755 systemd/galaxybook-audio.sleep /etc/systemd/system-sleep/galaxybook-audio
u=${SUDO_USER:-$USER}; h=$(getent passwd "$u" | cut -d: -f6)
install -d -m 755 -o "$u" -g "$u" "$h/.config/wireplumber/wireplumber.conf.d"
install -m 644 -o "$u" -g "$u" wireplumber/51-alc298-no-suspend.conf "$h/.config/wireplumber/wireplumber.conf.d/"
systemctl daemon-reload; systemctl enable --now galaxybook-audio.service galaxybook-jack-watch.service
echo "Installed. Speakers should work now; reboot once to confirm boot-time init. Log out/in for the WirePlumber rule."
