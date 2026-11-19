"""Cute chibi dogs & cats, rendered with Pillow (4x supersampled, antialiased) and cached as pygame sprites.

Sprite canvas is 64x56 units at scale 1, ground line at y=52, animal faces right (flipped for left).
"""
import math
import pygame
from PIL import Image, ImageDraw

SS = 4
W, H, GROUND = 64, 56, 52
INK = (38, 34, 52, 255)
_cache = {}


def _c(rgb, a=255):
    return tuple(int(v) for v in rgb[:3]) + (a,)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def lighten(c, k):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


class Pen:
    def __init__(self, d, k):
        self.d, self.k = d, k
        self.ow = max(2, int(1.5 * k))

    def E(self, cx, cy, rx, ry, fill, ink=True):
        k = self.k
        self.d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=_c(fill),
                       outline=INK if ink else None, width=self.ow if ink else 0)

    def RR(self, x0, y0, x1, y1, r, fill, ink=True):
        k = self.k
        self.d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], r * k, fill=_c(fill),
                                 outline=INK if ink else None, width=self.ow if ink else 0)

    def P(self, pts, fill, ink=True):
        k = self.k
        self.d.polygon([(x * k, y * k) for x, y in pts], fill=_c(fill), outline=INK if ink else None,
                       width=self.ow if ink else 0)

    def L(self, pts, col, w):
        k = self.k
        self.d.line([(x * k, y * k) for x, y in pts], fill=_c(col), width=int(w * k), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = w * k / 2
            self.d.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=_c(col))

    def tube(self, pts, col, w):
        """Thick outlined stroke (tails)."""
        self.L(pts, INK, w + 3.0)
        self.L(pts, col, w)

    def arc(self, cx, cy, r, a0, a1, col, w=1.4):
        k = self.k
        self.d.arc([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], a0, a1, fill=_c(col), width=int(w * k))


def _rot_ellipse(cx, cy, rx, ry, ang, n=24):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(t) * ca - ry * math.sin(t) * sa, cy + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
            for t in (i * 2 * math.pi / n for i in range(n))]


def _face(p, cat, hx, hy, r, body, acc, pat, mode, blink, breed):
    """mode: side / front / sleep."""
    eye_col = (70, 170, 90) if cat else (40, 30, 30)
    if breed == "siyam":
        eye_col = (70, 140, 230)
    blush = lighten((255, 120, 150), 0.25)
    muzzle = acc if pat in ("mask", "mask_light") else lighten(body, 0.45)
    if pat == "mask":
        muzzle = shade(acc, 1.0)
    if mode == "front":
        eyes, sx = (hx - 4.2, hx + 4.2), hx
    else:
        eyes, sx = (hx + 4.0,), hx + 8.5
    if not cat:
        if mode == "front":
            p.E(sx, hy + 4.2, 5.2, 3.8, muzzle)
            p.E(sx, hy + 2.6, 2.2, 1.6, (30, 26, 34), False)
            p.arc(sx - 1.4, hy + 4.4, 1.6, 10, 170, INK, 1.1)
            p.arc(sx + 1.4, hy + 4.4, 1.6, 10, 170, INK, 1.1)
        else:
            p.E(sx, hy + 3.2, 5.0, 3.8, muzzle)
            p.E(sx + 3.8, hy + 1.4, 2.0, 1.7, (30, 26, 34), False)
            p.arc(sx + 1.0, hy + 4.2, 2.0, 30, 150, INK, 1.1)
    else:
        nx = sx if mode == "front" else hx + 9.5
        ny = hy + 3.0
        p.P([(nx - 1.4, ny - 0.8), (nx + 1.4, ny - 0.8), (nx, ny + 0.8)], (245, 140, 160), False)
        p.arc(nx - 1.2, ny + 1.2, 1.2, 0, 160, INK, 1.0)
        p.arc(nx + 1.2, ny + 1.2, 1.2, 20, 180, INK, 1.0)
        for dy in (-0.5, 1.2):
            if mode == "front":
                p.L([(nx - 3, ny + dy), (nx - 9, ny + dy - 0.8 + dy * 0.6)], (235, 235, 245), 0.5)
                p.L([(nx + 3, ny + dy), (nx + 9, ny + dy - 0.8 + dy * 0.6)], (235, 235, 245), 0.5)
            else:
                p.L([(nx - 1, ny + dy), (nx + 6, ny + dy - 1 + dy * 0.6)], (235, 235, 245), 0.5)
    for i, ex in enumerate(eyes):
        ey = hy - 1.0
        if mode == "sleep" or blink:
            p.arc(ex, ey - 1.0, 2.4, 20, 160, INK, 1.3)
        else:
            p.E(ex, ey, 2.6, 3.1, eye_col if cat else (34, 28, 34), False)
            if cat:
                p.E(ex, ey, 1.0, 2.6, (20, 18, 24), False)
            p.E(ex + 0.9, ey - 1.2, 1.0, 1.0, (255, 255, 255), False)
            p.E(ex - 0.8, ey + 1.2, 0.5, 0.5, (255, 255, 255), False)
    cheeks = (hx - 6.5, hx + 6.5) if mode == "front" else (hx + 2.5,)
    for cx in cheeks:
        p.E(cx, hy + 3.6, 2.2, 1.3, blush, False)


