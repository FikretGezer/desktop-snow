"""
Desktop Snow - homemade desktop weather & Christmas overlay for Windows.
pygame-ce renderer, one click-through window per selected screen, runs at the
screen's refresh rate. Cartoon art style (thick outlines, round shapes).

Everything is adjustable from the control panel (Ctrl+Alt+S) and saved in
settings.json. Chaos mode randomises the settings every few seconds.

Hotkeys (work anywhere):
  Ctrl+Alt+S  control panel
  Ctrl+Alt+E  next effect
  Ctrl+Alt+Q  quit
"""
import ctypes
import ctypes.wintypes as wt
import datetime
import json
import math
import os
import queue
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()
ctypes.windll.winmm.timeBeginPeriod(1)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame  # noqa: E402

import wallpaper  # noqa: E402
import pet_art  # noqa: E402
import art_hd  # noqa: E402

HERE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "settings.json")

KEY = (1, 2, 3)
FPS = 120
S = 60.0 / FPS
BUCKET = 6
SNOW = (250, 252, 255)
SNOW_SHADE = (196, 220, 246)
INK = (38, 44, 78)            # cartoon outline colour
LIGHTS = [(255, 70, 80), (255, 214, 60), (80, 230, 120), (80, 160, 255), (255, 130, 240)]

EFFECTS = {
    #            count, colours,                                          size,   speed,       drift, piles
    "snow":      (220, [(255, 255, 255), (240, 248, 255), (228, 242, 255)], (3, 8), (0.7, 2.0), 0.8, True),
    "leaves":    (60,  [(232, 102, 44), (246, 170, 50), (200, 70, 40), (220, 145, 40)], (6, 10), (1.0, 2.2), 2.0, False),
    "sakura":    (90,  [(255, 190, 212), (255, 168, 196), (255, 222, 232)], (4, 7), (0.6, 1.4), 1.6, False),
    "rain":      (260, [(150, 190, 235), (190, 215, 240)],                 (1, 2), (14, 20),   0.3, False),
    "fireflies": (45,  [(255, 245, 140), (230, 255, 110), (255, 225, 100)], (2, 4), (-0.3, 0.3), 0.6, False),
    "starfall":  (14,  [(255, 255, 255), (255, 240, 180), (200, 225, 255)], (2, 3), (5, 9),     0.0, False),
}
ORDER = list(EFFECTS)
EFFECT_NAMES = {"snow": "Kar", "leaves": "Yaprak", "sakura": "Sakura", "rain": "Yağmur",
                "fireflies": "Ateş böceği", "starfall": "Yıldız kayması"}
WHERE = ["görev çubuğu", "pencereler", "ikisi de"]
CARGO = ["ağaç", "kardan adam", "rastgele"]
# name, body, accent, ears, tail, size, leg length, pattern
DOGS = [("husky", (150, 160, 182), (246, 247, 252), "up", "curl", 1.1, 1.0, "mask_light"),
        ("golden", (228, 172, 92), (248, 214, 156), "flop", "plume", 1.1, 1.0, None),
        ("dalmaçyalı", (250, 250, 252), (40, 40, 48), "flop", "thin", 1.05, 1.1, "spots"),
        ("corgi", (232, 142, 62), (255, 242, 228), "up", "stub", 0.9, 0.55, "belly"),
        ("labrador", (78, 70, 78), (100, 92, 100), "flop", "thin", 1.1, 1.0, None),
        ("beagle", (170, 106, 58), (250, 246, 236), "flop", "thin", 0.95, 0.85, "saddle"),
        ("pug", (222, 196, 150), (62, 52, 54), "flop", "curl", 0.8, 0.7, "mask"),
        ("kaniş", (244, 238, 246), (250, 200, 220), "flop", "pom", 0.9, 1.05, None),
        ("çoban", (120, 84, 50), (40, 34, 36), "up", "plume", 1.2, 1.1, "saddle")]
CATS = [("tekir", (242, 152, 62), (255, 214, 160), "cat", "cat", 1.0, 0.9, "stripes"),
        ("kara kedi", (66, 66, 80), (90, 90, 106), "cat", "cat", 1.0, 0.9, None),
        ("beyaz", (250, 250, 252), (255, 205, 215), "cat", "cat", 1.0, 0.9, None),
        ("siyam", (240, 226, 202), (92, 70, 60), "cat", "cat", 0.95, 0.95, "points"),
        ("gri", (140, 150, 166), (190, 198, 212), "cat", "cat", 1.0, 0.9, "stripes"),
        ("calico", (250, 248, 242), (236, 140, 60), "cat", "cat", 1.0, 0.9, "calico"),
        ("van", (252, 252, 250), (232, 150, 70), "cat", "cat", 1.05, 0.9, "van"),
        ("tombul", (210, 180, 150), (250, 230, 210), "cat", "cat", 1.25, 0.7, "belly")]
DOG_CHOICES = ["karışık"] + [b[0] for b in DOGS]
CAT_CHOICES = ["karışık"] + [b[0] for b in CATS]

# ---------------------------------------------------------------- every option
# (tab, key, label, type, default, lo, hi)   type: f=slider float, i=slider int, b=checkbox, c=choice
SPEC = [
    ("Genel", "chaos", "KAOS MODU (ayarları sürekli karıştırır)", "b", False, 0, 0),
    ("Genel", "chaos_every", "Kaos: kaç saniyede bir", "f", 15.0, 2, 120),
    ("Genel", "chaos_amount", "Kaos: ne kadar ayar değişsin (%)", "i", 40, 5, 100),
    ("Genel", "chaos_effects", "Kaos hava efektini de değiştirsin", "b", True, 0, 0),
    ("Genel", "chaos_visitors", "Kaos ziyaretçi çağırsın", "b", True, 0, 0),
    ("Genel", "chaos_decor", "Kaos ağaç / kardan adam eklesin", "b", True, 0, 0),
    ("Genel", "fps", "FPS (0 = ekran hızı)", "i", 0, 0, 360),

    ("Kar", "density", "Yoğunluk", "f", 1.0, 0.1, 5),
    ("Kar", "size_min", "Tane boyutu: en küçük (piksel)", "f", 3.0, 1, 30),
    ("Kar", "size_max", "Tane boyutu: en büyük (piksel)", "f", 8.0, 1, 30),
    ("Kar", "speed", "Düşme hızı", "f", 1.0, 0.2, 5),
    ("Kar", "wind", "Rüzgar gücü", "f", 1.0, 0, 6),
    ("Kar", "wind_change", "Rüzgar kaç saniyede değişsin", "f", 2.0, 0.5, 20),
    ("Kar", "pile_rate", "Birikme hızı", "f", 1.0, 0, 6),
    ("Kar", "pile_max", "En fazla birikme (piksel)", "i", 16, 2, 60),
    ("Kar", "pile_windows", "Pencerelerin üstünde biriksin", "b", True, 0, 0),
    ("Kar", "pile_taskbar", "Görev çubuğunda biriksin", "b", True, 0, 0),
    ("Kar", "shake_sens", "Pencere sallayınca dökülme hassasiyeti", "f", 1.0, 0, 5),
    ("Kar", "mouse_push", "Fareyle kar itilsin", "b", True, 0, 0),
    ("Kar", "melt", "Erime hızı (0 = erimesin)", "f", 0.0, 0, 10),

    ("Ağaç", "tree_auto", "Kendiliğinden çıksın", "b", False, 0, 0),
    ("Ağaç", "tree_every", "Kaç saniyede bir çıksın", "f", 120.0, 3, 900),
    ("Ağaç", "tree_max", "En fazla ağaç", "i", 3, 0, 20),
    ("Ağaç", "tree_size", "Boyut", "f", 1.0, 0.3, 4),
    ("Ağaç", "tree_grow", "Küçük çıkıp büyüsün", "b", False, 0, 0),
    ("Ağaç", "tree_grow_time", "Büyüme süresi (saniye)", "f", 8.0, 0.5, 120),
    ("Ağaç", "tree_where", "Nerede çıksın", "c", "görev çubuğu", WHERE, 0),
    ("Ağaç", "twinkle", "Işık yanıp sönme hızı", "f", 1.0, 0, 5),

    ("Kardan adam", "snowman_auto", "Kendiliğinden çıksın", "b", False, 0, 0),
    ("Kardan adam", "snowman_every", "Kaç saniyede bir çıksın", "f", 90.0, 3, 900),
    ("Kardan adam", "snowman_max", "En fazla kardan adam", "i", 12, 0, 40),
    ("Kardan adam", "snowman_size", "Boyut", "f", 1.0, 0.3, 4),
    ("Kardan adam", "snowman_grow", "Küçük çıkıp büyüsün", "b", False, 0, 0),
    ("Kardan adam", "snowman_grow_time", "Büyüme süresi (saniye)", "f", 6.0, 0.5, 120),
    ("Kardan adam", "snowman_where", "Nerede çıksın", "c", "ikisi de", WHERE, 0),
    ("Kardan adam", "snowman_fall", "Pencere sallanınca düşsün", "b", True, 0, 0),

    ("Yeti", "yeti_auto", "Kendiliğinden gelsin", "b", True, 0, 0),
    ("Yeti", "yeti_every", "Kaç saniyede bir gelsin", "f", 120.0, 3, 900),
    ("Yeti", "yeti_speed", "Hız", "f", 1.0, 0.2, 5),
    ("Yeti", "yeti_size", "Boyut", "f", 1.0, 0.4, 4),
    ("Yeti", "yeti_smash_snowmen", "Kardan adamları ezsin", "b", True, 0, 0),
    ("Yeti", "yeti_smash_trees", "Ağaçları devirsin", "b", False, 0, 0),
    ("Yeti", "yeti_eat_snow", "Yürürken karı yesin", "b", False, 0, 0),
    ("Yeti", "yeti_roar", "Gelince kükresin (pencerelerdeki kar dökülür)", "b", False, 0, 0),
    ("Yeti", "yeti_stomp", "Zıplama süresi", "f", 1.0, 0.2, 4),

    ("Küreyici", "plow_auto", "Kendiliğinden gelsin", "b", True, 0, 0),
    ("Küreyici", "plow_every", "Kaç saniyede bir gelsin", "f", 60.0, 3, 900),
    ("Küreyici", "plow_min_snow", "Gelmesi için gereken kar", "f", 4.0, 0, 30),
    ("Küreyici", "plow_speed", "Hız", "f", 1.0, 0.2, 5),
    ("Küreyici", "plow_size", "Boyut", "f", 1.0, 0.4, 4),
    ("Küreyici", "plow_snowmen", "Kardan adamları ezsin", "b", True, 0, 0),
    ("Küreyici", "plow_trees", "Ağaçları ezsin", "b", False, 0, 0),
    ("Hayvanlar", "pets_on", "Hayvanlar dolaşsın", "b", True, 0, 0),
    ("Hayvanlar", "dog_count", "Köpek sayısı", "i", 2, 0, 12),
    ("Hayvanlar", "cat_count", "Kedi sayısı", "i", 2, 0, 12),
    ("Hayvanlar", "pet_size", "Hayvan boyu (hepsi)", "f", 1.0, 0.3, 5),
    ("Hayvanlar", "dog_size", "Köpek boyu", "f", 1.0, 0.3, 4),
    ("Hayvanlar", "cat_size", "Kedi boyu", "f", 1.0, 0.3, 4),
    ("Hayvanlar", "dog_breed", "Köpek türü", "c", "karışık", DOG_CHOICES, 0),
    ("Hayvanlar", "cat_breed", "Kedi türü", "c", "karışık", CAT_CHOICES, 0),
    ("Hayvanlar", "pet_speed", "Yürüme hızı", "f", 1.0, 0.2, 4),
    ("Hayvanlar", "pet_variety", "Her hayvan biraz farklı boyda ve hızda olsun", "b", True, 0, 0),
    ("Hayvanlar", "pet_state_time", "Bir hareketi kaç saniye sürdürsün", "f", 4.0, 1, 30),
    ("Hayvanlar", "anim_walk", "Dolaşma animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_walk", "Dolaşma (ağırlık)", "f", 6.0, 0, 10),
    ("Hayvanlar", "anim_sit", "Oturma animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_sit", "Oturma (ağırlık)", "f", 2.0, 0, 10),
    ("Hayvanlar", "anim_lie", "Yatıp uyuma animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_lie", "Yatıp uyuma (ağırlık)", "f", 1.5, 0, 10),
    ("Hayvanlar", "anim_look", "Ekrana bakma animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_look", "Ekrana bakma (ağırlık)", "f", 1.5, 0, 10),
    ("Hayvanlar", "anim_shiver", "Üşüyüp titreme animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_shiver", "Üşüyüp titreme (kar/yağmurda)", "f", 1.5, 0, 10),
    ("Hayvanlar", "anim_play", "Zıplayıp oynama animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_play", "Zıplayıp oynama (ağırlık)", "f", 1.0, 0, 10),
    ("Hayvanlar", "anim_leave", "Ekrandan çıkıp gitme animasyonu açık", "b", True, 0, 0),
    ("Hayvanlar", "pet_leave", "Ekrandan çıkıp gitme (ağırlık)", "f", 0.4, 0, 10),
    ("Hayvanlar", "pet_respawn", "Giden hayvan kaç saniye sonra gelsin", "f", 8.0, 1, 120),
    ("Hayvanlar", "pet_snow", "Hayvanlar karı itip dağıtsın", "b", True, 0, 0),
    ("Hayvanlar", "pet_snow_amt", "Karı ne kadar dağıtsınlar", "f", 0.5, 0, 4),
    ("Hayvanlar", "pet_wag", "Kuyruk sallama hızı", "f", 1.0, 0, 3),
    ("Hayvanlar", "pet_breath", "Üşüyünce nefesi buhar olsun", "b", True, 0, 0),

    ("Tren", "train_auto", "Kendiliğinden gelsin", "b", False, 0, 0),
    ("Tren", "train_every", "Kaç saniyede bir gelsin", "f", 180.0, 3, 900),
    ("Tren", "train_speed", "Hız", "f", 1.0, 0.2, 5),
    ("Tren", "train_size", "Boyut", "f", 1.0, 0.4, 4),
    ("Tren", "train_cargo", "Ne getirsin", "c", "rastgele", CARGO, 0),
    ("Tren", "train_wait", "Durakta bekleme (saniye)", "f", 2.0, 0, 20),
]
DEFAULTS = {s[1]: s[4] for s in SPEC}
SPEC_BY_KEY = {s[1]: s for s in SPEC}


