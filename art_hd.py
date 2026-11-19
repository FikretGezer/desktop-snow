"""Smooth, shaded cartoon art for yeti, snowplow, gift train, snowman and tree.

Everything is drawn with Pillow at 4x and downsampled (antialiased), then cached as pygame sprites.
Art is drawn facing right with origin (0, 0) at the bottom centre; flipped for left.
"""
import math
import random
import pygame
from PIL import Image, ImageDraw

SS = 4
INK = (36, 34, 56, 255)
_cache = {}


def _c(c):
    return tuple(int(v) for v in c[:3]) + ((c[3],) if len(c) > 3 else (255,))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def light(c, k):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


def rot_ellipse(cx, cy, rx, ry, ang, n=28):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(t) * ca - ry * math.sin(t) * sa, cy + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
            for t in (i * 2 * math.pi / n for i in range(n))]


class Pen:
    def __init__(self, img, k, ox, oy):
        self.img, self.d, self.k, self.ox, self.oy = img, ImageDraw.Draw(img), k, ox, oy
        self.ow = max(2, int(1.6 * k))

    def _p(self, x, y):
        return ((x + self.ox) * self.k, (y + self.oy) * self.k)

    def _box(self, x0, y0, x1, y1):
        a, b = self._p(x0, y0), self._p(x1, y1)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def O(self, x0, y0, x1, y1, col, ink=True):
        if len(col) > 3 and col[3] < 255:                  # translucent glow: blend, don't overwrite
            layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).ellipse(self._box(x0, y0, x1, y1), fill=_c(col))
            self.img.alpha_composite(layer)
            return
        self.d.ellipse(self._box(x0, y0, x1, y1), fill=_c(col), outline=INK if ink else None,
                       width=self.ow if ink else 0)

    def C(self, x, y, r, col, ink=True):
        self.O(x - r, y - r, x + r, y + r, col, ink)

    def R(self, x0, y0, x1, y1, col, ink=True, rad=3):
        self.d.rounded_rectangle(self._box(x0, y0, x1, y1), rad * self.k, fill=_c(col),
                                 outline=INK if ink else None, width=self.ow if ink else 0)

    def P(self, pts, col, ink=True):
        self.d.polygon([self._p(x, y) for x, y in pts], fill=_c(col), outline=INK if ink else None,
                       width=self.ow if ink else 0)

    def L(self, x0, y0, x1, y1, col, w=2, cap=True):
        a, b = self._p(x0, y0), self._p(x1, y1)
        self.d.line([a, b], fill=_c(col), width=max(1, int(w * self.k)))
        if cap:
            r = w * self.k / 2
            for q in (a, b):
                self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=_c(col))

    def T(self, x0, y0, x1, y1, col, w):
        """outlined thick stroke"""
        self.L(x0, y0, x1, y1, INK, w + 3)
        self.L(x0, y0, x1, y1, col, w)

    def arc(self, cx, cy, r, a0, a1, col, w=1.5):
        self.d.arc(self._box(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=_c(col), width=max(1, int(w * self.k)))

    def ball(self, x0, y0, x1, y1, col, shadow=None):
        """outlined ellipse with soft lower shade and a highlight"""
        w, h = x1 - x0, y1 - y0
        self.O(x0, y0, x1, y1, shadow or shade(col, 0.82))
        self.O(x0 + w * 0.04, y0 + h * 0.02, x1 - w * 0.12, y1 - h * 0.14, col, False)
        self.O(x0 + w * 0.2, y0 + h * 0.12, x0 + w * 0.42, y0 + h * 0.26, light(col, 0.6), False)


def make(fn, bbox, scale, flip, *args):
    """Render fn(pen, *args) inside bbox (x0, y0, x1, y1 relative to origin). Returns (surface, ax, ay)."""
    x0, y0, x1, y1 = bbox
    k = SS * scale
    img = Image.new("RGBA", (max(1, int((x1 - x0) * k)), max(1, int((y1 - y0) * k))), (0, 0, 0, 0))
    fn(Pen(img, k, -x0, -y0), *args)
    w, h = max(1, int((x1 - x0) * scale)), max(1, int((y1 - y0) * scale))
    img = img.resize((w, h), Image.LANCZOS)
    ax = -x0 * scale
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        ax = x1 * scale
    surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
    return surf, ax, -y0 * scale


def cached(key, fn, bbox, scale, flip, *args):
    scale = max(0.2, round(scale * 10) / 10)
    k = (key, scale, flip) + args
    v = _cache.get(k)
    if v is None:
        if len(_cache) > 2500:
            _cache.clear()
        v = _cache[k] = make(fn, bbox, scale, flip, *args)
    return v


# ================================================================ yeti
FUR, FUR_SH, SKIN = (244, 248, 255), (196, 210, 236), (116, 156, 220)


def _yeti(p, f, sk, stomp):
    ph = f * math.pi / 4
    bob = 0 if stomp else abs(math.sin(ph)) * 3
    jump = -math.sin(sk / 11 * math.pi) * 18 if stomp and sk < 11 else 0
    up = stomp and sk < 10
    y = jump - bob
    sw = 0 if stomp else math.sin(ph) * 6
    # far arm + far leg
    if up:
        p.P(rot_ellipse(-16, y - 78, 7, 20, -0.25), FUR_SH)
    else:
        p.P(rot_ellipse(-20 - sw * 0.3, y - 34, 7.5, 18, 0.15 - sw * 0.03), FUR_SH)
    p.O(-14 - sw * 0.6, y - 16 + jump * 0.2, 2 - sw * 0.6, jump, FUR_SH)
    # body
    p.ball(-27, y - 72, 27, y - 6, FUR, FUR_SH)
    for i in range(7):                                       # shaggy fur tufts on the hem
        tx = -22 + i * 7.3
        p.P([(tx - 4, y - 12), (tx, y - 3 - (i % 2) * 2), (tx + 4, y - 12)], FUR, False)
    p.O(-14, y - 46, 14, y - 14, light(SKIN, 0.82), False)  # belly
    # near leg + foot
    p.O(-2 + sw * 0.6, y - 16 + jump * 0.2, 16 + sw * 0.6, jump, FUR)
    fx = 7 + sw * 0.6
    p.O(fx - 6, jump - 6, fx + 12, jump + 1, SKIN)
    for tx in (fx + 2, fx + 6, fx + 10):
        p.C(tx, jump - 3, 1.6, light(SKIN, 0.4), False)
    # head
    hy = y - 60
    for i in range(5):
        tx = -16 + i * 7
        p.P([(tx - 5, hy - 8), (tx + 1, hy - 20 - (i % 2) * 4), (tx + 5, hy - 8)], FUR)
    p.O(-20, hy - 16, 22, hy + 10, FUR, False)
    p.O(-6, hy - 9, 22, hy + 13, SKIN)                       # face
    p.O(-2, hy - 7, 12, hy - 1, light(SKIN, 0.25), False)
    for ex in (3, 13):                                       # eyes
        p.O(ex - 4, hy - 6, ex + 4, hy + 3, (255, 255, 255))
        p.C(ex + 1.5, hy - 1, 2.2, (24, 24, 40), False)
        p.C(ex + 2.3, hy - 2.2, 0.8, (255, 255, 255), False)
    brow = -2 if stomp else 0
    p.L(-1, hy - 8 + brow, 7, hy - 6 - brow, shade(SKIN, 0.5), 2)
    p.L(10, hy - 6 - brow, 17, hy - 8 + brow, shade(SKIN, 0.5), 2)
    p.C(8, hy + 4, 2, shade(SKIN, 0.6), False)               # nose
    if stomp:
        p.O(0, hy + 5, 18, hy + 14, (90, 30, 50))
        p.O(5, hy + 9, 13, hy + 13.5, (240, 110, 130), False)
        p.P([(2, hy + 5.5), (4, hy + 9), (6, hy + 5.5)], (255, 255, 255), False)
        p.P([(12, hy + 5.5), (14, hy + 9), (16, hy + 5.5)], (255, 255, 255), False)
    else:
        p.arc(9, hy + 4, 6, 25, 155, INK, 1.6)
        p.P([(5, hy + 9), (6.5, hy + 12), (8, hy + 9.6)], (255, 255, 255), False)
        p.P([(11, hy + 9.6), (12.5, hy + 12), (14, hy + 9)], (255, 255, 255), False)
    p.O(-2, hy + 3, 3, hy + 6, (255, 160, 190), False)
    p.O(17, hy + 3, 22, hy + 6, (255, 160, 190), False)
    # near arm
    if up:
        p.P(rot_ellipse(22, y - 80, 7.5, 21, 0.25), FUR)
        p.C(25, y - 101, 6, SKIN)
    else:
        p.P(rot_ellipse(22 + sw * 0.3, y - 34, 7.5, 18, -0.15 + sw * 0.03), FUR)
        p.C(25 + sw * 0.6, y - 18, 5.5, SKIN)


def yeti(dir_, t, stomp, timer, s):
    f = int(t * 0.08) % 8 if not stomp else 0
    sk = min(11, int(timer / 4)) if stomp else 0
    return cached("yeti", _yeti, (-36, -128, 40, 6), s, dir_ < 0, f, sk, stomp)


# ================================================================ snowplow
YEL = (255, 198, 40)


def _plow(p, wf, beacon, hump):
    # snow pushed in front of the blade
    if hump > 0:
        hx = 50 + hump * 0.45
        p.ball(hx - hump * 0.9, -hump * 1.05, hx + hump * 0.9, 2, (250, 252, 255), (205, 220, 245))
    # exhaust
    p.R(-36, -50, -31, -24, (120, 124, 140), rad=2)
    p.R(-37.5, -52, -29.5, -48, (90, 94, 110), rad=2)
    # chassis
    p.R(-40, -28, 34, -9, YEL, rad=6)
    p.R(-38, -16, 32, -10, shade(YEL, 0.82), False, rad=3)
    p.R(-36, -26, 30, -23, light(YEL, 0.45), False, rad=2)
    # cab
    p.R(-28, -54, 2, -26, YEL, rad=8)
    p.R(-24, -50, -2, -34, (170, 222, 255), rad=4)
    p.L(-20, -48, -13, -36, (235, 248, 255), 2)
    p.C(-12, -40, 5, (250, 210, 175))                        # driver (elf)
    p.C(-10, -41, 0.9, (30, 30, 40), False)
    p.P([(-17, -43), (-7, -43), (-14, -55)], (50, 170, 90))
    p.C(-14, -55, 2, (255, 255, 255))
    # hood + grill
    p.R(2, -38, 30, -24, YEL, rad=6)
    for gx in (20, 24, 28):
        p.L(gx, -35, gx, -27, shade(YEL, 0.6), 1.4)
    p.C(30, -31, 2.6, (255, 246, 190))
    # beacon
    p.R(-18, -59, -8, -54, (255, 120, 20) if beacon else (230, 150, 70), rad=4)
    # blade (hazard stripes)
    p.P([(34, -32), (46, -38), (51, 0), (34, -4)], (160, 170, 186))
    for i in range(4):
        y0 = -34 + i * 9
        p.P([(36, y0 + 3), (44, y0 - 1), (45.5, y0 + 4), (37, y0 + 8)], (40, 40, 52) if i % 2 else (255, 140, 30), False)
    p.L(30, -18, 38, -16, (90, 94, 110), 3)
    # wheels
    for wx, r in ((-24, 9.5), (18, 9.5)):
        p.C(wx, -8, r, (46, 46, 58))
        p.C(wx, -8, r * 0.5, (205, 208, 220))
        for a in range(4):
            ang = wf * math.pi / 8 + a * math.pi / 2
            p.L(wx, -8, wx + math.cos(ang) * r * 0.45, -8 + math.sin(ang) * r * 0.45, (120, 124, 140), 1.3, False)
        p.C(wx, -8, 1.6, (120, 124, 140), False)


def plow(dir_, t, pushed, s):
    wf = int(t * 0.3) % 4
    beacon = int(t // 8) % 2 == 0
    hump = round((4 + min(pushed, 400) ** 0.5 * 1.4) / 2) * 2
    return cached("plow", _plow, (-44, -68, 64 + hump * 1.4, 6), s, dir_ < 0, wf, beacon, hump)


# ================================================================ gift train
RED, GOLD = (228, 56, 64), (255, 205, 70)


def _train(p, wf, wave, stopped):
    cx = -130
    # flatcar (cargo sprite is blitted on top by the app)
    p.L(cx + 38, -11, -48, -11, (70, 70, 84), 3)
    p.R(cx - 40, -18, cx + 40, -8, (160, 104, 60), rad=3)
    for i in range(-3, 4):
        p.L(cx + i * 11, -17, cx + i * 11, -9, shade((160, 104, 60), 0.7), 1)
    for wx in (cx - 25, cx + 25):
        p.C(wx, -7, 7, (46, 46, 58))
        p.C(wx, -7, 3, GOLD)
    # frame
    p.R(-50, -15, 40, -8, (52, 52, 66), rad=2)
    # boiler
    p.R(-18, -42, 36, -13, RED, rad=12)
    p.R(-14, -40, 32, -34, light(RED, 0.4), False, rad=3)
    for bx in (-6, 8, 22):
        p.R(bx - 1.5, -42, bx + 1.5, -13, GOLD, False, rad=1)
    p.C(2, -45, 5.5, GOLD)                                   # dome
    p.P([(16, -42), (13, -58), (31, -58), (28, -42)], (60, 60, 78))   # chimney
    p.R(11, -63, 33, -57, (78, 78, 96), rad=3)
    p.C(38, -29, 4.5, (255, 244, 170))                       # lamp
    p.P([(36, -15), (52, -2), (36, -2)], (150, 154, 170))    # cow catcher
    for k in (40, 44, 48):
        p.L(k, -10 + (k - 40) * 0.6, k - 2, -3, (110, 114, 130), 1)
    # cab
    p.R(-50, -60, -12, -54, (60, 60, 78), rad=3)
    p.R(-46, -55, -16, -13, RED, rad=4)
    p.R(-42, -51, -21, -36, (255, 238, 180), rad=3)
    # elf in the window
    p.C(-31, -42, 5.5, (250, 212, 178))
    p.C(-29, -43, 0.9, (30, 30, 40), False)
    p.C(-33, -43, 0.9, (30, 30, 40), False)
    p.O(-35, -40, -32.5, -38.5, (255, 160, 170), False)
    p.P([(-37, -45), (-25, -45), (-27 + wave * 0.4, -56)], (50, 170, 90))
    p.C(-27 + wave * 0.4, -56, 2.2, (255, 255, 255))
    if stopped:
        p.T(-24, -40, -14 + wave, -52, (50, 170, 90), 3)
        p.C(-14 + wave, -52, 2.6, (250, 212, 178))
    # wheels + rod
    for wx, r in ((-34, 9.5), (-13, 8.5), (10, 7), (27, 7)):
        p.C(wx, -8, r, (46, 46, 58))
        p.C(wx, -8, r * 0.62, RED)
        for a in range(3):
            ang = wf * math.pi / 6 + a * math.pi * 2 / 3
            p.L(wx, -8, wx + math.cos(ang) * r * 0.6, -8 + math.sin(ang) * r * 0.6, GOLD, 1.3, False)
        p.C(wx, -8, 1.8, GOLD, False)
    ang = wf * math.pi / 6
    p.L(-13 + math.cos(ang) * 5, -8 + math.sin(ang) * 5, 10 + math.cos(ang) * 4, -8 + math.sin(ang) * 4,
        (200, 204, 216), 2)


def train(t, state, s):
    stopped = state == "stop"
    wf = 0 if stopped else int(t * 0.3) % 4
    wave = int(math.sin(t * 0.3) * 5) if stopped else 0
    return cached("train", _train, (-176, -70, 58, 6), s, False, wf, wave, stopped)


# ================================================================ snowman
SNOWC, SNOWS = (252, 253, 255), (200, 214, 240)


def _snowman(p):
    p.T(-11, -36, -24, -48, (120, 76, 44), 2.6)              # stick arms
    p.T(-19, -43, -23, -52, (120, 76, 44), 1.8)
    p.T(11, -36, 24, -48, (120, 76, 44), 2.6)
    p.T(19, -43, 25, -41, (120, 76, 44), 1.8)
    p.ball(-16, -29, 16, 0, SNOWC, SNOWS)
    p.ball(-12, -48, 12, -24, SNOWC, SNOWS)
    p.ball(-10, -65, 10, -45, SNOWC, SNOWS)
    for yy in (14, 31, 38):
        p.C(0, -yy, 2, (60, 64, 92), False)
        p.C(-0.6, -yy - 0.6, 0.6, (140, 146, 180), False)
    for ex in (-4, 4):
        p.O(ex - 2, -59, ex + 2, -54, (30, 30, 44), False)
        p.C(ex - 0.6, -57.6, 0.7, (255, 255, 255), False)
    for i, mx in enumerate((-4.5, -2.2, 0, 2.2, 4.5)):        # coal smile
        p.C(mx, -50 + abs(mx) * -0.35 + 0.4, 0.9, (40, 40, 52), False)
    p.O(-9, -54, -5, -51, (255, 168, 182), False)
    p.O(5, -54, 9, -51, (255, 168, 182), False)
    p.P([(0, -56), (13, -53), (0, -51)], (255, 140, 30))     # carrot
    p.L(5, -55, 5.5, -52, shade((255, 140, 30), 0.7), 0.8, False)
    p.L(9, -54, 9.3, -52.5, shade((255, 140, 30), 0.7), 0.8, False)
    p.R(-13, -48, 13, -42, (226, 50, 62), rad=3)             # scarf
    p.R(3, -45, 9, -30, (226, 50, 62), rad=2)
    for k in (-8, -2, 4, 10):
        p.L(k, -46, k + 2, -44, (255, 255, 255), 1.2, False)
    p.R(-12, -68, 12, -63, (42, 42, 58), rad=2)              # hat
    p.R(-7.5, -81, 7.5, -64, (42, 42, 58), rad=2)
    p.R(-7.5, -70, 7.5, -66, (226, 50, 62), False, rad=0)
    p.P(rot_ellipse(5, -70, 3.2, 1.6, 0.5), (50, 160, 80), False)
    p.C(3, -69, 1.4, (230, 40, 50), False)


def snowman(s):
    return cached("snowman", _snowman, (-30, -86, 30, 4), s, False)


# ================================================================ tree
LIGHTS = [(255, 80, 80), (255, 220, 60), (90, 200, 255), (120, 255, 140), (255, 120, 230)]
ORN = [(230, 50, 60), (250, 200, 50), (70, 120, 230), (200, 90, 220)]
GREEN = (44, 164, 88)


def _tree(p, frame, seed):
    p.R(-5, -13, 5, 0, (130, 82, 46), rad=2)
    tiers = ((0, 31, 34), (18, 25, 30), (34, 19, 26))
    for up, half, hgt in tiers:
        yb = -9 - up
        p.P([(-half, yb), (half, yb), (0, yb - hgt)], GREEN)
        for i in range(5):                                     # scalloped hem
            sx = -half + (i + 0.5) * half * 2 / 5
            p.C(sx, yb - 1, half / 5 + 0.6, GREEN, False)
        p.P([(-half * 0.25, yb - hgt * 0.75), (0, yb - hgt), (half * 0.25, yb - hgt * 0.75)], light(GREEN, 0.25), False)
        p.P([(-half * 0.42, yb - hgt * 0.6), (half * 0.42, yb - hgt * 0.6), (0, yb - hgt)], SNOWC, False)
        for i in range(4):                                     # snow drips
            sx = -half * 0.42 + i * half * 0.28
            p.C(sx + 2, yb - hgt * 0.6, 2.2, SNOWC, False)
        p.L(-half + 3, yb - 2, half - 3, yb - 2, shade(GREEN, 0.72), 1.5, False)
    # garland
    for y0, h in ((-24, 22), (-42, 17), (-58, 12)):
        pts = [(-h + i * h / 4, y0 + math.sin(i * 0.8) * 2.5 + i * 0.6) for i in range(9)]
        for a, b in zip(pts, pts[1:]):
            p.L(a[0], a[1], b[0], b[1], (255, 214, 90), 1.4, False)
    rnd = random.Random(seed * 31 + 5)
    for i in range(14):
        ty = rnd.uniform(16, 66)
        half = 30 - ty * 0.4
        bx, by = rnd.uniform(-half, half) * 0.8, -ty
        if i % 2:
            col = rnd.choice(ORN)
            p.C(bx, by, 3.2, col)
            p.C(bx - 1, by - 1.1, 1, light(col, 0.7), False)
        else:
            on = (frame + i) % 3 != 0
            col = LIGHTS[(i + frame) % len(LIGHTS)]
            p.C(bx, by, 2, col if on else (90, 90, 104), False)
    sy, pts = -78, []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = 9.5 if i % 2 == 0 else 4.2
        pts.append((math.cos(ang) * rr, sy + math.sin(ang) * rr))
    p.P(pts, (255, 214, 60))
    p.C(-1.5, sy - 2, 1.5, (255, 248, 200), False)


def tree(frame, seed, s):
    return cached("tree", _tree, (-36, -92, 36, 4), s, False, frame, seed % 997)
