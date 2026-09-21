#!/usr/bin/env python3
"""Replay the Windows driver's amp routine (RTKVHD64.sys 0x43132c) for the
Galaxy Book 10.6 (144d:c150): two I2C amps at 0x34/0x35 behind the ALC298.

Ops come from amp_ops.json (extracted from the driver, not hand-typed).
Primitives mirror the driver's 0x49520 wrapper exactly:
  wait busy -> nid6/0x73e/0x80 -> 0x26|=0x4000 -> 0x22=addr -> 0x23=reg
  -> data -> 0x26=opcode -> nid6/0x73e/0x00 -> 0x26&=~0x4000
  opcodes: w8 0xb010, w16 0xb012, w24 0xb016, read8 0xa018 (result in 0x28)

usage: sudo amp_replay.py [MODE0 MODE2 MODE1 ...] [--verify] [--verbose]
"""
import json, sys, time, os
sys.path.insert(0, "/usr/local/lib/galaxybook-audio")
from verbUI import execVerb, set_coef, get_coef, update_coef

AMPS = (0x34, 0x35)
OPS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "amp_ops.json")))


def _wait():
    for _ in range(100):
        if not (get_coef(0x26) & 0x4000): return True
        time.sleep(0.001)
    return False

def _begin(addr, reg):
    _wait(); execVerb(0x6, 0x73e, 0x80); update_coef(0x26, 0x4000)
    set_coef(0x22, addr); set_coef(0x23, reg)

def _end():
    execVerb(0x6, 0x73e, 0x00); update_coef(0x26, 0x0, 0x4000)

def w8(addr, reg, val):
    _begin(addr, reg); set_coef(0x25, val & 0xff); set_coef(0x26, 0xb010); _end()

def w16(addr, reg, val):
    _begin(addr, reg); set_coef(0x25, val & 0xffff); set_coef(0x26, 0xb012); _end()

def w24(addr, reg, val):
    _begin(addr, reg); set_coef(0x25, val & 0xffff); set_coef(0x24, (val >> 16) & 0xff)
    set_coef(0x26, 0xb016); _end()

def r8(addr, reg):
    _begin(addr, reg); set_coef(0x26, 0xa018); time.sleep(0.002); _wait()
    v = get_coef(0x28) & 0xff; _end(); return v

def rmw(addr, reg, mask, val):
    if mask == 0xff: return w8(addr, reg, val)
    old = r8(addr, reg); new = (val & mask) | (old & ~mask & 0xff)
    w8(addr, reg, new); return old, new


def run(mode, verbose=False):
    ops = OPS[mode]
    for addr in AMPS:
        n = 0
        for op in ops:
            k = op[0]
            if k == "delay_ms": time.sleep(op[1] / 1000.0); continue
            n += 1
            if k == "w8":   w8(addr, op[1], op[2]);  d = f"w8  {op[1]:#04x}={op[2]:#04x}"
            elif k == "w16": w16(addr, op[1], op[2]); d = f"w16 {op[1]:#04x}={op[2]:#06x}"
            elif k == "w24": w24(addr, op[1], op[2]); d = f"w24 {op[1]:#04x}={op[2]:#08x}"
            elif k == "rmw": o = rmw(addr, op[1], op[2], op[3]); d = f"rmw {op[1]:#04x} &{op[2]:#04x} <-{op[3]:#04x} ({o[0]:#04x}->{o[1]:#04x})" if isinstance(o, tuple) else f"rmw {op[1]:#04x}"
            if verbose: print(f"  {mode} amp {addr:#04x}: {d}")
        print(f"{mode} -> amp {addr:#04x}: {n} ops applied")


def verify():
    checks = {0x1f: 0x9a, 0x20: 0x97, 0x21: 0x64, 0x25: 0x04, 0xf4: None, 0x22: None}
    for addr in AMPS:
        got = {r: r8(addr, r) for r in checks}
        print(f"verify amp {addr:#04x}: " + "  ".join(f"{r:#04x}={v:#04x}{'' if checks[r] is None or checks[r]==v else ' (exp %#04x)'%checks[r]}" for r, v in got.items()))


if __name__ == "__main__":
    modes = [a for a in sys.argv[1:] if a.startswith("MODE")]
    for m in modes or ["MODE0", "MODE2", "MODE1"]:
        run(m, "--verbose" in sys.argv)
    if "--verify" in sys.argv: verify()