def _ears_back(p, cat, ear, hx, hy, r, body, acc, pat, mode, breed):
    ecol = acc if pat in ("points", "van") else body
    if cat or ear == "up":
        inner = (255, 175, 195) if cat else lighten(ecol, 0.5)
        if mode == "front":
            sides = ((hx - r * 0.62, -1), (hx + r * 0.62, 1))
        else:
            sides = ((hx - r * 0.55, -1), (hx + r * 0.25, 1))
        for ex, s in sides:
            tip = (ex + s * 2.0, hy - r * 1.35)
            p.P([(ex - 4.6, hy - r * 0.45), tip, (ex + 4.6, hy - r * 0.45)], ecol)
            p.P([(ex - 2.3, hy - r * 0.6), (tip[0], tip[1] + 3.2), (ex + 2.3, hy - r * 0.6)], inner, False)


def _ears_front(p, cat, ear, hx, hy, r, body, acc, pat, mode, breed, wag):
    if cat or ear != "flop":
        return
    ecol = shade(body, 0.75) if breed not in ("kaniş", "golden") else shade(body, 0.92)
    if pat == "saddle" and breed == "beagle":
        ecol = (150, 92, 50)
    if breed == "dalmaçyalı":
        ecol = (60, 56, 62)
    if mode == "front":
        for s in (-1, 1):
            p.P(_rot_ellipse(hx + s * r * 0.92, hy - 0.5 + wag * 0.3, 3.6, 7.0, -s * 0.35), ecol)
    else:
        p.P(_rot_ellipse(hx - r * 0.35, hy - 0.5 + wag * 0.3, 3.8, 7.2, 0.25), ecol)


def _patterns(p, pat, bx, by, rx, ry, acc, body, seed):
    if pat == "spots":
        import random
        rnd = random.Random(seed)
        for _ in range(6):
            p.E(bx + rnd.uniform(-0.65, 0.65) * rx, by + rnd.uniform(-0.6, 0.35) * ry, rnd.uniform(1.2, 2.0),
                rnd.uniform(1.0, 1.7), acc, False)
    elif pat == "stripes":
        dk = shade(body, 0.72)
        for k in (-0.45, -0.1, 0.25, 0.6):
            p.L([(bx + k * rx - 1, by - ry * 0.92), (bx + k * rx + 1, by - ry * 0.35)], dk, 1.6)
    elif pat == "saddle":
        p.E(bx - rx * 0.1, by - ry * 0.45, rx * 0.72, ry * 0.55, acc if acc[0] < 90 else (44, 36, 36), False)
    elif pat == "calico":
        p.E(bx - rx * 0.4, by - ry * 0.4, rx * 0.38, ry * 0.45, acc, False)
        p.E(bx + rx * 0.35, by - ry * 0.3, rx * 0.3, ry * 0.4, (54, 48, 54), False)
    elif pat in ("belly", "mask_light"):
        p.E(bx + rx * 0.1, by + ry * 0.45, rx * 0.7, ry * 0.45, lighten(acc if pat == "belly" else (255, 255, 255), 0.2), False)


