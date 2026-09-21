# Samsung Galaxy Book 10.6 — speakers and headphone jack on Linux

Working internal speakers and 3.5 mm jack for the **Samsung Galaxy Book 10.6**
(2017, SM-W620 Wi-Fi / SM-W627 LTE), Realtek ALC298, codec subsystem ID
**`144d:c150`**. Realtek's own driver database names this audio design
`SS_TabPro`, so the **Galaxy TabPro S** very likely shares it — reports welcome.

Tested on Omarchy 4.0.4 (Arch), kernel 7.2.5, PipeWire 1.6.8. Nothing here is
distribution-specific beyond the install paths.

## The symptom

Everything looks fine and nothing comes out. The codec enumerates, PipeWire
streams to it, the DMA counter advances at exactly real time, nothing is
muted — and both the speakers and the jack are silent. Input (headset mic)
works. `dmesg` shows:

```
snd_hda_codec_alc269 hdaudioC0D0: autoconfig for ALC298: line_outs=1 (0x17/0x0/0x0/0x0/0x0) type:speaker
snd_hda_codec_alc269 hdaudioC0D0:    hp_outs=0 (0x0/0x0/0x0/0x0/0x0)
```

None of the kernel's Samsung quirks (`alc298-samsung-amp`, `-v2-2-amps`,
`-v2-4-amps`) help: they target other Galaxy Books with other amplifiers.

## Why

The firmware leaves two things unconfigured that only the Windows driver sets:

1. **The ALC298's analog output stage** (vendor COEF registers).
2. **Two I²C speaker amplifiers at addresses `0x34` and `0x35`** on the codec's
   own I²C master. They are invisible to ACPI (no `_HID`, no GPIO, an empty
   NHLT) and to the kernel; they only exist inside the Windows driver's
   per-device table.

Speakers and jack share codec pin `0x17`; the codec's routing selects which
one is live, and the jack is detected on mic pin `0x18`.

## What this installs

| File | Role |
|---|---|
| `bin/galaxybook-audio-init [0\|1]` | applies the full recipe: codec init → routing (`0` speakers / `1` jack) → amplifier registers |
| `systemd/galaxybook-audio.service` | runs it at boot |
| `systemd/galaxybook-audio.sleep` | runs it again on resume (codec and amp state do not survive suspend) |
| `bin/galaxybook-jack-watch` + `.service` | polls jack-sense on pin `0x18` once a second and flips routing on plug/unplug |
| `wireplumber/51-alc298-no-suspend.conf` | stops WirePlumber suspending the ALSA node, which powers the output stage back down |
| `scripts/` | the pieces the wrapper calls (see Credits) |

## Install

```
sudo pacman -S alsa-tools        # for hda-verb (Debian/Ubuntu: apt install alsa-tools)
git clone https://github.com/<you>/galaxybook-10.6-audio
cd galaxybook-10.6-audio && sudo ./install.sh
```

Speakers work immediately; reboot once to confirm the boot-time path. To
remove everything: `sudo ./uninstall.sh`.

If speakers ever go quiet, `sudo galaxybook-audio-init` reapplies the recipe;
`journalctl -b -u galaxybook-audio -t galaxybook-jack` shows what ran.

## How it works, briefly

* `scripts/initializeALC298.py` / `setHeadphone.py` / `verbUI.py` are Aurélien
  Croc's GPL-2.0 tooling for the **Galaxy Book 12** — a codec output-stage init
  and a speaker/jack routing switch, both reverse-engineered from the Windows
  driver via QEMU. The 10.6's codec is configured identically; only the
  amplifiers differ (the Book 12 has Maxim amps at `0x31`/`0x34`).
* `scripts/amp_ops.json` is the 10.6's amplifier initialisation: **116
  register operations** (8/16/24-bit writes, read-modify-writes, delays)
  extracted programmatically from the Windows driver's device-specific routine
  (`RTKVHD64.sys`, the `cmp ecx,0xc150` case) in Samsung's
  `GB10.6_DriverPackage_20180502.zip`. `amp_replay.py` applies them to both
  amps through the same I²C-over-COEF primitive the driver uses (opcodes
  `0xb010`/`0xb012`/`0xb016` for 8/16/24-bit writes, `0xa018` for reads).
* Mode 0 must be applied completely — its five 16-bit clock/format words and
  eight read-modify-writes are what make the configuration stick after the
  chip's reset. Skipping them leaves the amps at defaults and silent.
* The amplifier tables are configuration data taken from a proprietary
  driver, published for interoperability in the same spirit as the kernel's
  own Samsung amp quirks and the Book 12 projects this builds on.

Two things worth knowing if you adapt this to another model: a COEF `0x26`
status of `0xb000` after a write is **not** an acknowledgement (empty addresses
return it too); a present device echoes its registers back on read, an empty
address reads `0xff`.

## Notes

* The internal microphone (a PDM digital mic on pin `0x12`) works out of the
  box and is unaffected by this recipe. **Do not drive the codec's GPIOs**
  (verbs `0x715`–`0x717`): doing so wedges the mic into a full-scale rail until
  the codec init runs again or the machine reboots.

## Not solved

* Jack switching is polled (≤1 s latency), not event-driven.
* Whether the amps auto-standby after long idle is unverified.

## Credits

* **Aurélien Croc (AP²C)** — the codec sequences and the I²C-over-COEF
  primitive, from <https://github.com/Teetoow/SamsungGalaxyBook12> (GPL-2.0).
* fxjosemi's <https://github.com/fxjosemi/Samsung-Galaxy-Book-12-Linux> for
  documenting the shared-pin / mic-pin-detect layout.

GPL-2.0, see `LICENSE`.
