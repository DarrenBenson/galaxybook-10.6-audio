#!/usr/bin/env bash
set -euo pipefail; [ "$(id -u)" = 0 ] || exec sudo "$0" "$@"
systemctl disable --now galaxybook-audio.service galaxybook-jack-watch.service 2>/dev/null || true
rm -f /etc/systemd/system/galaxybook-audio.service /etc/systemd/system/galaxybook-jack-watch.service /etc/systemd/system-sleep/galaxybook-audio
rm -f /usr/local/bin/galaxybook-audio-init /usr/local/bin/galaxybook-jack-watch; rm -rf /usr/local/lib/galaxybook-audio
u=${SUDO_USER:-$USER}; h=$(getent passwd "$u" | cut -d: -f6); rm -f "$h/.config/wireplumber/wireplumber.conf.d/51-alc298-no-suspend.conf"
systemctl daemon-reload; echo "Removed. Speakers and jack return to silent (stock) on next boot."