def render(sp, br, state, leg, tail, blink, scale, flip, seed):
    name, body, acc, ear, tailk, size, leglen, pat = br
    cat = sp == "cat"
    k = SS * scale
    img = Image.new("RGBA", (int(W * k), int(H * k)), (0, 0, 0, 0))
    p = Pen(ImageDraw.Draw(img), k)
    far = shade(body, 0.8)
    paw = acc if pat == "points" else (lighten(body, 0.5) if pat in ("belly", "mask_light") else body)
    wag = (tail - 1) * 1.0                                  # -1, 0, 1
    hr = 11.5 if not cat else 11.0
    if name == "tombul":
        hr = 12
    L = 9 * leglen
    tcol = acc if pat in ("points", "van") else body

    if state == "sit":
        bx, by, rx, ry = 27, GROUND - 11, 11, 11.5
        hx, hy, mode = 34, by - ry - hr * 0.55, "side"
    elif state == "lie":
        bx, by, rx, ry = 28, GROUND - 6.5, 17, 7
        hx, hy, mode = 46, GROUND - hr + 1, "sleep" if blink == 2 else "side"
    else:
        bob = 1.0 if leg in (1, 3) else 0.0
        rx, ry = (14, 8.5) if not cat else (13.5, 7.8)
        if name == "tombul":
            rx, ry = 15, 10
        bx, by = 27, GROUND - L - ry * 0.55 - bob
        hx, hy = bx + rx + 2, by - ry - hr * 0.35
        mode = "front" if state == "look" else "side"
        if mode == "front":
            hx -= 6
    if state == "lie" and mode == "side":
        mode = "side"

    # ---- tail
    tx, ty = bx - rx * 0.9, by - ry * 0.35
    if state in ("sit", "lie"):
        p.tube([(bx - rx * 0.6, GROUND - 2), (bx - rx - 6, GROUND - 3 + wag * 0.6), (bx - rx - 10, GROUND - 6)], tcol, 4.2)
    elif cat:
        p.tube([(tx, ty), (tx - 7, ty - 6), (tx - 6 + wag * 3, ty - 15), (tx - 2 + wag * 5, ty - 19)], tcol, 4.0)
    elif tailk == "curl":
        p.E(tx + 1, ty - 7 + wag * 0.5, 5.5, 5.5, body)
        p.E(tx + 1, ty - 7 + wag * 0.5, 2.3, 2.3, shade(body, 0.75), False)
    elif tailk == "plume":
        p.P(_rot_ellipse(tx - 6, ty - 4 + wag, 9, 4.2, -0.5 + wag * 0.25), lighten(body, 0.1))
    elif tailk == "stub":
        p.E(tx, ty - 1, 3.2, 3.2, body)
    else:
        p.tube([(tx, ty), (tx - 6, ty - 5 + wag * 2), (tx - 9, ty - 12 + wag * 3)], body, 2.6)
        if tailk == "pom":
            p.E(tx - 9, ty - 12 + wag * 3, 4.2, 4.2, lighten(acc, 0.3))

    # ---- legs (far)
    sw = [0, 2.2, 0, -2.2][leg] if state in ("walk", "play", "leave") else 0
    if state not in ("sit", "lie"):
        for lx, s in ((bx - rx * 0.55 + 2.5, -sw), (bx + rx * 0.55 + 2.5, sw)):
            p.RR(lx - 2.8 + s, by, lx + 2.8 + s, GROUND, 2.8, far)

    # ---- body
    if state == "sit":
        p.E(bx - 4, GROUND - 5, 8, 5.5, body)                  # haunch
        p.E(bx, by, rx, ry, body)
    else:
        p.E(bx, by, rx, ry, body)
    _patterns(p, pat, bx, by, rx, ry, acc, body, seed)

    # ---- legs (near) / paws
    if state == "sit":
        for lx in (bx + 4, bx + 8.5):
            p.RR(lx - 2.8, by - 2, lx + 2.8, GROUND, 2.8, paw)
    elif state == "lie":
        p.E(bx + rx - 1, GROUND - 2.4, 5.2, 2.6, paw)
        p.E(bx + rx + 4, GROUND - 2.2, 5.0, 2.5, paw)
    else:
        for lx, s in ((bx - rx * 0.55, sw), (bx + rx * 0.55, -sw)):
            p.RR(lx - 2.8 + s, by + 1, lx + 2.8 + s, GROUND + 0.4, 2.8, paw)

    # ---- head
    hcol = acc if pat == "van" else body
    _ears_back(p, cat, ear, hx, hy, hr, body, acc, pat, mode, name)
    p.E(hx, hy, hr, hr * 0.95, hcol)
    if pat == "points":
        p.E(hx + (0 if mode == "front" else 5), hy + 2.5, 6.5, 5.5, acc, False)
    if pat == "mask_light":
        p.E(hx + (0 if mode == "front" else 3), hy + 3, 8, 5.5, (250, 250, 255), False)
    if name == "kaniş":
        p.E(hx - 1, hy - hr * 0.8, 6, 4.5, lighten(body, 0.2))
    _face(p, cat, hx, hy, hr, body, acc, pat, mode, blink == 1, name)
    _ears_front(p, cat, ear, hx, hy, hr, body, acc, pat, mode, name, wag)

    out = img.resize((max(1, int(W * scale)), max(1, int(H * scale))), Image.LANCZOS)
    if flip:
        out = out.transpose(Image.FLIP_LEFT_RIGHT)
    return pygame.image.frombuffer(out.tobytes(), out.size, "RGBA").convert_alpha()


def sprite(sp, breed_idx, br, state, leg, tail, blink, scale, flip, seed):
    scale = max(0.3, round(scale * 8) / 8)
    if state in ("shiver", "look"):
        leg = 0
    key = (sp, breed_idx, state, leg, tail, blink, scale, flip, seed if br[7] == "spots" else 0)
    s = _cache.get(key)
    if s is None:
        if len(_cache) > 3000:
            _cache.clear()
        s = _cache[key] = render(sp, br, state, leg, tail, blink, scale, flip, seed)
    return s