# ---------------------------------------------------------------- win32 helpers
class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wt.DWORD)]


EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
MonProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HANDLE, wt.HDC, ctypes.POINTER(RECT), wt.LPARAM)
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
user32.MonitorFromPoint.restype = wt.HANDLE


def monitors():
    out = []

    def cb(hm, hdc, pr, lp):
        r = pr.contents
        out.append((r.l, r.t, r.r, r.b, r.l == 0 and r.t == 0))
        return True
    user32.EnumDisplayMonitors(None, None, MonProc(cb), 0)
    return sorted(out, key=lambda m: (not m[4], m[0], m[1]))   # screen 1 = main


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wt.DWORD),
                ("szDevice", ctypes.c_wchar * 32)]


def refresh_rate(m):
    """Refresh rate (Hz) of the monitor whose rect is m."""
    try:
        hm = user32.MonitorFromPoint(wt.POINT((m[0] + m[2]) // 2, (m[1] + m[3]) // 2), 2)
        mi = MONITORINFOEX(); mi.cbSize = ctypes.sizeof(mi)
        user32.GetMonitorInfoW(hm, ctypes.byref(mi))
        dm = ctypes.create_string_buffer(220)
        ctypes.memmove(ctypes.addressof(dm) + 68, ctypes.byref(ctypes.c_ushort(220)), 2)   # dmSize
        if user32.EnumDisplaySettingsW(mi.szDevice, -1, dm):
            return int.from_bytes(dm.raw[184:188], "little")                              # dmDisplayFrequency
    except Exception:
        pass
    return 60


def work_bottom(x, y):
    m = user32.MonitorFromPoint(wt.POINT(int(x), int(y)), 2)
    mi = MONITORINFO(); mi.cbSize = ctypes.sizeof(mi)
    user32.GetMonitorInfoW(m, ctypes.byref(mi))
    return mi.rcWork.b


_rect, _cloak = RECT(), ctypes.c_int(0)


def list_windows(skip, ox, oy):
    out = []

    def cb(h, _):
        if h in skip or not user32.IsWindowVisible(h) or user32.IsIconic(h):
            return True
        if user32.GetWindowTextLengthW(h) == 0:
            return True
        dwmapi.DwmGetWindowAttribute(h, 14, ctypes.byref(_cloak), 4)
        if _cloak.value:
            return True
        r = _rect
        if dwmapi.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(h, ctypes.byref(r))
        if r.r - r.l < 80 or r.b - r.t < 40:
            return True
        out.append((h, r.l - ox, r.t - oy, r.r - ox, r.b - oy))
        return True
    user32.EnumWindows(EnumProc(cb), 0)
    return out


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------- cartoon drawing helper
class G:
    """pygame.draw wrapper: every shape gets a thick dark outline; records touched rects."""
    def __init__(self, surf, dirty=None, ox=0, oy=0, ow=2):
        self.s, self.d, self.ox, self.oy, self.ow = surf, dirty, ox, oy, ow

    def _rec(self, r):
        if self.d is not None:
            self.d.append(r.inflate(4, 4))

    def _r(self, x0, y0, x1, y1):
        return pygame.Rect(int(x0 + self.ox), int(y0 + self.oy), max(1, int(x1 - x0)), max(1, int(y1 - y0)))

    def O(self, x0, y0, x1, y1, col, ink=INK):
        r = self._r(x0, y0, x1, y1)
        if ink:
            pygame.draw.ellipse(self.s, ink, r.inflate(self.ow * 2, self.ow * 2))
        pygame.draw.ellipse(self.s, col, r)
        self._rec(r)

    def C(self, x, y, rad, col, ink=INK):
        c = (int(x + self.ox), int(y + self.oy))
        if ink:
            pygame.draw.circle(self.s, ink, c, max(1, int(rad)) + self.ow)
        self._rec(pygame.draw.circle(self.s, col, c, max(1, int(rad))))

    def R(self, x0, y0, x1, y1, col, ink=INK, rad=3):
        r = self._r(x0, y0, x1, y1)
        if ink:
            pygame.draw.rect(self.s, ink, r.inflate(self.ow * 2, self.ow * 2), border_radius=rad + 1)
        pygame.draw.rect(self.s, col, r, border_radius=rad)
        self._rec(r)

    def P(self, pts, col, ink=INK):
        if len(pts) < 3:
            return
        pts = [(p[0] + self.ox, p[1] + self.oy) for p in pts]
        r = pygame.draw.polygon(self.s, col, pts)
        if ink:
            pygame.draw.lines(self.s, ink, True, pts, self.ow + 1)
        self._rec(r)

    def L(self, x0, y0, x1, y1, col, w=2):
        self._rec(pygame.draw.line(self.s, col, (int(x0 + self.ox), int(y0 + self.oy)),
                                   (int(x1 + self.ox), int(y1 + self.oy)), w))


# ---------------------------------------------------------------- cartoon art (origin = bottom centre)
def art_snowman(g, x, b, s=1.0):
    w = SNOW
    g.O(x - 15 * s, b - 28 * s, x + 15 * s, b, w)
    g.O(x - 11 * s, b - 47 * s, x + 11 * s, b - 24 * s, w)
    g.O(x - 9 * s, b - 63 * s, x + 9 * s, b - 45 * s, w)
    for yy, xx in ((14, 0), (35, 0), (29, 0)):                      # buttons
        g.C(x + xx, b - yy * s, 2 * s, (60, 64, 90), None)
    g.O(x - 6 * s, b - 57 * s, x - 2 * s, b - 52 * s, (30, 30, 40), None)  # eyes
    g.O(x + 2 * s, b - 57 * s, x + 6 * s, b - 52 * s, (30, 30, 40), None)
    g.C(x - 4 * s, b - 56 * s, 0.8 * s, (255, 255, 255), None)
    g.C(x + 4 * s, b - 56 * s, 0.8 * s, (255, 255, 255), None)
    g.O(x - 8 * s, b - 52 * s, x - 4 * s, b - 49 * s, (255, 170, 180), None)   # cheeks
    g.O(x + 4 * s, b - 52 * s, x + 8 * s, b - 49 * s, (255, 170, 180), None)
    g.P([(x, b - 53 * s), (x + 11 * s, b - 50 * s), (x, b - 49 * s)], (255, 140, 30))  # carrot
    g.R(x - 12 * s, b - 47 * s, x + 12 * s, b - 42 * s, (230, 50, 60))            # scarf
    g.R(x + 3 * s, b - 45 * s, x + 9 * s, b - 32 * s, (230, 50, 60))
    g.R(x - 11 * s, b - 66 * s, x + 11 * s, b - 62 * s, (40, 40, 56))             # hat
    g.R(x - 7 * s, b - 78 * s, x + 7 * s, b - 63 * s, (40, 40, 56))
    g.R(x - 7 * s, b - 68 * s, x + 7 * s, b - 65 * s, (230, 50, 60), None, 0)
    g.L(x - 11 * s, b - 36 * s, x - 23 * s, b - 46 * s, (110, 70, 40), max(2, int(3 * s)))
    g.L(x + 11 * s, b - 36 * s, x + 23 * s, b - 46 * s, (110, 70, 40), max(2, int(3 * s)))


def art_tree(g, x, b, frame=0, seed=0, s=1.0):
    g.R(x - 5 * s, b - 12 * s, x + 5 * s, b, (130, 80, 45))
    for up, half, hgt in ((0, 30, 34), (18, 24, 30), (34, 18, 26)):
        yb = b - 9 * s - up * s
        g.P([(x - half * s, yb), (x + half * s, yb), (x, yb - hgt * s)], (40, 160, 80))
        g.P([(x - half * 0.45 * s, yb - hgt * 0.58 * s), (x + half * 0.45 * s, yb - hgt * 0.58 * s),
             (x, yb - hgt * s)], SNOW, None)
        g.P([(x - half * s, yb), (x - half * 0.35 * s, yb - 5 * s), (x + half * 0.3 * s, yb - 3 * s),
             (x + half * s, yb)], SNOW, None)
    rnd = random.Random(seed * 31 + 5)
    for i in range(12):
        ty = rnd.uniform(16, 64)
        half = 30 - ty * 0.4
        bx, by = x + rnd.uniform(-half, half) * 0.8 * s, b - ty * s
        if i % 2:
            g.C(bx, by, 3 * s, rnd.choice([(230, 50, 60), (250, 200, 50), (70, 120, 230), (200, 90, 220)]))
        else:
            on = (frame + i) % 3 != 0
            g.C(bx, by, 2 * s, LIGHTS[(i + frame) % len(LIGHTS)] if on else (90, 90, 100), None)
    sy, pts = b - 76 * s, []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = (9 if i % 2 == 0 else 4) * s
        pts.append((x + math.cos(ang) * rr, sy + math.sin(ang) * rr))
    g.P(pts, (255, 214, 60))


def draw_yeti(g, x, b, d, t, stomp, timer, s):
    bob = 0 if stomp else abs(math.sin(t * 0.25)) * 3 * s
    jump = -abs(math.sin(timer * 0.18)) * 20 * s if stomp and timer < 40 else 0
    y = b + jump
    fur, face = (240, 246, 255), (130, 165, 215)
    sw = math.sin(t * 0.25) * 6 * s
    g.O(x - 15 * s, y - 12 * s - bob, x - 2 * s, y, fur)
    g.O(x + 2 * s, y - 12 * s + bob * 0.3, x + 15 * s, y, fur)
    g.O(x - 24 * s, y - 66 * s - bob, x + 24 * s, y - 6 * s, fur)
    g.O(x - 13 * s, y - 40 * s - bob, x + 13 * s, y - 14 * s - bob, (224, 234, 250), None)   # belly
    for side in (-1, 1):
        ax = x + side * 22 * s
        if stomp and timer < 36:
            g.O(ax - 7 * s, y - 92 * s, ax + 7 * s, y - 46 * s, fur)
        else:
            g.O(ax - 7 * s, y - 52 * s + side * sw * 0.3, ax + 7 * s, y - 16 * s + side * sw * 0.3, fur)
    g.O(x - 14 * s + d * 4 * s, y - 62 * s - bob, x + 14 * s + d * 4 * s, y - 38 * s - bob, face)
    for ex in (-6, 6):
        g.C(x + (ex + d * 4) * s, y - 53 * s - bob, 3.5 * s, (255, 255, 255))
        g.C(x + (ex + d * 5) * s, y - 53 * s - bob, 1.8 * s, (20, 20, 30), None)
    if stomp:
        g.O(x - 6 * s + d * 4 * s, y - 47 * s - bob, x + 6 * s + d * 4 * s, y - 40 * s - bob, (60, 30, 50))
    else:
        g.L(x - 5 * s + d * 4 * s, y - 44 * s - bob, x + 5 * s + d * 4 * s, y - 44 * s - bob, (40, 40, 70), 2)
    for i in range(-2, 3):
        g.P([(x + i * 7 * s - 4 * s, y - 64 * s - bob), (x + i * 7 * s, y - 74 * s - bob),
             (x + i * 7 * s + 4 * s, y - 64 * s - bob)], fur, None)


def draw_plow(g, x, b, d, t, pushed, s):
    hump = (4 + min(pushed, 400) ** 0.5 * 1.4) * s
    bx = x + d * 42 * s + d * hump * 0.4
    g.O(bx - hump * 0.7, b - hump, bx + hump * 0.7, b + 2, SNOW)
    yel = (255, 196, 30)
    g.R(x - 30 * s, b - 24 * s, x + 30 * s, b - 8 * s, yel)
    cab = x - d * 10 * s
    g.R(cab - 14 * s, b - 42 * s, cab + 14 * s, b - 22 * s, yel, rad=5)
    g.R(cab - 9 * s + d * 2 * s, b - 38 * s, cab + 9 * s + d * 2 * s, b - 28 * s, (170, 220, 255), rad=3)
    g.C(cab, b - 46 * s, 4 * s, (255, 110, 0) if int(t // 8) % 2 else (255, 220, 120))
    g.P([(x + d * 30 * s, b - 26 * s), (x + d * 42 * s, b - 32 * s), (x + d * 45 * s, b),
         (x + d * 30 * s, b - 5 * s)], (150, 160, 175))
    for wx in (x - 18 * s, x + 16 * s):
        g.C(wx, b - 7 * s, 8 * s, (50, 50, 60))
        g.C(wx, b - 7 * s, 3 * s, (200, 200, 210), None)


def draw_train(g, x, b, t, state, cargo_spr, s):
    red = (225, 50, 60)
    g.R(x - 44 * s, b - 32 * s, x + 12 * s, b - 9 * s, red)
    g.R(x - 44 * s, b - 52 * s, x - 18 * s, b - 30 * s, red)
    g.R(x - 40 * s, b - 48 * s, x - 24 * s, b - 38 * s, (255, 236, 170))
    g.R(x + 20 * s, b - 52 * s, x + 32 * s, b - 32 * s, (60, 60, 75))
    g.R(x + 16 * s, b - 56 * s, x + 36 * s, b - 50 * s, (60, 60, 75))
    g.R(x - 2 * s, b - 32 * s, x + 38 * s, b - 11 * s, (40, 150, 80))
    g.P([(x + 38 * s, b - 14 * s), (x + 50 * s, b - 2 * s), (x + 38 * s, b - 2 * s)], (110, 110, 125))
    g.C(x + 36 * s, b - 24 * s, 4 * s, (255, 240, 150))
    for wx in (x - 32 * s, x - 13 * s, x + 9 * s, x + 27 * s):
        g.C(wx, b - 7 * s, 7 * s, (50, 50, 60))
        g.C(wx, b - 7 * s, 2.5 * s, (240, 200, 80), None)
    ex = x - 30 * s
    wave = math.sin(t * 0.3) * 5 * s if state == "stop" else 0
    g.C(ex, b - 60 * s, 6 * s, (250, 210, 170))
    g.C(ex - 2 * s, b - 61 * s, 1 * s, (20, 20, 30), None)
    g.C(ex + 2 * s, b - 61 * s, 1 * s, (20, 20, 30), None)
    g.P([(ex - 7 * s, b - 63 * s), (ex + 7 * s, b - 63 * s), (ex + 12 * s + wave * 0.5, b - 78 * s)], (230, 50, 60))
    g.C(ex + 12 * s + wave * 0.5, b - 78 * s, 3 * s, (255, 255, 255))
    g.L(ex + 6 * s, b - 54 * s, ex + 16 * s + wave, b - 68 * s, (50, 170, 80), max(2, int(4 * s)))
    cx = x - 130 * s
    g.L(cx + 38 * s, b - 9 * s, x - 44 * s, b - 9 * s, (70, 70, 80), max(2, int(3 * s)))
    g.R(cx - 38 * s, b - 14 * s, cx + 38 * s, b - 7 * s, (150, 95, 55))
    for wx in (cx - 24 * s, cx + 24 * s):
        g.C(wx, b - 7 * s, 7 * s, (50, 50, 60))
    g.R(x + 2 * s, b - 46 * s, x + 14 * s, b - 34 * s, (230, 50, 60))
    g.R(x + 7 * s, b - 46 * s, x + 9 * s, b - 34 * s, (255, 214, 60), None, 0)
    return cx


def draw_pet(g, x, b, p, t, s):
    br = (DOGS if p["sp"] == "dog" else CATS)[p["breed"]]
    _, body, acc, ear, tail, size, leg, pat = br
    cat = p["sp"] == "cat"
    st, d, ph = p["state"], p["dir"], p["phase"]
    s *= size * p["var"]
    dark = tuple(max(0, c - 40) for c in body)
    pts_col = acc if pat == "points" else body
    if st == "shiver":
        x += math.sin(t * 2.4) * 1.1 * s
    if st == "play":
        b -= abs(math.sin(p["timer"] * 0.12)) * 14 * s
    L = 9 * s * leg
    bl, bh = (14 if cat else 15) * s, (6.5 if cat else 8) * s
    walk = st in ("walk", "leave", "play")
    sw = math.sin(ph) * 4 * s if walk else 0
    wag = math.sin(t * 0.35 * p["wag"] + p["seed"]) * (1.0 if st != "lie" else 0.2)
    blink = (t + p["seed"] * 37) % 220 < 7
    lie, sit, look = st == "lie", st == "sit", st == "look"

    if lie:
        cy, bx = b - bh * 0.85, x
    elif sit:
        cy, bx = b - bh * 1.35, x - d * bl * 0.25
    else:
        cy, bx = b - L - bh * 0.55, x

    # tail (behind body)
    tx, ty = bx - d * bl * (0.75 if sit else 0.95), cy - bh * 0.3
    tcol = acc if pat in ("points", "van") else body
    if lie or sit:
        g.O(tx - 10 * s, b - 5 * s, tx + 10 * s, b, tcol)
    elif cat:
        mx, my = tx - d * 7 * s, ty - 10 * s + wag * 2 * s
        g.L(tx, ty, mx, my, INK, int(6 * s) + 2)
        g.L(mx, my, mx + d * 3 * s + wag * 4 * s, my - 9 * s, INK, int(6 * s) + 2)
        g.L(tx, ty, mx, my, tcol, int(4 * s) + 1)
        g.L(mx, my, mx + d * 3 * s + wag * 4 * s, my - 9 * s, tcol, int(4 * s) + 1)
    elif tail == "curl":
        g.C(tx - d * 2 * s, ty - 6 * s + wag * s, 5 * s, body)
        g.C(tx - d * 2 * s, ty - 6 * s + wag * s, 2 * s, dark, None)
    elif tail == "plume":
        g.P([(tx, ty - 2 * s), (tx - d * 16 * s, ty - 8 * s + wag * 6 * s), (tx - d * 12 * s, ty + 3 * s + wag * 5 * s),
             (tx, ty + 3 * s)], body)
    elif tail == "stub":
        g.C(tx, ty - 1 * s, 3 * s, body)
    else:
        ex, ey = tx - d * 11 * s, ty - 8 * s + wag * 6 * s
        g.L(tx, ty, ex, ey, INK, int(4 * s) + 2)
        g.L(tx, ty, ex, ey, body, int(2.4 * s) + 1)
        if tail == "pom":
            g.C(ex, ey, 4 * s, acc)

    # far legs
    paw = acc if pat in ("points",) else (acc if pat == "belly" else body)
    def legp(lx, swing, col):
        g.P([(lx - 2.6 * s, cy + bh * 0.2), (lx + 2.6 * s, cy + bh * 0.2),
             (lx + swing + 2.6 * s, b), (lx + swing - 2.6 * s, b)], col)
    if not lie and not sit:
        legp(bx - d * bl * 0.55 + 2 * s, -sw, dark)
        legp(bx + d * bl * 0.55 + 2 * s, sw, dark)

    # body
    if sit:
        g.O(bx - bl * 0.7, cy - bh * 1.1, bx + bl * 0.7, b, body)
    else:
        g.O(bx - bl, cy - bh * (0.8 if lie else 1), bx + bl, cy + bh * (0.8 if lie else 1), body)
    if pat == "spots":
        r = random.Random(p["seed"])
        for _ in range(5):
            g.C(bx + r.uniform(-0.7, 0.7) * bl, cy + r.uniform(-0.5, 0.4) * bh, 1.6 * s, acc, None)
    elif pat == "stripes":
        for k in (-0.4, 0, 0.4):
            g.L(bx + k * bl, cy - bh * 0.95, bx + k * bl - d * 2 * s, cy - bh * 0.3, dark, max(2, int(2 * s)))
    elif pat == "saddle" and not sit:
        g.O(bx - bl * 0.6, cy - bh, bx + bl * 0.5, cy - bh * 0.1, acc if br[0] == "çoban" else (40, 34, 36), None)
    elif pat == "calico":
        g.O(bx - bl * 0.6, cy - bh * 0.9, bx - bl * 0.05, cy - bh * 0.1, acc, None)
        g.O(bx + bl * 0.1, cy - bh * 0.8, bx + bl * 0.55, cy - bh * 0.2, (50, 46, 52), None)
    elif pat == "belly" and not sit:
        g.O(bx - bl * 0.6, cy, bx + bl * 0.6, cy + bh * 0.9, acc, None)

    # near legs
    if sit:
        fx = x + d * bl * 0.35
        g.R(fx - 2.6 * s, cy - bh * 0.2, fx + 2.6 * s, b, paw, rad=2)
        g.O(bx - d * bl * 0.2 - 5 * s, b - 5 * s, bx - d * bl * 0.2 + 5 * s, b + 1, body)
    elif lie:
        fx = x + d * bl * 0.9
        g.O(fx - 4 * s, b - 4 * s, fx + 6 * s, b, paw)
    else:
        legp(bx - d * bl * 0.55, sw, paw if pat == "points" else body)
        legp(bx + d * bl * 0.55, -sw, paw if pat == "points" else body)

    # head
    hr = (6.5 if cat else 7) * s * (1.1 if br[0] == "tombul" else 1)
    if lie:
        hx, hy = bx + d * (bl + hr * 0.3), b - hr
    elif sit:
        hx, hy = x + d * bl * 0.45, cy - bh * 1.1 - hr * 0.6
    else:
        hx, hy = bx + d * (bl + hr * 0.25), cy - bh - hr * 0.35
    if look:
        hx -= d * hr * 0.4
    hcol = acc if pat in ("van",) else body
    ecol = acc if pat in ("points", "van") else (dark if ear == "flop" and br[0] != "kaniş" else body)
    if cat:
        for side in ((-1, 1) if look else (-0.2, 0.9)):
            ex = hx + side * hr * 0.65 * (1 if look else d)
            g.P([(ex - 3.5 * s, hy - hr * 0.5), (ex + 0.5 * s * d, hy - hr * 1.55), (ex + 4 * s, hy - hr * 0.5)], ecol)
            g.P([(ex - 1.6 * s, hy - hr * 0.7), (ex + 0.4 * s * d, hy - hr * 1.25), (ex + 2 * s, hy - hr * 0.7)],
                (255, 170, 190), None)
    elif ear == "up":
        for side in ((-1, 1) if look else (-0.3, 0.7)):
            ex = hx + side * hr * 0.6 * (1 if look else d)
            g.P([(ex - 3.5 * s, hy - hr * 0.55), (ex, hy - hr * 1.6), (ex + 3.5 * s, hy - hr * 0.55)], ecol)
    g.C(hx, hy, hr, hcol)
    if pat == "mask_light":
        g.O(hx - hr * 0.6, hy - hr * 0.1, hx + hr * 0.6, hy + hr * 0.9, acc, None)
    if not cat and ear == "flop":
        for side in ((-1, 1) if look else (-0.6,)):
            ex = hx + side * hr * 0.85 * (1 if look else d)
            g.O(ex - 3 * s, hy - hr * 0.6 + wag * 0.5 * s, ex + 3 * s, hy + hr * 0.5 + wag * 0.5 * s, ecol)
    # face
    fc = (24, 22, 34)
    if lie and p["sleep"]:
        for side in (-1, 1) if look else (1,):
            ex = hx + (side * 2.6 * s if look else d * 2.5 * s)
            g.L(ex - 1.6 * s, hy - 1 * s, ex + 1.6 * s, hy - 1 * s, fc, max(1, int(1.4 * s)))
        zt = (t * 0.6 + p["seed"]) % 60 / 60
        zx, zy, zs = hx + d * 6 * s + zt * 8 * s, hy - hr - zt * 18 * s, (2 + zt * 3) * s
        g.L(zx, zy, zx + zs, zy, (210, 220, 255), 2)
        g.L(zx + zs, zy, zx, zy + zs, (210, 220, 255), 2)
        g.L(zx, zy + zs, zx + zs, zy + zs, (210, 220, 255), 2)
    else:
        eyes = (-1, 1) if look else (1,)
        for side in eyes:
            ex = hx + (side * 2.8 * s if look else d * 3 * s)
            if blink:
                g.L(ex - 1.6 * s, hy - 1 * s, ex + 1.6 * s, hy - 1 * s, fc, max(1, int(1.4 * s)))
            else:
                g.C(ex, hy - 1 * s, 1.9 * s, (255, 255, 255), None)
                g.C(ex + (0 if look else d * 0.4 * s), hy - 0.8 * s, 1.2 * s, (60, 160, 90) if cat else fc, None)
    if cat:
        nx = hx if look else hx + d * hr * 0.75
        g.C(nx, hy + 1.6 * s, 1.2 * s, (240, 130, 150), None)
        for k in (-1, 1):
            g.L(nx, hy + 2 * s, nx + (k if look else d) * 7 * s, hy + (1 + k) * s, (230, 230, 240), 1)
    else:
        mcol = acc if pat == "mask" else (tuple(min(255, c + 25) for c in body))
        if look:
            g.O(hx - 3.5 * s, hy + 0.5 * s, hx + 3.5 * s, hy + 5.5 * s, mcol)
            g.C(hx, hy + 1.6 * s, 1.6 * s, fc, None)
        else:
            sx = hx + d * hr * 0.75
            g.O(sx - 4 * s, hy - 0.5 * s, sx + 4 * s, hy + 4.5 * s, mcol)
            g.C(sx + d * 3 * s, hy + 0.8 * s, 1.5 * s, fc, None)
        if st in ("walk", "play") and not cat and (p["seed"] + int(t / 40)) % 3 == 0:
            tx2 = hx + (0 if look else d * hr * 0.6)
            g.O(tx2 - 1.5 * s, hy + 4 * s, tx2 + 1.5 * s, hy + 8 * s, (255, 120, 140))
    # breath puffs while shivering
    if st == "shiver" and p["breath"]:
        k = (t * 0.5 + p["seed"]) % 40 / 40
        bx2 = hx + d * (hr + 3 * s + k * 10 * s)
        g.C(bx2, hy + 2 * s - k * 6 * s, (1.5 + k * 3.5) * s, (236, 242, 252), (200, 210, 230))


def make_icon(path):
    """Draw a 32x32 cartoon snowflake and save it as a .ico (no image files needed)."""
    import struct
    n = 32
    px = [[(0, 0, 0, 0)] * n for _ in range(n)]

    def dot(x, y, col, r=1.4):
        for yy in range(int(y - r - 1), int(y + r + 2)):
            for xx in range(int(x - r - 1), int(x + r + 2)):
                if 0 <= xx < n and 0 <= yy < n and (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                    px[yy][xx] = col
    for col, r in (((78, 44, 38, 255), 2.4), ((255, 230, 200, 255), 1.3)):   # BGRA: ink outline, then ice blue
        for a in range(6):
            ang = a * math.pi / 3
            for i in range(26):
                d = i * 0.52
                dot(16 + math.cos(ang) * d, 16 + math.sin(ang) * d, col, r)
            for side in (-1, 1):                                               # little branches
                bx, by = 16 + math.cos(ang) * 8.5, 16 + math.sin(ang) * 8.5
                for i in range(8):
                    d = i * 0.55
                    dot(bx + math.cos(ang + side * 0.9) * d, by + math.sin(ang + side * 0.9) * d, col, r * 0.85)
        dot(16, 16, col, r + 1.5)
    xor = b"".join(bytes(px[y][x]) for y in range(n - 1, -1, -1) for x in range(n))
    and_mask = b"\0" * (4 * n)
    bmp = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0, len(xor) + len(and_mask), 0, 0, 0, 0) + xor + and_mask
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(bmp), 22) + bmp)


# ---------------------------------------------------------------- objects
class Flake:
    __slots__ = ("x", "y", "vy", "r", "phase", "var")


class Bit:
    __slots__ = ("x", "y", "vx", "vy")


class Decor:
    def __init__(self, kind, x, born=0.0, grow=0.0):
        self.kind, self.x = kind, x
        self.host, self.rel = None, 0.0
        self.y, self.vy = 0.0, 0.0
        self.falling = False
        self.seed = random.randint(0, 6)
        self.born, self.grow = born, grow          # grow: seconds to reach full size (0 = instant)


# ---------------------------------------------------------------- app
class App:
    def __init__(self, effect=None):
        self.cfg = load_settings()
        self.opt = dict(DEFAULTS)
        self.opt.update({k: v for k, v in self.cfg.get("opt", {}).items() if k in DEFAULTS})
        self.mons = monitors()
        scr = self.cfg.get("screen_cfg", {})
        default_on = lambda i: (i >= 2) or len(self.mons) == 1
        self.scfg = {i: {"on": scr.get(str(i), {}).get("on", default_on(i)),
                         "front": scr.get(str(i), {}).get("front", True)}
                     for i in range(1, len(self.mons) + 1)}
        if not any(v["on"] for v in self.scfg.values()):
            self.scfg[1]["on"] = True
        ms = self.mons
        self.ox, self.oy = min(m[0] for m in ms), min(m[1] for m in ms)
        self.w = max(m[2] for m in ms) - self.ox
        self.h = max(m[3] for m in ms) - self.oy

        pygame.init()
        self.wins = []          # [screen index, pygame.Window, hwnd, Rect in canvas coords]
        self.skip = set()
        self.canvas = pygame.Surface((self.w, self.h))
        self.canvas.fill(KEY)
        for i in self.scfg:
            if self.scfg[i]["on"]:
                self.open_window(i)
        self.apply_layers()
        self.hz = max([refresh_rate(m) for m in ms] + [60])
        self.apply_fps()

        nb = self.w // BUCKET + 1

        def floor_at(x):
            for m in ms:
                if m[0] <= x < m[2]:
                    return work_bottom(x, (m[1] + m[3]) // 2) - self.oy
            return self.h + 100
        self.gbase = [floor_at(self.ox + k * BUCKET) for k in range(nb)]
        self.ground = [0.0] * nb
        self.windows, self.win_index, self.piles = [], {}, {}
        self.flakes, self.bits, self.decor, self.actors = [], [], [], []
        self.pets, self.next_pet, self.pets_ready = [], 0.0, False
        self.wind, self.t, self.frame = 0.0, 0.0, 0
        self.mouse = None
        self.paused = False
        self.running = True
        self.prev_dirty = []
        self.hk = queue.Queue()
        self.sprites = {}
        now = time.time()
        self.next_at = {k: now + self.opt[k + "_every"] * random.uniform(0.5, 1.0)
                        for k in ("tree", "snowman", "yeti", "plow", "train")}
        self.next_at["chaos"] = now + self.opt["chaos_every"]
        self.next_wind = now
        self.next_layer = now

        for d in self.cfg.get("decor", []):
            if d.get("kind") in ("tree", "snowman"):
                self.decor.append(Decor(d["kind"], float(d["x"])))

        self.effect = None
        self.set_effect(effect or self.cfg.get("effect", "snow"))

        try:   # own taskbar identity, so Windows shows our icon instead of python's
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DesktopSnow.App")
        except Exception:
            pass
        self.tk = tk.Tk()
        self.tk.withdraw()
        ico = os.path.join(HERE, "snow.ico")
        if not os.path.exists(ico):
            make_icon(ico)
        try:
            self.tk.iconbitmap(default=ico)            # every Tk window (panel too) uses the snow icon
        except tk.TclError:
            pass
        self.wall_mode = tk.StringVar(value=self.cfg.get("wallpaper", "off"))
        self.wall_current = None
        if "original_wallpaper" not in self.cfg:
            self.cfg["original_wallpaper"] = wallpaper.get_wallpaper()
        self.build_panel()
        self.apply_wallpaper()
        threading.Thread(target=self.hotkeys, daemon=True).start()
        threading.Thread(target=self.tray, daemon=True).start()

    # ================================================================ settings
    def save(self):
        self.cfg["effect"] = self.effect
        self.cfg["wallpaper"] = self.wall_mode.get()
        self.cfg["opt"] = self.opt
        self.cfg["screen_cfg"] = {str(i): v for i, v in self.scfg.items()}
        self.cfg["decor"] = [{"kind": d.kind, "x": round(d.x)} for d in self.decor
                             if d.host is None and not d.falling]
        try:
            with open(SETTINGS, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=1, ensure_ascii=False)
        except Exception:
            pass

    def save_soon(self):
        if getattr(self, "_save_job", None):
            self.tk.after_cancel(self._save_job)
        self._save_job = self.tk.after(600, self.save)

    def apply_fps(self):
        global FPS, S
        FPS = max(30, min(360, int(self.opt["fps"]) or self.hz))
        S = 60.0 / FPS

    def apply_layers(self):
        for i, win, hwnd, _ in self.wins:
            if self.scfg[i]["front"]:
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x13)      # always on top
            else:
                user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x13)      # not topmost
                user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x13)       # behind every app (on the desktop)
        if getattr(self, "panel_hwnd", None):                         # control panel stays above the snow
            user32.SetWindowPos(self.panel_hwnd, -1, 0, 0, 0, 0, 0x13)

    # ================================================================ screens (live, no restart)
    def open_window(self, i):
        if any(w[0] == i for w in self.wins):
            return
        m = self.mons[i - 1]
        title = f"Desktop Snow overlay {i}"
        win = pygame.Window(title, (m[2] - m[0], m[3] - m[1]), (m[0], m[1]), borderless=True)
        hwnd = user32.FindWindowW(None, title)
        ex = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, ex | 0x80000 | 0x20 | 0x80 | 0x8000000)
        user32.SetLayeredWindowAttributes(hwnd, KEY[0] | KEY[1] << 8 | KEY[2] << 16, 0, 1)
        user32.SetWindowPos(hwnd, -1, m[0], m[1], m[2] - m[0], m[3] - m[1], 0x10 | 0x40 | 0x20)
        R = pygame.Rect(m[0] - self.ox, m[1] - self.oy, m[2] - m[0], m[3] - m[1])
        self.canvas.fill(KEY, R)
        surf = win.get_surface()
        surf.fill(KEY)
        win.flip()
        self.wins.append([i, win, hwnd, R])
        self.wins.sort(key=lambda w: w[0])
        self.skip.add(hwnd)

    def close_window(self, i):
        for w in list(self.wins):
            if w[0] == i:
                self.wins.remove(w)
                self.skip.discard(w[2])
                w[1].destroy()

    def area(self):
        """(left, right, top, bottom) of a random enabled screen, weighted by width (canvas coords)."""
        R = random.choices([w[3] for w in self.wins], weights=[w[3].w for w in self.wins])[0]
        return R.left, R.right, R.top, R.bottom

    def on_screen(self, x):
        return any(w[3].left - 30 <= x < w[3].right + 30 for w in self.wins)

    def rand_x(self):
        lo, hi = self.area()[:2]
        return random.uniform(lo + (hi - lo) * 0.05, lo + (hi - lo) * 0.95)

    # ================================================================ effects
    def count(self):
        width = sum(w[3].w for w in self.wins) or 1920
        return max(1, int(EFFECTS[self.effect][0] * self.opt["density"] * max(1.0, width / 1920)))

    def set_effect(self, name):
        if name not in EFFECTS:
            name = "snow"
        self.effect = name
        self.fcache = {}
        self.flakes = [self.spawn(random.uniform(0, self.h)) for _ in range(self.count())]
        if hasattr(self, "effect_var"):
            self.effect_var.set(name)

    def flake_sprite(self, var, r, sq=0):
        k = (var, r, sq)
        spr = self.fcache.get(k)
        if spr is not None:
            return spr
        col = EFFECTS[self.effect][1][var]
        eff = self.effect
        if eff == "snow":
            n = r * 2 + 5                       # round cartoon puff: ink outline, blue shade, white shine
            spr = pygame.Surface((n, n)); spr.fill(KEY)
            c = n // 2
            o = max(1, r // 4)
            pygame.draw.circle(spr, INK, (c, c), r + 2)
            pygame.draw.circle(spr, SNOW_SHADE, (c, c), r)
            pygame.draw.circle(spr, col, (c - o, c - o), max(1, r - o))
            pygame.draw.circle(spr, (255, 255, 255), (c - r // 2, c - r // 2), max(1, r // 3))
        elif eff in ("leaves", "sakura"):
            hh = max(3, int(r * 2 * (0.25 + sq * 0.24)))
            spr = pygame.Surface((r * 2 + 2, hh + 2)); spr.fill(KEY)
            pygame.draw.ellipse(spr, INK if eff == "leaves" else (220, 120, 150), spr.get_rect())
            pygame.draw.ellipse(spr, col, spr.get_rect().inflate(-2, -2))
        elif eff == "fireflies":
            spr = pygame.Surface((r * 4 + 2, r * 4 + 2)); spr.fill(KEY)
            c = r * 2 + 1
            pygame.draw.circle(spr, tuple(int(v * 0.55) for v in col), (c, c), r * 2)
            pygame.draw.circle(spr, col, (c, c), r)
        elif eff == "rain":
            spr = pygame.Surface((3, 18)); spr.fill(KEY)
            pygame.draw.line(spr, col, (1, 0), (1, 17), 2)
        else:
            spr = pygame.Surface((46, 56)); spr.fill(KEY)
            pygame.draw.line(spr, col, (3, 53), (43, 3), 3)
            pygame.draw.circle(spr, (255, 255, 255), (4, 52), 3)
        spr.set_colorkey(KEY)
        self.fcache[k] = spr
        return spr

    def spawn(self, y=None):
        _, cols, size, speed, _, _ = EFFECTS[self.effect]
        f = Flake()
        lo, hi, top, bot = self.area()
        f.x = random.uniform(lo, hi)
        f.y = top - 10 if y is None else top + (y / self.h) * (bot - top)
        a, b = sorted((self.opt["size_min"], self.opt["size_max"]))
        if self.effect == "snow":
            f.r = random.uniform(a, b)                       # every flake gets its own size in the range
        else:                                                # other effects scale their own base size
            f.r = random.uniform(size[0] * a / 3.0, size[1] * b / 8.0)
        f.vy = random.uniform(*speed)
        f.phase = random.uniform(0, math.tau)
        f.var = random.randrange(len(cols))
        if self.effect == "fireflies":
            f.y = random.uniform(top + (bot - top) * 0.3, bot)
        if self.effect == "starfall":
            f.x = random.uniform(lo, hi + (hi - lo) * 0.3)
            f.y = random.uniform(top - (bot - top), top) if y is not None else random.uniform(top - 400, top - 20)
        return f

    def burst(self, x, y, n=10, vx=0.0, spread=2.5):
        for _ in range(n):
            b = Bit()
            b.x, b.y = x + random.uniform(-6, 6), y + random.uniform(-4, 2)
            b.vx = vx * random.uniform(0.4, 1.0) + random.uniform(-spread, spread)
            b.vy = random.uniform(-3.5, -0.5)
            self.bits.append(b)
        if len(self.bits) > 2000:
            self.bits = self.bits[-2000:]

    # ================================================================ windows
    def refresh_windows(self):
        try:
            wins = list_windows(self.skip, self.ox, self.oy)
        except Exception:
            wins = []
        alive = set()
        for h, l, t, r, b in wins:
            alive.add(h)
            p = self.piles.get(h)
            if p is not None and p["rect"] != (l, t, r) and p["rect"][2] - p["rect"][0] == r - l:
                ol, ot, _ = p["rect"]
                sens = self.opt["shake_sens"]
                if sens > 0:
                    self.spill(h, p, min(1.0, (abs(l - ol) + abs(t - ot)) * sens / 60.0), l - ol)
                p["rect"] = (l, t, r)
            elif p is None or p["rect"] != (l, t, r):
                if p is not None:
                    self.slide_off(h, p)
                self.piles[h] = {"rect": (l, t, r), "h": [0.0] * max(1, (r - l) // BUCKET)}
        for h in list(self.piles):
            if h not in alive:
                self.slide_off(h, self.piles.pop(h))
        self.windows = wins
        self.win_index = {w[0]: i for i, w in enumerate(wins)}

    def spill(self, h, p, frac, dx):
        l, t, r = p["rect"]
        if frac < 0.08:
            return
        for i, hgt in enumerate(p["h"]):
            lost = hgt * frac * random.uniform(0.6, 1.0)
            if lost > 0.3:
                p["h"][i] -= lost
                self.burst(l + i * BUCKET, t - hgt, max(1, int(lost * 0.8)), vx=-dx * 0.15, spread=1.2)
        if frac > 0.6:
            self.drop_decor(h, l)

    def slide_off(self, h, p):
        l, t, r = p["rect"]
        for i, hgt in enumerate(p["h"]):
            if hgt > 1:
                self.burst(l + i * BUCKET, t - hgt, max(1, int(hgt * 0.6)), spread=1.2)
        self.drop_decor(h, l, force=True)

    def drop_decor(self, h, l, force=False):
        for d in self.decor:
            if d.host == h and (force or d.kind == "tree" or self.opt["snowman_fall"]):
                d.host, d.falling, d.vy = None, True, 0.0
                d.x = l + d.rel

    def covered(self, x, y, upto):
        for w in self.windows[:upto]:
            if w[1] <= x < w[3] and w[2] <= y < w[4]:
                return True
        return False

    def bucket(self, x):
        return max(0, min(int(x // BUCKET), len(self.ground) - 1))

    def find_surface(self, x, y0, y1, windows=True, ground=True):
        if windows:
            pm = self.opt["pile_max"]
            for i, (h, l, t, r, b) in enumerate(self.windows):
                if l <= x < r and y0 < t <= y1 + pm + 1:
                    p = self.piles.get(h)
                    if not p:
                        continue
                    k = min(int((x - l) // BUCKET), len(p["h"]) - 1)
                    surf = t - p["h"][k]
                    if y0 < surf <= y1 and not self.covered(x, t - 1, i):
                        return h, surf
        if ground:
            k = self.bucket(x)
            surf = self.gbase[k] - self.ground[k]
            if y1 >= surf:
                return None, surf
        return None

    def win_rect(self, h):
        i = self.win_index.get(h)
        return self.windows[i] if i is not None else None

    def add_snow(self, host, x, amt):
        pm = self.opt["pile_max"]
        if host is None:
            arr, cap, k = self.ground, pm * 1.4, self.bucket(x)
        else:
            p = self.piles.get(host)
            if not p:
                return
            arr, cap = p["h"], pm
            k = max(0, min(int((x - p["rect"][0]) // BUCKET), len(arr) - 1))
        if arr[k] < cap:
            arr[k] += amt
            for d in (-1, 1):
                j = k + d
                if 0 <= j < len(arr) and arr[j] < arr[k] - 2:
                    arr[j] += amt * 0.6

    # ================================================================ simulation
    def step_flakes(self):
        eff, o = self.effect, self.opt
        drift, piles = EFFECTS[eff][4], EFFECTS[eff][5]
        w, h = self.w, self.h
        sp = o["speed"] * S
        wind = self.wind * (1.5 if eff != "rain" else 0.5)
        pw, pg, rate = o["pile_windows"], o["pile_taskbar"], o["pile_rate"] * 0.7
        keep = []
        for f in self.flakes:
            y0 = f.y
            f.phase += 0.03 * S
            if eff == "fireflies":
                f.x += math.cos(f.phase * 1.3) * drift * S
                f.y += (math.sin(f.phase) * drift + f.vy * 0.3) * S
                if not (0 < f.y < h + 10):
                    f.y = random.uniform(h * 0.3, h)
                keep.append(f)
                continue
            if eff == "starfall":
                f.x -= f.vy * 0.8 * sp
                f.y += f.vy * sp
                if f.y < h + 60 and f.x > -60:
                    keep.append(f)
                continue
            f.x += (math.sin(f.phase) * drift * 0.5 + wind) * S
            f.y += f.vy * sp
            if f.x < -20:
                f.x += w + 30
            elif f.x > w + 20:
                f.x -= w + 30
            if piles and (pw or pg):
                hit = self.find_surface(f.x, y0, f.y, pw, pg)
                if hit:
                    if rate > 0:
                        self.add_snow(hit[0], f.x, f.r * rate * 0.6)
                    continue
            if f.y < h + 20:
                keep.append(f)
        n = self.count()
        while len(keep) < n:
            keep.append(self.spawn())
        if len(keep) > n * 1.2:
            keep = keep[:n]
        self.flakes = keep

    def step_bits(self):
        keep = []
        g, damp = 0.25 * S, 0.97 ** S
        pw, pg = self.opt["pile_windows"], self.opt["pile_taskbar"]
        for b in self.bits:
            y0 = b.y
            b.vy = min(b.vy + g, 9)
            b.vx *= damp
            b.x += b.vx * S
            b.y += b.vy * S
            if b.vy > 0 and 0 <= b.x < self.w:
                hit = self.find_surface(b.x, y0, b.y, pw, pg)
                if hit:
                    self.add_snow(hit[0], b.x, 1.2)
                    continue
            if b.y < self.h + 10 and -50 < b.x < self.w + 50:
                keep.append(b)
        self.bits = keep

    def step_decor(self):
        for d in self.decor:
            if d.falling:
                y0 = d.y
                d.vy = min(d.vy + 0.5 * S, 18)
                d.y += d.vy * S
                hit = self.find_surface(d.x, y0, d.y)
                if hit:
                    d.falling, d.host = False, hit[0]
                    if d.host is not None:
                        d.rel = d.x - self.win_rect(d.host)[1]
                    elif d.vy > 6:
                        self.burst(d.x, d.y, 8)
                    self.save_soon()
            elif d.host is not None:
                wr = self.win_rect(d.host)
                if wr is None:
                    d.host, d.falling, d.vy = None, True, 0.0
                    continue
                d.x = wr[1] + d.rel
                p = self.piles.get(d.host)
                k = max(0, min(int(d.rel // BUCKET), len(p["h"]) - 1)) if p else 0
                d.y = wr[2] - (min(p["h"][k], 6) if p else 0)
            else:
                k = self.bucket(d.x)
                d.y = self.gbase[k] - min(self.ground[k], 6)

    def step_melt(self):
        m = self.opt["melt"]
        if m <= 0 or self.frame % 10:
            return
        amt = m * 0.02 * S * 10
        self.ground = [max(0.0, v - amt) for v in self.ground]
        for p in self.piles.values():
            p["h"] = [max(0.0, v - amt) for v in p["h"]]

    def step_mouse(self):
        if not self.opt["mouse_push"]:
            return
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        x, y = pt.x - self.ox, pt.y - self.oy
        last, self.mouse = self.mouse, (x, y)
        if last is None:
            return
        dx = x - last[0]
        if abs(dx) + abs(y - last[1]) < 2:
            return
        k = self.bucket(x)
        if self.ground[k] > 1 and self.gbase[k] - self.ground[k] - 6 <= y <= self.gbase[k] + 4:
            self.push(self.ground, k, x, self.gbase[k], dx)
        pm = self.opt["pile_max"]
        for i, (h, l, t, r, b) in enumerate(self.windows):
            if l <= x < r and t - pm - 6 <= y <= t + 4 and not self.covered(x, y, i):
                p = self.piles.get(h)
                if p:
                    j = min(int((x - l) // BUCKET), len(p["h"]) - 1)
                    if p["h"][j] > 1:
                        self.push(p["h"], j, x, t, dx)
                break

    def push(self, arr, k, x, base, dx):
        total = 0.0
        for j in range(k - 2, k + 3):
            if 0 <= j < len(arr):
                total += arr[j]
                arr[j] = 0.0
        if total > 1:
            self.burst(x, base - 4, int(min(14, total)), vx=dx * 0.6)

    # ================================================================ timers, chaos
    def step_timers(self):
        now, o = time.time(), self.opt
        if now >= self.next_wind:
            self.next_wind = now + o["wind_change"] * random.uniform(0.6, 1.4)
            self.wind = random.uniform(-0.6, 0.6) * o["wind"]
        if now >= self.next_layer:
            self.next_layer = now + 1.0
            self.apply_layers()
        for kind in ("tree", "snowman", "yeti", "plow", "train"):
            if now < self.next_at[kind]:
                continue
            self.next_at[kind] = now + o[kind + "_every"] * random.uniform(0.7, 1.3)
            if not o[kind + "_auto"]:
                continue
            if kind == "tree":
                self.add_tree()
            elif kind == "snowman":
                self.add_snowman()
            elif kind == "yeti":
                self.call_yeti()
            elif kind == "plow":
                if sum(self.ground) / len(self.ground) >= o["plow_min_snow"]:
                    self.call_plow()
            else:
                self.send_train()
        if o["chaos"] and now >= self.next_at["chaos"]:
            self.next_at["chaos"] = now + o["chaos_every"]
            self.chaos()

    def chaos(self):
        o = self.opt
        skip = {"chaos", "chaos_every", "chaos_amount", "chaos_effects", "chaos_visitors", "chaos_decor", "fps"}
        frac = o["chaos_amount"] / 100.0
        for tab, key, label, typ, default, lo, hi in SPEC:
            if key in skip or random.random() > frac:
                continue
            if typ == "b":
                val = random.random() < 0.5
            elif typ == "c":
                val = random.choice(lo)
            elif typ == "i":
                val = random.randint(int(lo), int(hi))
            else:
                if key.endswith("_every"):
                    val = random.uniform(3, 60)        # keep things happening
                elif key.endswith("_time"):
                    val = random.uniform(0.5, 15)
                else:
                    val = random.uniform(lo, hi)
            self.set_opt(key, val)
        if o["chaos_effects"] and random.random() < frac:
            self.set_effect(random.choice(ORDER))
        elif self.effect == "snow" or random.random() < 0.5:
            self.flakes = self.flakes[:self.count()]
        if o["chaos_visitors"]:
            random.choice([self.call_yeti, self.call_plow, self.send_train])()
        if o["chaos_decor"]:
            random.choice([self.add_tree, self.add_snowman])()

    def set_opt(self, key, val):
        self.opt[key] = val
        var = getattr(self, "vars", {}).get(key)
        if var is not None:
            self._quiet = True
            var.set(val)
            self._quiet = False

    # ================================================================ actors
    def call_yeti(self):
        if any(a["kind"] == "yeti" for a in self.actors):
            return
        d = 1 if random.random() < 0.5 else -1
        lo, hi = self.area()[:2]
        self.actors.append({"kind": "yeti", "x": lo - 80.0 if d > 0 else hi + 80.0, "dir": d, "spawn_dir": d,
                            "lo": lo, "hi": hi,
                            "state": "walk", "timer": 0.0, "target": None})
        if self.opt["yeti_roar"]:
            for h, p in list(self.piles.items()):
                self.spill(h, p, 1.0, random.uniform(-20, 20))

    def call_plow(self):
        if any(a["kind"] == "plow" for a in self.actors):
            return
        d = 1 if random.random() < 0.5 else -1
        lo, hi = self.area()[:2]
        self.actors.append({"kind": "plow", "x": lo - 100.0 if d > 0 else hi + 100.0, "dir": d, "pushed": 0.0,
                            "lo": lo, "hi": hi})

    def send_train(self, cargo=None):
        c = cargo or self.opt["train_cargo"]
        c = {"ağaç": "tree", "kardan adam": "snowman"}.get(c, c)
        if c not in ("tree", "snowman"):
            c = random.choice(["tree", "snowman"])
        if c == "tree" and self.n("tree") >= self.opt["tree_max"]:
            c = "snowman"
        lo, hi = self.area()[:2]
        self.actors.append({"kind": "train", "x": lo - 260.0, "dir": 1, "cargo": c, "smoke": [], "lo": lo, "hi": hi,
                            "stop": random.uniform(lo + (hi - lo) * 0.3, lo + (hi - lo) * 0.8),
                            "state": "in", "timer": 0.0})

    def n(self, kind):
        return sum(1 for d in self.decor if d.kind == kind)

    def smash(self, d):
        self.burst(d.x, d.y - 20, 26, spread=3.5)
        if d in self.decor:
            self.decor.remove(d)
        self.save_soon()

    def step_actors(self):
        for a in list(self.actors):
            getattr(self, "step_" + a["kind"])(a)

    def yeti_targets(self):
        o = self.opt
        return [d for d in self.decor if d.host is None and not d.falling and
                ((d.kind == "snowman" and o["yeti_smash_snowmen"]) or (d.kind == "tree" and o["yeti_smash_trees"]))]

    def step_yeti(self, a):
        o = self.opt
        s, sp = o["yeti_size"], 2.2 * o["yeti_speed"] * S
        if o["yeti_eat_snow"] and 0 <= a["x"] < self.w:
            k = self.bucket(a["x"])
            for j in range(k - 3, k + 4):
                if 0 <= j < len(self.ground):
                    self.ground[j] *= 0.9
        if a["state"] == "walk":
            targets = self.yeti_targets()
            if a["target"] not in targets:
                a["target"] = min(targets, key=lambda d: abs(d.x - a["x"])) if targets else None
            if a["target"] is None:
                # nothing to smash: keep walking across the whole screen and out the far side
                # (before, it turned back to the nearest edge and vanished before you could see it)
                a["state"] = "leave"
                if "exit" not in a:
                    a["exit"] = a.get("spawn_dir", a["dir"])
                a["dir"] = a["exit"]
            else:
                tx = a["target"].x
                a["dir"] = 1 if tx > a["x"] else -1
                if abs(tx - a["x"]) < 30 * s:
                    a["state"], a["timer"] = "stomp", 0.0
                else:
                    a["x"] += a["dir"] * sp
        elif a["state"] == "stomp":
            a["timer"] += S / o["yeti_stomp"]
            if a["timer"] - S / o["yeti_stomp"] < 36 <= a["timer"] and a["target"] in self.decor:
                self.smash(a["target"])
            if a["timer"] > 60:
                a["state"], a["target"] = "walk", None
        else:
            a["x"] += a["dir"] * sp * 1.3
            if a["x"] < a["lo"] - 100 * s or a["x"] > a["hi"] + 100 * s:
                self.actors.remove(a)

    def step_plow(self, a):
        o = self.opt
        s = o["plow_size"]
        a["x"] += a["dir"] * 3.0 * o["plow_speed"] * S
        front = a["x"] + a["dir"] * 40 * s
        if 0 <= front < self.w:
            for j in range(self.bucket(front - 4 * s), self.bucket(front + 4 * s) + 1):
                a["pushed"] = min(a["pushed"] + self.ground[j], 400)
                self.ground[j] = 0.0
            if random.random() < 0.3 * S and a["pushed"] > 5:
                self.burst(front, self.gbase[self.bucket(front)] - 6, 1, vx=a["dir"] * 3, spread=1)
        for d in list(self.decor):
            if d.host is None and not d.falling and abs(d.x - front) < 12 * s:
                if (d.kind == "snowman" and o["plow_snowmen"]) or (d.kind == "tree" and o["plow_trees"]):
                    self.smash(d)
                    a["pushed"] += 40
        if a["x"] < a["lo"] - 150 * s or a["x"] > a["hi"] + 150 * s:
            self.actors.remove(a)

    def step_train(self, a):
        o = self.opt
        s, sp = o["train_size"], 2.6 * o["train_speed"] * S
        if a["state"] == "in":
            a["x"] += sp
            if a["x"] >= a["stop"]:
                a["state"], a["timer"] = "stop", 0.0
        elif a["state"] == "stop":
            a["timer"] += S
            if a["timer"] >= 50 and a["cargo"]:
                self.place(a["cargo"], a["x"] - 130 * s, "ground", drop_from=60 * s)
                a["cargo"] = None
            if a["timer"] > 60 + o["train_wait"] * 60:
                a["state"] = "out"
        else:
            a["x"] += sp * 1.2
            if a["x"] > a["hi"] + 300 * s:
                self.actors.remove(a)
        if self.frame % max(1, int(9 / S)) == 0:
            a["smoke"].append([a["x"] + 26 * s, self.gbase[self.bucket(a["x"])] - 56 * s, 4.0 * s])
        for p in a["smoke"]:
            p[1] -= 0.8 * S; p[0] -= 0.4 * S; p[2] += 0.35 * S
        a["smoke"] = [p for p in a["smoke"] if p[2] < 16 * s]

    # ================================================================ decorations
    # ================================================================ pets
    def pet_breed(self, sp):
        pick = self.opt["dog_breed" if sp == "dog" else "cat_breed"]
        names = [b[0] for b in (DOGS if sp == "dog" else CATS)]
        return names.index(pick) if pick in names else random.randrange(len(names))

    def add_pet(self, sp, enter=True):
        lo, hi = self.area()[:2]
        d = random.choice((-1, 1))
        x = (lo - 40 if d > 0 else hi + 40) if enter else random.uniform(lo + 60, hi - 60)
        v = random.uniform(0.85, 1.15) if self.opt["pet_variety"] else 1.0
        p = {"sp": sp, "breed": self.pet_breed(sp), "x": float(x), "dir": d, "lo": lo, "hi": hi,
             "state": "walk", "timer": 0.0, "phase": random.uniform(0, 6.28), "seed": random.randrange(1000),
             "var": v, "spd": random.uniform(0.8, 1.2) if self.opt["pet_variety"] else 1.0,
             "wag": 1.0, "sleep": False, "breath": True, "enter": enter}
        p["timer"] = 60 * self.opt["pet_state_time"] * random.uniform(0.6, 1.4) + (200 if enter else 0)
        self.pets.append(p)

    def pet_next_state(self, p):
        o = self.opt
        cold = self.effect in ("snow", "rain")
        opts = {"walk": o["pet_walk"], "sit": o["pet_sit"], "lie": o["pet_lie"], "look": o["pet_look"],
                "shiver": o["pet_shiver"] * (1 if cold else 0.1), "play": o["pet_play"], "leave": o["pet_leave"]}
        opts = {k: (v if o["anim_" + k] else 0) for k, v in opts.items()}
        if sum(opts.values()) <= 0:
            opts = {"stand": 1}
        st = random.choices(list(opts), weights=list(opts.values()))[0]
        p["state"], p["sleep"] = st, st == "lie" and random.random() < 0.7
        p["timer"] = 60 * o["pet_state_time"] * random.uniform(0.5, 1.5) * (1.6 if st == "lie" else 1)
        if st in ("walk", "play") and random.random() < 0.4:
            p["dir"] *= -1
        if st == "leave":
            p["dir"] = -1 if p["x"] - p["lo"] < p["hi"] - p["x"] else 1

    def step_pets(self):
        o, now = self.opt, time.time()
        want = {"dog": o["dog_count"], "cat": o["cat_count"]} if o["pets_on"] else {"dog": 0, "cat": 0}
        for sp in ("dog", "cat"):
            mine = [p for p in self.pets if p["sp"] == sp and p["state"] != "leave"]
            if len(mine) > want[sp]:
                for p in mine[want[sp]:]:
                    p["state"], p["dir"] = "leave", (-1 if p["x"] - p["lo"] < p["hi"] - p["x"] else 1)
                    p["timer"] = 1e9
            elif len(mine) < want[sp] and self.wins:
                if not self.pets_ready:
                    for _ in range(want[sp] - len(mine)):
                        self.add_pet(sp, enter=False)
                elif now >= self.next_pet:
                    self.add_pet(sp)
                    self.next_pet = now + o["pet_respawn"] * random.uniform(0.6, 1.4)
        self.pets_ready = True
        for p in list(self.pets):
            p["wag"], p["breath"] = o["pet_wag"], o["pet_breath"]
            st = p["state"]
            v = 0.0
            if st in ("walk", "leave"):
                v = (1.1 if p["sp"] == "dog" else 0.8) * o["pet_speed"] * p["spd"] * (1.5 if st == "leave" else 1)
            elif st == "play":
                v = 1.6 * o["pet_speed"] * p["spd"]
            if v:
                p["x"] += p["dir"] * v * S
                p["phase"] += 0.22 * v * S / max(0.5, o["pet_size"])
                amt = o["pet_snow_amt"]
                if o["pet_snow"] and amt > 0 and self.ground:
                    k = self.bucket(p["x"] + p["dir"] * 10 * o["pet_size"])
                    if self.ground[k] > 1.5:
                        # frame-rate independent: amt=1 moves ~1.5% of the snow under the paws per 60 Hz tick
                        a = self.ground[k] * min(0.5, 0.015 * amt * amt) * S
                        self.ground[k] -= a
                        nb = max(0, min(len(self.ground) - 1, k + p["dir"]))
                        self.ground[nb] += a * 0.6
                        if random.random() < 0.04 * amt * S:
                            self.burst(p["x"] + p["dir"] * 8, self.gbase[k] - self.ground[k] - 2,
                                       max(1, int(2 * amt)), vx=p["dir"] * 1.4, spread=1.0)
                if st == "leave":
                    if p["x"] < p["lo"] - 80 or p["x"] > p["hi"] + 80:
                        self.pets.remove(p)
                        self.next_pet = max(self.next_pet, now + o["pet_respawn"] * random.uniform(0.6, 1.4))
                        continue
                elif not p["enter"]:
                    if p["x"] < p["lo"] + 40:
                        p["dir"] = 1
                    elif p["x"] > p["hi"] - 40:
                        p["dir"] = -1
                elif p["lo"] + 60 < p["x"] < p["hi"] - 60:
                    p["enter"] = False
            if st in ("walk", "sit", "lie", "look", "shiver", "play") and not o["anim_" + st]:
                p["timer"] = 0
            p["timer"] -= S
            if p["timer"] <= 0 and not p["enter"]:
                self.pet_next_state(p)

    def remove_pets(self):
        for p in self.pets:
            p["state"], p["timer"] = "leave", 1e9
            p["dir"] = -1 if p["x"] - p["lo"] < p["hi"] - p["x"] else 1

    def place(self, kind, x, where, drop_from=60):
        d = Decor(kind, x, self.t, self.opt[kind + "_grow_time"] if self.opt[kind + "_grow"] else 0.0)
        d.falling = True
        d.y = self.gbase[self.bucket(x)] - drop_from
        if where == "window":
            for i, (h, l, t, r, b) in enumerate(self.windows):
                if t < 90 or r - l < 120:
                    continue
                for _ in range(15):
                    xx = random.uniform(l + 30, r - 30)
                    if not self.covered(xx, t - 1, i):
                        d.x, d.y = xx, t - drop_from
                        self.decor.append(d)
                        return
        self.decor.append(d)

    def pick_where(self, kind):
        w = self.opt[kind + "_where"]
        if w == "ikisi de":
            w = random.choice(WHERE[:2])
        return "window" if w == "pencereler" else "ground"

    def add_tree(self, where=None):
        if self.n("tree") >= self.opt["tree_max"]:
            return
        taken = [d.x for d in self.decor if d.kind == "tree"]
        x = self.rand_x()
        for _ in range(30):
            if all(abs(x - t) > 90 * self.opt["tree_size"] for t in taken):
                break
            x = self.rand_x()
        self.place("tree", x, where or self.pick_where("tree"))

    def add_snowman(self, where=None):
        if self.n("snowman") >= self.opt["snowman_max"]:
            return
        self.place("snowman", self.rand_x(), where or self.pick_where("snowman"))

    def clear_decor(self):
        self.decor = []
        self.save()

    def clear_snow(self):
        for p in self.piles.values():
            p["h"] = [0.0] * len(p["h"])
        self.ground = [0.0] * len(self.ground)

    def decor_scale(self, d):
        s = self.opt[d.kind + "_size"]
        if d.grow > 0:
            prog = min(1.0, (self.t - d.born) / (d.grow * 60.0))
            s *= 0.12 + 0.88 * (prog ** 0.7)
        return s

    def decor_sprite(self, kind, seed, frame, scale):
        q = max(0.1, round(scale * 20) / 20)
        k = (kind, seed if kind == "tree" else 0, frame if kind == "tree" else 0, q)
        spr = self.sprites.get(k)
        if spr is None:
            if len(self.sprites) > 600:
                self.sprites.clear()
            if kind == "tree":
                spr = art_hd.tree(frame, seed, q)[0]
            else:
                spr = art_hd.snowman(q)[0]
            self.sprites[k] = spr
        return spr

    # ================================================================ rendering
    def render(self):
        cv = self.canvas
        if len(self.prev_dirty) > 150:      # one memset is cheaper than hundreds of overlapping fills
            for w in self.wins:
                cv.fill(KEY, w[3])
        else:
            for r in self.prev_dirty:
                cv.fill(KEY, r)
        dirty = []
        g = G(cv, dirty)
        blit = cv.blit

        frame = int(self.t * self.opt["twinkle"] / 30) % 3
        for d in self.decor:
            if d.host is not None and not d.falling:
                if self.covered(d.x, d.y - 2, self.win_index.get(d.host, 0)):
                    continue
            spr = self.decor_sprite(d.kind, d.seed, frame, self.decor_scale(d))
            dirty.append(blit(spr, (int(d.x - spr.get_width() / 2), int(d.y - spr.get_height() + 4))))

        for a in self.actors:
            y = self.gbase[self.bucket(a["x"])] if 0 <= a["x"] < self.w else self.gbase[0]
            k, o, x = a["kind"], self.opt, a["x"]
            if k == "yeti":
                spr, ax, ay = art_hd.yeti(a["dir"], self.t, a["state"] == "stomp", a["timer"], o["yeti_size"])
                dirty.append(blit(spr, (int(x - ax), int(y - ay))))
            elif k == "plow":
                spr, ax, ay = art_hd.plow(a["dir"], self.t, a["pushed"], o["plow_size"])
                dirty.append(blit(spr, (int(x - ax), int(y - ay))))
            else:
                s = o["train_size"]
                for sx, sy, r in a["smoke"]:
                    g.C(sx, sy, r, (236, 240, 248), (190, 198, 215))
                spr, ax, ay = art_hd.train(self.t, a["state"], s)
                dirty.append(blit(spr, (int(x - ax), int(y - ay))))
                cx = x - 130 * s
                if a["cargo"]:
                    spr = self.decor_sprite(a["cargo"], 3, frame, 0.8 * s)
                    dirty.append(blit(spr, (int(cx - spr.get_width() / 2), int(y - 14 * s - spr.get_height() + 4))))

        ps = self.opt["pet_size"]
        for p in self.pets:
            k = self.bucket(p["x"]) if 0 <= p["x"] < self.w else 0
            b = self.gbase[k] - min(self.ground[k] * 0.5, 6)
            self.blit_pet(g, blit, dirty, p, b, ps)

        # piles drawn AFTER decorations and visitors, so they stand in the snow, not on top of it
        if EFFECTS[self.effect][5] or any(v > 0.5 for v in self.ground):
            for i, (h, l, t, r, b) in enumerate(self.windows):
                p = self.piles.get(h)
                if not p:
                    continue
                arr, run, last = p["h"], [], len(p["h"]) - 1
                for k, v in enumerate(arr):
                    x = l + k * BUCKET
                    vis = v > 0.8 and not self.covered(x + 3, t - 1, i)
                    if vis:
                        run.append((x, v))
                    if (not vis or k == last) and run:
                        self.draw_run(g, run, t)
                        run = []
            run, last = [], len(self.ground) - 1
            for k, v in enumerate(self.ground):
                if v > 0.8:
                    run.append((k * BUCKET, v))
                if (v <= 0.8 or k == last) and run:
                    self.draw_run(g, run, self.gbase[run[0][0] // BUCKET])
                    run = []

        eff, fsp = self.effect, self.flake_sprite
        if eff == "snow":
            for f in self.flakes:
                r = max(1, int(f.r))
                spr = fsp(f.var, r)
                hw = spr.get_width() // 2
                dirty.append(blit(spr, (int(f.x - hw), int(f.y - hw))))
        elif eff in ("leaves", "sakura"):
            for f in self.flakes:
                sq = int(abs(math.sin(f.phase * 1.6)) * 3.99)
                r = max(2, int(f.r))
                dirty.append(blit(fsp(f.var, r, sq), (int(f.x - r), int(f.y))))
        elif eff == "fireflies":
            for f in self.flakes:
                glow = (math.sin(f.phase * 3) + 1) / 2
                if glow > 0.25:
                    rr = max(1, min(8, int(f.r * (0.4 + glow))))
                    dirty.append(blit(fsp(f.var, rr), (int(f.x - rr * 2), int(f.y - rr * 2))))
        elif eff == "rain":
            for f in self.flakes:
                dirty.append(blit(fsp(f.var, 0), (int(f.x), int(f.y - 16))))
        else:
            for f in self.flakes:
                dirty.append(blit(fsp(f.var, 0), (int(f.x), int(f.y - 54))))

        for b in self.bits:
            pygame.draw.circle(cv, SNOW_SHADE, (int(b.x), int(b.y)), 3)
            dirty.append(pygame.draw.circle(cv, SNOW, (int(b.x), int(b.y)), 2))

        # copy changed areas into each screen's window, one present per window
        changed = self.prev_dirty + dirty
        for _, win, _, R in self.wins:
            surf = win.get_surface()
            if len(changed) > 120:          # busy screen: one big copy beats hundreds of small ones
                surf.blit(cv, (0, 0), R)
                win.flip()
                continue
            jobs = []
            for r in changed:
                if r.colliderect(R):
                    c = r.clip(R)
                    jobs.append((cv, (c.x - R.x, c.y - R.y), c))
            if jobs:
                surf.blits(jobs, doreturn=False)
                win.flip()
        self.prev_dirty = dirty

    def blit_pet(self, g, blit, dirty, p, b, ps):
        br = (DOGS if p["sp"] == "dog" else CATS)[p["breed"]]
        st, t, x = p["state"], self.t, p["x"]
        sc = ps * self.opt["dog_size" if p["sp"] == "dog" else "cat_size"] * br[5] * p["var"] * 1.1
        leg = int(p["phase"] / (math.pi / 2)) % 4
        tail = [0, 1, 2, 1][int(t * 0.1 * max(0.05, p["wag"]) + p["seed"]) % 4]
        blink = 2 if (st == "lie" and p["sleep"]) else (1 if (t + p["seed"] * 37) % 220 < 7 else 0)
        draw_st = "walk" if st in ("leave", "play", "shiver", "stand") else st
        if st == "shiver":
            x += math.sin(t * 2.4) * 1.1 * sc
        if st == "play":
            b -= abs(math.sin(p["timer"] * 0.12)) * 14 * sc
        spr = pet_art.sprite(p["sp"], p["breed"], br, draw_st, leg if st != "shiver" else 0, tail, blink, sc,
                             p["dir"] < 0, p["seed"])
        sw, sh = spr.get_size()
        top = b - sh * pet_art.GROUND / pet_art.H
        dirty.append(blit(spr, (int(x - sw / 2), int(top))))
        d = -1 if p["dir"] < 0 else 1
        hx, hy = x + d * sw * 0.3, top + sh * 0.45
        if blink == 2:
            zt = (t * 0.6 + p["seed"]) % 60 / 60
            zx, zy, zs = hx + d * 6 * sc + zt * 8 * sc, top + sh * 0.5 - zt * 18 * sc, (2 + zt * 3) * sc
            for a0, a1 in (((zx, zy), (zx + zs, zy)), ((zx + zs, zy), (zx, zy + zs)), ((zx, zy + zs), (zx + zs, zy + zs))):
                g.L(a0[0], a0[1], a1[0], a1[1], (210, 220, 255), 2)
        if st == "shiver" and p["breath"]:
            k = (t * 0.5 + p["seed"]) % 40 / 40
            g.C(hx + d * (10 * sc + k * 10 * sc), hy - k * 6 * sc, (1.5 + k * 3.5) * sc, (236, 242, 252), (200, 210, 230))

    @staticmethod
    def draw_run(g, run, base):
        top = [(x + BUCKET / 2, base - v) for x, v in run]
        pts = [(run[0][0], base)] + top + [(run[-1][0] + BUCKET, base)]
        g.P(pts, SNOW_SHADE, None)
        g.P([(run[0][0] + 1, base - 2)] + [(x, y + 0) for x, y in top] + [(run[-1][0] + BUCKET - 1, base - 2)],
            SNOW, None)
        g.L(run[0][0], base, run[0][0], base, INK, 1)
        if len(top) > 1:
            g._rec(pygame.draw.lines(g.s, (150, 180, 220), False, top, 2))

    # ================================================================ wallpaper
    def apply_wallpaper(self):
        """Wallpaper feature is turned off: just put the user's own wallpaper back once if we changed it."""
        if self.cfg.get("wallpaper", "off") != "off" and self.cfg.get("original_wallpaper"):
            wallpaper.set_wallpaper(self.cfg["original_wallpaper"])
        self.cfg["wallpaper"] = "off"
        self.wall_mode.set("off")
        self.wall_current = None
        return
        mode = self.wall_mode.get()
        if mode == "off":
            if self.wall_current is not None and self.cfg.get("original_wallpaper"):
                wallpaper.set_wallpaper(self.cfg["original_wallpaper"])
            self.wall_current = None
            return
        phase = wallpaper.phase_for_hour(datetime.datetime.now().hour) if mode == "auto" else mode
        if phase != self.wall_current:
            self.wall_current = phase
            sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            threading.Thread(target=lambda: wallpaper.set_wallpaper(wallpaper.ensure(phase, sw, sh)),
                             daemon=True).start()

    # ================================================================ panel
    def build_panel(self):
        import ui
        p = ui.build(self, SPEC, ORDER, EFFECT_NAMES, DEFAULTS, EFFECTS)
        p.update_idletasks()
        pos = self.cfg.get("panel_pos")
        if pos:                                    # stay wherever the user left it
            p.geometry(f"+{pos[0]}+{pos[1]}")
        else:
            R = self.wins[0][3]
            p.geometry(f"+{self.ox + R.right - p.winfo_width() - 40}+{self.oy + R.y + 60}")
        if self.cfg.pop("panel_hidden", False):
            p.withdraw()
        p.update()
        self.panel_hwnd = user32.GetParent(p.winfo_id())
        self.skip.add(self.panel_hwnd)

    def remove_kind(self, kind):
        self.decor = [d for d in self.decor if d.kind != kind]
        self.save()

    def reset_defaults(self):
        for k, v in DEFAULTS.items():
            self.set_opt(k, v)
        self.apply_fps()
        self.save()

    def screen_front(self, i, var):
        self.scfg[i]["front"] = var.get()
        self.apply_layers()
        self.save()

    def screen_on(self, i, var):
        on = var.get()
        if not on and len(self.wins) <= 1:          # keep at least one screen
            var.set(True)
            return
        self.scfg[i]["on"] = on
        if on:
            self.open_window(i)
            self.apply_layers()
        else:
            self.close_window(i)
        self.flakes = [f for f in self.flakes if self.on_screen(f.x)]
        self.save()

    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def autostart_get(self):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY) as k:
                winreg.QueryValueEx(k, "Desktop Snow")
            return True
        except OSError:
            return False

    def autostart_set(self, on):
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                exe = sys.executable.replace("python.exe", "pythonw.exe")
                winreg.SetValueEx(k, "Desktop Snow", 0, winreg.REG_SZ,
                                  f'"{exe}" "{os.path.abspath(__file__)}"')
            else:
                try:
                    winreg.DeleteValue(k, "Desktop Snow")
                except OSError:
                    pass

    def restart(self):
        self.cfg["panel_hidden"] = self.panel.state() == "withdrawn"
        self.quit()
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable])
            return
        exe = sys.executable.replace("python.exe", "pythonw.exe")
        subprocess.Popen([exe if os.path.exists(exe) else sys.executable, os.path.abspath(__file__), "--restart"])

    # ================================================================ tray icon (bottom-right of the taskbar)
    def tray(self):
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
        user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        user32.DefWindowProcW.restype = LRESULT

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                        ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                        ("lpszClassName", wt.LPCWSTR)]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
                        ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", ctypes.c_wchar * 128),
                        ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", ctypes.c_wchar * 256),
                        ("uVersion", wt.UINT), ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", wt.DWORD),
                        ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON)]

        WM_TRAY = 0x8001
        shell32 = ctypes.windll.shell32
        user32.TrackPopupMenu.argtypes = [wt.HANDLE, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                          wt.HWND, ctypes.c_void_p]
        user32.LoadImageW.restype = wt.HANDLE
        user32.CreatePopupMenu.restype = wt.HANDLE
        user32.AppendMenuW.argtypes = [wt.HANDLE, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
        user32.CreateWindowExW.restype = wt.HWND
        user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_int, wt.HWND, wt.HANDLE, wt.HINSTANCE, ctypes.c_void_p]

        def proc(hwnd, msg, wp, lp):
            if msg == WM_TRAY:
                if lp in (0x202, 0x203):                   # left click / double click
                    self.hk.put(2)
                elif lp == 0x205:                          # right click: menu
                    menu = user32.CreatePopupMenu()
                    user32.AppendMenuW(menu, 0, 1, "Paneli göster")
                    user32.AppendMenuW(menu, 0, 2, "Devam et" if self.paused else "Duraklat")
                    user32.AppendMenuW(menu, 0x800, 0, None)
                    user32.AppendMenuW(menu, 0, 3, "Çıkış")
                    pt = wt.POINT(); user32.GetCursorPos(ctypes.byref(pt))
                    user32.SetForegroundWindow(hwnd)
                    cmd = user32.TrackPopupMenu(menu, 0x100 | 0x80, pt.x, pt.y, 0, hwnd, None)
                    user32.DestroyMenu(menu)
                    if cmd:
                        self.hk.put({1: 2, 2: 10, 3: 3}[cmd])
                return 0
            return user32.DefWindowProcW(hwnd, msg, wp, lp)

        self._tray_proc = WNDPROC(proc)
        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._tray_proc, hInstance=hinst, lpszClassName="DesktopSnowTray")
        user32.RegisterClassW(ctypes.byref(wc))
        hwnd = user32.CreateWindowExW(0, "DesktopSnowTray", "Desktop Snow tray", 0, 0, 0, 0, 0, None, None, hinst, None)
        ico = os.path.join(HERE, "snow.ico")
        if not os.path.exists(ico):
            make_icon(ico)
        hicon = user32.LoadImageW(None, ico, 1, 0, 0, 0x10 | 0x40)   # IMAGE_ICON, LR_LOADFROMFILE|LR_DEFAULTSIZE
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd, nid.uID, nid.uFlags = hwnd, 1, 0x1 | 0x2 | 0x4    # message | icon | tip
        nid.uCallbackMessage, nid.hIcon = WM_TRAY, hicon
        nid.szTip = "Desktop Snow — tıkla: panel, sağ tık: menü"
        shell32.Shell_NotifyIconW(0, ctypes.byref(nid))                # NIM_ADD
        self._nid, self._shell32 = nid, shell32
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def remove_tray(self):
        if getattr(self, "_nid", None) is not None:
            self._shell32.Shell_NotifyIconW(2, ctypes.byref(self._nid))   # NIM_DELETE
            self._nid = None

    # ================================================================ hotkeys
    def hotkeys(self):
        MOD = 0x0001 | 0x0002 | 0x4000
        for i, k in ((1, "E"), (2, "S"), (3, "Q")):
            user32.RegisterHotKey(None, i, MOD, ord(k))
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:
                self.hk.put(msg.wParam)

    def handle_hotkeys(self):
        while not self.hk.empty():
            k = self.hk.get()
            if k == 1:
                self.set_effect(ORDER[(ORDER.index(self.effect) + 1) % len(ORDER)])
                self.save_soon()
            elif k == 2:
                self.panel.deiconify()
                self.panel.lift()
            elif k == 3:
                self.quit()
            elif k == 10:
                self.paused = not self.paused
                self.pause_var.set(self.paused)

    def quit(self):
        if not self.running:
            return
        self.running = False
        self.remove_tray()
        try:
            if self.panel.state() == "normal":
                self.cfg["panel_pos"] = [self.panel.winfo_x(), self.panel.winfo_y()]
        except Exception:
            pass
        self.save()
        if self.wall_current is not None and self.cfg.get("original_wallpaper"):
            wallpaper.set_wallpaper(self.cfg["original_wallpaper"])

    # ================================================================ main loop
    def run(self):
        self.refresh_windows()
        last_wall = time.time()
        nxt = time.perf_counter()
        while self.running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit()
            self.handle_hotkeys()
            self.t += S
            self.frame += 1
            if self.frame % max(1, FPS // 60) == 0:
                self.refresh_windows()
            if time.time() - last_wall > 60:
                last_wall = time.time()
                self.apply_wallpaper()
            self.step_timers()
            if not self.paused:
                self.step_flakes()
            self.step_bits()
            self.step_decor()
            self.step_melt()
            self.step_mouse()
            self.step_actors()
            self.step_pets()
            self.render()
            try:
                self.tk.update()
            except tk.TclError:
                self.quit()
            nxt += 1.0 / FPS
            gap = nxt - time.perf_counter()
            if gap > 0.0015:
                time.sleep(gap - 0.0012)
            while time.perf_counter() < nxt:
                pass
            if time.perf_counter() - nxt > 0.05:
                nxt = time.perf_counter()
        try:
            self.tk.destroy()
        except Exception:
            pass
        pygame.quit()


def single_instance(wait):
    """Only one Desktop Snow at a time (named mutex). A restart waits for the old one to exit."""
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = wt.HANDLE
    for _ in range(50 if wait else 1):
        h = k32.CreateMutexW(None, False, r"Local\DesktopSnow.SingleInstance")
        if k32.GetLastError() != 183:            # ERROR_ALREADY_EXISTS
            return h
        k32.CloseHandle(h)
        time.sleep(0.2)
    return None


if __name__ == "__main__":
    _mutex = single_instance("--restart" in sys.argv)
    if _mutex is None:
        ctypes.windll.user32.MessageBoxW(None, "Desktop Snow zaten çalışıyor.\n\nPaneli açmak için sağ alttaki kar tanesi "
                                         "simgesine tıkla ya da Ctrl+Alt+S'ye bas.", "Desktop Snow", 0x40 | 0x40000)
        sys.exit(0)
    sys.argv = [a for a in sys.argv if a != "--restart"]
    eff = sys.argv[1].lower() if len(sys.argv) > 1 and sys.argv[1].lower() in EFFECTS else None
    App(eff).run()
