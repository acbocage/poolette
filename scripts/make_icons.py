#!/usr/bin/env python3
"""Génère les icônes PNG de Poolette (stdlib uniquement) à partir du même dessin que icon.svg."""
import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "icons"
C1, C2 = (10, 110, 142), (25, 182, 204)
WHITE, GREEN = (255, 255, 255), (30, 158, 90)


def in_round_rect(x, y, r=112, size=512):
    cx = min(max(x, r), size - r)
    cy = min(max(y, r), size - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def wave_hit(x, y, y0, a=26.0, period=240.0, x0=92.0, x1=420.0, half=15.0):
    if x0 - half <= x <= x1 + half:
        xc = min(max(x, x0), x1)
        yc = y0 - a * math.sin(2 * math.pi * (xc - x0) / period)
        slope = -a * 2 * math.pi / period * math.cos(2 * math.pi * (xc - x0) / period)
        if x0 <= x <= x1:
            return abs(y - yc) / math.sqrt(1 + slope * slope) <= half
        return math.hypot(x - xc, y - yc) <= half
    return False


def pixel(x, y, maskable):
    """x, y en repère 512. Retourne (r, g, b, a)."""
    if not maskable and not in_round_rect(x, y):
        return (0, 0, 0, 0)
    t = (x + y) / 1024.0
    bg = tuple(int(C1[i] + (C2[i] - C1[i]) * t) for i in range(3))
    if maskable:  # contenu réduit à 80 % au centre (zone de sécurité)
        x, y = (x - 256) / 0.8 + 256, (y - 256) / 0.8 + 256
    d = math.hypot(x - 352, y - 170)
    if d <= 34:
        return GREEN + (255,)
    if d <= 54:
        return WHITE + (255,)
    if wave_hit(x, y, 292):
        return WHITE + (255,)
    if wave_hit(x, y, 372):
        return tuple(int(bg[i] * 0.3 + 255 * 0.7) for i in range(3)) + (255,)
    return bg + (255,)


def render(size, maskable=False, ss=2):
    rows = []
    scale = 512.0 / size
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    r, g, b, a = pixel((px + (sx + 0.5) / ss) * scale, (py + (sy + 0.5) / ss) * scale, maskable)
                    acc[0] += r * a; acc[1] += g * a; acc[2] += b * a; acc[3] += a
            n = ss * ss
            if acc[3] == 0:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes((acc[0] // acc[3], acc[1] // acc[3], acc[2] // acc[3], acc[3] // n))
        rows.append(bytes(row))
    return rows


def write_png(path, size, rows):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size, mask in (("icon-192.png", 192, False), ("icon-512.png", 512, False),
                             ("icon-maskable-512.png", 512, True), ("apple-touch-icon.png", 180, True)):
        write_png(OUT / name, size, render(size, mask))
        print("écrit", name)
