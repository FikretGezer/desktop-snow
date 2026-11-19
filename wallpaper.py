"""
Paints winter landscape wallpapers from scratch (no images downloaded) and
sets them as the Windows desktop background.

Four times of day: dawn, day, dusk, night. Saved as BMP files in ./wallpapers.
"""
import ctypes
import math
import os
import sys
import random
import struct

HERE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
OUT = os.path.join(HERE, "wallpapers")

PALETTES = {
    #        sky top,        sky bottom,     far mtn,        mid mtn,        forest,        snow,           snow shade,     lights
    "night": ((10, 16, 46),  (60, 62, 125),  (72, 80, 145),  (44, 52, 108),  (20, 28, 60),  (150, 165, 218), (108, 122, 186), True),
    "dawn":  ((66, 78, 150), (252, 184, 160), (156, 144, 186), (112, 106, 162), (52, 56, 98), (238, 218, 228), (196, 180, 210), True),
    "day":   ((80, 145, 222), (205, 228, 248), (172, 192, 224), (120, 146, 192), (36, 68, 84), (246, 249, 255), (204, 220, 242), False),
    "dusk":  ((36, 36, 98),  (242, 132, 100), (124, 92, 142), (86, 66, 122),  (34, 30, 70),  (204, 172, 204), (160, 132, 176), True),
}


def phase_for_hour(h):
    if 5 <= h < 8:
        return "dawn"
    if 8 <= h < 17:
        return "day"
    if 17 <= h < 20:
        return "dusk"
    return "night"


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.rows = [bytearray(w * 3) for _ in range(h)]
        self.sky = [(0, 0, 0)] * h

    @staticmethod
    def bgr(c):
        return bytes((c[2], c[1], c[0]))

    def span(self, y, x0, x1, c):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0)); x1 = min(self.w, int(x1))
        if x1 > x0:
            self.rows[y][x0 * 3:x1 * 3] = self.bgr(c) * (x1 - x0)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1)):
            self.span(y, x0, x1, c)

    def circle(self, cx, cy, r, c):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = math.sqrt(max(0, r * r - dy * dy))
            self.span(int(cy) + dy, cx - dx, cx + dx, c)

    def glow(self, cx, cy, r, c, strength=0.6):
        """Additive soft light blended onto whatever is already painted."""
        b, g, rr_ = c[2], c[1], c[0]
        r2 = r * r
        for y in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 1)):
            dy2 = (y - cy) ** 2
            if dy2 >= r2:
                continue
            row = self.rows[y]
            half = math.sqrt(r2 - dy2)
            for x in range(max(0, int(cx - half)), min(self.w, int(cx + half))):
                t = strength * (1 - math.sqrt((x - cx) ** 2 + dy2) / r) ** 2
                i = x * 3
                row[i] = int(row[i] + (b - row[i]) * t)
                row[i + 1] = int(row[i + 1] + (g - row[i + 1]) * t)
                row[i + 2] = int(row[i + 2] + (rr_ - row[i + 2]) * t)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(max(0, int(min(ys))), min(self.h, int(max(ys)) + 1)):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
                if (y1 <= yc < y2) or (y2 <= yc < y1):
                    xs.append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.span(y, xs[i], xs[i + 1], c)

    def save_bmp(self, path):
        pad = (4 - (self.w * 3) % 4) % 4
        size = 54 + (self.w * 3 + pad) * self.h
        with open(path, "wb") as f:
            f.write(b"BM" + struct.pack("<IHHI", size, 0, 0, 54))
            f.write(struct.pack("<IiiHHIIiiII", 40, self.w, self.h, 1, 24, 0, size - 54, 2835, 2835, 0, 0))
            for row in reversed(self.rows):
                f.write(row)
                f.write(b"\0" * pad)


def ridge(w, base, amp, seed, freq, step=8):
    rnd = random.Random(seed)
    waves = [(rnd.uniform(0.5, 1.0), rnd.uniform(0, 6.28), f) for f in freq]
    pts = []
    for x in range(-step, w + step * 2, step):
        y = base
        for j, (a, ph, f) in enumerate(waves):
            v = 1 - abs(math.sin(x / w * f * 3.14 + ph))   # sharp peaks
            y -= amp * a * v ** (1.6 if j == 0 else 1.0) / (1 + j * 0.8)
        pts.append((x, y))
    return pts


def pine(cv, x, base, hgt, col, snow, caps=True):
    tw = hgt * 0.08
    cv.rect(x - tw, base - hgt * 0.15, x + tw, base, mix(col, (40, 25, 15), 0.5))
    for i in range(4):
        top = base - hgt + i * hgt * 0.2
        bot = top + hgt * 0.38
        half = hgt * (0.16 + i * 0.07)
        cv.poly([(x, top), (x + half, bot), (x - half, bot)], col)
        if caps:
            cv.poly([(x, top), (x + half * 0.45, top + hgt * 0.13), (x - half * 0.45, top + hgt * 0.13)], snow)
            cv.poly([(x + half * 0.4, bot - hgt * 0.03), (x + half, bot), (x + half * 0.2, bot)], snow)


def cabin(cv, x, base, s, P):
    wall = (110, 62, 40); dark = (70, 38, 26)
    sky, snow, shade, lights = P[0], P[5], P[6], P[7]
    w, h = 230 * s, 130 * s
    if lights:
        cv.glow(x, base - h * 0.5, 260 * s, (255, 180, 90), 0.35)
    cv.rect(x - w / 2, base - h, x + w / 2, base, wall)
    for i in range(1, 7):  # log lines
        cv.rect(x - w / 2, base - h + i * h / 7, x + w / 2, base - h + i * h / 7 + 2 * s, dark)
    # roof
    cv.poly([(x - w / 2 - 28 * s, base - h), (x, base - h - 105 * s), (x + w / 2 + 28 * s, base - h)], dark)
    cv.poly([(x - w / 2 - 34 * s, base - h + 4 * s), (x, base - h - 112 * s),
             (x + w / 2 + 34 * s, base - h + 4 * s), (x + w / 2 + 20 * s, base - h - 10 * s),
             (x, base - h - 92 * s), (x - w / 2 - 20 * s, base - h - 10 * s)], snow)
    # chimney
    cv.rect(x + 50 * s, base - h - 110 * s, x + 76 * s, base - h - 50 * s, (90, 60, 55))
    cv.rect(x + 46 * s, base - h - 118 * s, x + 80 * s, base - h - 108 * s, snow)
    # windows + door
    win = (255, 196, 96) if lights else (60, 80, 110)
    for wx in (x - 72 * s, x + 50 * s):
        cv.rect(wx - 2 * s, base - h * 0.72 - 2 * s, wx + 42 * s, base - h * 0.32 + 2 * s, dark)
        cv.rect(wx, base - h * 0.72, wx + 40 * s, base - h * 0.32, win)
        cv.rect(wx + 19 * s, base - h * 0.72, wx + 21 * s, base - h * 0.32, dark)
        cv.rect(wx - 4 * s, base - h * 0.32, wx + 44 * s, base - h * 0.28, snow)
    cv.rect(x - 18 * s, base - h * 0.62, x + 18 * s, base, dark)
    if lights:  # string lights under eaves
        cols = [(255, 80, 80), (255, 220, 90), (90, 220, 120), (90, 160, 255)]
        n = 16
        for i in range(n):
            lx = x - w / 2 - 20 * s + i * (w + 40 * s) / (n - 1)
            cv.circle(lx, base - h + 6 * s + math.sin(i) * 2 * s, 3 * s, cols[i % 4])


def fence(cv, x0, x1, base, s, snow):
    wood = (120, 78, 50)
    cv.rect(x0, base - 34 * s, x1, base - 28 * s, wood)
    cv.rect(x0, base - 18 * s, x1, base - 12 * s, wood)
    cv.rect(x0, base - 37 * s, x1, base - 34 * s, snow)
    x = x0
    while x < x1:
        cv.rect(x, base - 46 * s, x + 7 * s, base, wood)
        cv.rect(x - 1 * s, base - 50 * s, x + 8 * s, base - 45 * s, snow)
        x += 46 * s


def render(w, h, phase, path):
    P = PALETTES[phase]
    s = h / 1080
    cv = Canvas(w, h)
    rnd = random.Random(7)
    top, bot = P[0], P[1]
    for y in range(h):
        c = mix(top, bot, min(1, y / (h * 0.62)))
        cv.sky[y] = c
        cv.span(y, 0, w, c)
    if phase in ("night", "dusk"):
        for _ in range(int(500 * w / 1920)):
            sx, sy = rnd.uniform(0, w), rnd.uniform(0, h * 0.5) ** 1.1 / (h * 0.5) ** 0.1
            b = rnd.uniform(0.4, 1.0) * (1 if phase == "night" else 0.6)
            cv.circle(sx, sy, rnd.choice((0, 0, 1)) * s + 0.6, mix(cv.sky[int(sy)], (255, 255, 240), b))
    # moon / sun
    if phase == "night":
        cv.glow(w * 0.72, h * 0.16, 170 * s, (230, 230, 255), 0.45)
        cv.circle(w * 0.72, h * 0.16, 44 * s, (250, 246, 220))
        for dx, dy, rr in ((-12, -8, 9), (14, 10, 7), (6, -16, 5)):  # craters
            cv.circle(w * 0.72 + dx * s, h * 0.16 + dy * s, rr * s, (228, 222, 196))
    elif phase == "day":
        cv.glow(w * 0.78, h * 0.15, 220 * s, (255, 255, 230), 0.6)
        cv.circle(w * 0.78, h * 0.15, 52 * s, (255, 252, 230))
    else:
        sx = w * (0.25 if phase == "dawn" else 0.75)
        cv.glow(sx, h * 0.52, 360 * s, (255, 210, 150), 0.7)
        cv.circle(sx, h * 0.52, 60 * s, (255, 230, 180))
    # mountains
    far = ridge(w, h * 0.55, h * 0.30, 1, (1.3, 2.7, 6.1))
    cv.poly(far + [(w + 20, h), (-20, h)], mix(P[2], P[5], 0.6))      # snowy caps
    cv.poly([(x, y + 55 * s) for x, y in ridge(w, h * 0.55, h * 0.26, 1, (1.3, 2.7, 6.1))]
            + [(w + 20, h), (-20, h)], P[2])
    mid = ridge(w, h * 0.66, h * 0.20, 2, (2.1, 4.3, 9.7))
    cv.poly(mid + [(w + 20, h), (-20, h)], mix(P[3], P[5], 0.45))
    cv.poly([(x, y + 35 * s) for x, y in ridge(w, h * 0.66, h * 0.17, 2, (2.1, 4.3, 9.7))]
            + [(w + 20, h), (-20, h)], P[3])
    # distant forest
    for i in range(int(110 * w / 1920)):
        x = rnd.uniform(0, w)
        pine(cv, x, h * 0.70 + rnd.uniform(-6, 10) * s, rnd.uniform(40, 80) * s, P[4], mix(P[4], P[5], 0.4), caps=False)
    # snow field with drifts
    field = ridge(w, h * 0.80, h * 0.08, 3, (1.1, 2.9), 6)
    cv.poly([(x, y - h * 0.06) for x, y in field] + [(w + 20, h), (-20, h)], P[6])
    cv.poly(field + [(w + 20, h), (-20, h)], P[5])
    # cabin + fence
    base = h * 0.83
    cabin(cv, w * 0.30, base, s, P)
    fence(cv, w * 0.42, w * 0.70, h * 0.86, s, P[5])
    # foreground pines
    for x, hh in ((w * 0.06, 420), (w * 0.14, 300), (w * 0.88, 460), (w * 0.95, 330), (w * 0.52, 190)):
        pine(cv, x, h * 0.93, hh * s, mix(P[4], (20, 60, 40), 0.35), P[5])
    if P[7]:
        cv.glow(w * 0.52, h * 0.93 - 190 * s, 60 * s, (255, 220, 120), 0.25)
    # foreground drift
    fg = ridge(w, h * 1.0, h * 0.07, 4, (1.7, 3.3), 6)
    cv.poly(fg + [(w + 20, h + 5), (-20, h + 5)], mix(P[5], (255, 255, 255), 0.3))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv.save_bmp(path)


def get_wallpaper():
    buf = ctypes.create_unicode_buffer(520)
    ctypes.windll.user32.SystemParametersInfoW(0x73, 520, buf, 0)
    return buf.value


def set_wallpaper(path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)


def ensure(phase, w, h):
    path = os.path.join(OUT, f"{phase}_{w}x{h}.bmp")
    if not os.path.exists(path):
        render(w, h, phase, path)
    return path


if __name__ == "__main__":
    import sys
    ph = sys.argv[1] if len(sys.argv) > 1 else "night"
    render(1920, 1080, ph, os.path.join(OUT, f"preview_{ph}.bmp"))
    print("done")
