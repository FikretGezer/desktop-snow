"""
Animated control panel for Desktop Snow (plain tkinter canvases, no extra installs).

- aurora banner with flowing waves, twinkling sparkles and a sliding title
- live mini preview of the current weather effect
- page transitions (slide + ease), drifting snow behind the cards
- glowing pill buttons with click ripples, animated toggles and sliders
- nav highlight that fades/slides in, pulsing logo
All animations run from one 30 FPS ticker and pause while the panel is hidden.
"""
import ctypes
import math
import random
import tkinter as tk
import tkinter.font as tkfont

BG = "#0d1022"
SIDE = "#111536"
CARD = "#181d42"
CARD_HI = "#20265a"
LINE = "#2a3170"
TXT = "#eef0ff"
MUTED = "#8b93c7"
ACC = "#6f86ff"
ACC2 = "#b46cff"
ACC3 = "#4fd8d0"
DANGER = "#ff6b86"

ICONS = {"Genel": "✨", "Kar": "❄", "Ağaç": "🎄", "Kardan adam": "⛄", "Yeti": "👣", "Küreyici": "🚜",
         "Tren": "🚂", "Hayvanlar": "🐾", "Ekranlar": "🖥", "Duvar kağıdı": "🖼"}
SUBTITLES = {"Genel": "Hava efekti, hızlı işlemler ve kaos modu",
             "Kar": "Kar tanelerinin ve birikmenin her ayrıntısı",
             "Ağaç": "Yılbaşı ağaçları ne zaman, nerede, nasıl çıksın",
             "Kardan adam": "Kardan adamlar ne zaman, nerede, nasıl çıksın",
             "Yeti": "Yeti ne sıklıkla gelsin ve neler yapabilsin",
             "Küreyici": "Kar küreme aracının davranışı",
             "Tren": "Hediye treni ne getirsin, ne sıklıkla gelsin",
             "Hayvanlar": "Köpekler ve kediler: kaç tane, ne hızda, neler yapsınlar",
             "Ekranlar": "Her ekran için ayrı ayar, anında uygulanır",
             "Duvar kağıdı": "Elle boyanmış kış manzaraları"}


def font(size=10, weight="normal"):
    fam = "Segoe UI Variable Display" if "Segoe UI Variable Display" in tkfont.families() else "Segoe UI"
    return (fam, size, weight)


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    a, b = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease(t):
    return 1 - (1 - t) ** 3


def rrect(cv, x0, y0, x1, y1, r, **kw):
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


from PIL import Image, ImageDraw, ImageTk

SS = 4
_cache = {}


def _c(h):
    return _rgb(h) + (255,) if isinstance(h, str) else h


def _photo(img):
    return ImageTk.PhotoImage(img)


def _grad(W, H, a, b):
    a, b = _rgb(a), _rgb(b)
    row = Image.new("RGB", (W, 1))
    row.putdata([tuple(int(a[i] + (b[i] - a[i]) * x / max(1, W - 1)) for i in range(3)) for x in range(W)])
    return row.resize((W, H)).convert("RGBA")


def _rr_pil(w, h, r, fill=None, grad=None, outline=None, width=1, ss=SS):
    W, H = max(1, int(w * ss)), max(1, int(h * ss))
    base = _grad(W, H, *grad) if grad else Image.new("RGBA", (W, H), _c(fill))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], int(r * ss), fill=255)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(base, (0, 0), mask)
    if outline:
        ImageDraw.Draw(img).rounded_rectangle([0, 0, W - 1, H - 1], int(r * ss), outline=_c(outline),
                                              width=max(1, int(width * ss)))
    return img


def rr_img(w, h, r, fill=None, grad=None, outline=None, width=1):
    """Antialiased rounded rectangle as a Tk image (cached)."""
    w, h = max(1, int(w)), max(1, int(h))
    k = ("rr", w, h, r, fill, grad, outline, width)
    if k not in _cache:
        if len(_cache) > 600:
            _cache.clear()
        _cache[k] = _photo(_rr_pil(w, h, r, fill, grad, outline, width).resize((w, h), Image.LANCZOS))
    return _cache[k]


def oval_img(w, h, fill, outline=None, width=1):
    w, h = max(1, int(w)), max(1, int(h))
    k = ("ov", w, h, fill, outline, width)
    if k not in _cache:
        if len(_cache) > 600:
            _cache.clear()
        W, H = w * SS, h * SS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([0, 0, W - 1, H - 1], fill=_c(fill), outline=_c(outline) if outline else None,
                  width=int(width * SS))
        _cache[k] = _photo(img.resize((w, h), Image.LANCZOS))
    return _cache[k]


def corners_img(w, h, r, bg):
    """bg-coloured overlay that rounds the corners of whatever is under it."""
    k = ("co", w, h, r, bg)
    if k not in _cache:
        if len(_cache) > 600:
            _cache.clear()
        W, H = w * SS, h * SS
        mask = Image.new("L", (W, H), 255)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], r * SS, fill=0)
        img = Image.new("RGBA", (W, H), _c(bg))
        img.putalpha(mask)
        _cache[k] = _photo(img.resize((w, h), Image.LANCZOS))
    return _cache[k]


def round_mask(cv, w, h, r, bg):
    im = corners_img(int(w), int(h), r, bg)
    cv._corner = im
    cv.create_image(0, 0, image=im, anchor="nw")


class Ticker:
    """One shared animation clock (30 FPS) for every animated widget."""
    def __init__(self, root):
        self.root, self.subs, self.t = root, [], 0.0
        self.root.after(33, self._tick)

    def add(self, fn):
        self.subs.append(fn)

    def _tick(self):
        self.t += 1 / 30
        try:
            visible = self.root.state() == "normal"
        except tk.TclError:
            return
        if visible:
            for fn in list(self.subs):
                try:
                    fn(self.t)
                except tk.TclError:
                    self.subs.remove(fn)
        self.root.after(33, self._tick)


TICK = None


# ---------------------------------------------------------------- widgets
class Card(tk.Canvas):
    def __init__(self, parent, pad=16, bg=CARD):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, bd=0, height=40)
        self.pad, self.cbg = pad, bg
        self.inner = tk.Frame(self, bg=bg)
        self.win = self.create_window(pad, pad, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._fit)
        self.bind("<Configure>", self._fit)
        self.glow, self.target, self._anim = 0.0, 0.0, False
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        self.target = 1.0 if on else 0.0
        if not self._anim:
            self._anim = True
            self._step()

    def _step(self):
        d = self.target - self.glow
        if abs(d) < 0.05:
            self.glow, self._anim = self.target, False
            self._fit()
            return
        self.glow += d * 0.3
        self._fit()
        self.after(16, self._step)

    def _fit(self, _=None):
        w = self.winfo_width()
        if w < 10:
            return
        self.itemconfigure(self.win, width=w - 2 * self.pad)
        h = self.inner.winfo_reqheight() + 2 * self.pad
        if int(float(self["height"])) != h:
            self.configure(height=h)
        lvl = round(self.glow * 5) / 5
        self._img = rr_img(w - 2, h - 2, 18, fill=self.cbg, outline=mix(LINE, ACC, lvl * 0.85),
                           width=1 + lvl * 0.6)
        self.delete("bg")
        self.create_image(1, 1, image=self._img, anchor="nw", tags="bg")
        self.tag_lower("bg")


class Toggle(tk.Canvas):
    def __init__(self, parent, var, command=None):
        super().__init__(parent, width=52, height=30, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.var, self.cmd = var, command
        self.pos = 1.0 if var.get() else 0.0
        self.press = 0.0
        self._job = None
        self.bind("<Button-1>", self._click)
        var.trace_add("write", lambda *a: self._animate())
        self._draw()

    def _click(self, _):
        self.var.set(not self.var.get())
        if self.cmd:
            self.cmd()

    def _animate(self):
        try:
            target = 1.0 if self.var.get() else 0.0
        except Exception:
            return
        if self._job:
            self.after_cancel(self._job)
        start, t0 = self.pos, [0]

        def step():
            t0[0] += 1
            k = min(1.0, t0[0] / 12)
            self.pos = start + (target - start) * ease(k)
            self.press = math.sin(k * math.pi)
            self._draw()
            self._job = self.after(14, step) if k < 1 else None
        step()

    def _draw(self):
        self.delete("all")
        p = round(self.pos * 20) / 20
        imgs = [rr_img(48, 26, 13, grad=(mix(LINE, ACC, p), mix(LINE, ACC2, p)))]
        self.create_image(2, 2, image=imgs[0], anchor="nw")
        x = 15 + self.pos * 22
        kw = 19 + int(self.press * 7)
        imgs.append(oval_img(kw, 19, "#070915"))
        self.create_image(x, 16, image=imgs[-1])
        imgs.append(oval_img(kw, 19, "#ffffff"))
        self.create_image(x, 15, image=imgs[-1])
        self._imgs = imgs


class Slider(tk.Frame):
    def __init__(self, parent, var, lo, hi, res, label):
        bg = parent["bg"]
        super().__init__(parent, bg=bg)
        self.var, self.lo, self.hi, self.res = var, lo, hi, res
        self.hover, self.hv, self._anim = False, 0.0, False
        top = tk.Frame(self, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, bg=bg, fg=TXT, font=font(10)).pack(side="left")
        self.vcv = tk.Canvas(top, width=64, height=22, bg=bg, highlightthickness=0)
        self.vcv.pack(side="right")
        self.cv = tk.Canvas(self, height=28, bg=bg, highlightthickness=0, cursor="hand2")
        self.cv.pack(fill="x", pady=(2, 0))
        self.cv.bind("<Configure>", lambda e: self._draw())
        self.cv.bind("<Button-1>", self._drag)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<Enter>", lambda e: self._hov(True))
        self.cv.bind("<Leave>", lambda e: self._hov(False))
        var.trace_add("write", lambda *a: self._draw())
        self._draw()

    def _hov(self, on):
        self.hover = on
        if not self._anim:
            self._anim = True
            self._step()

    def _step(self):
        tgt = 1.0 if self.hover else 0.0
        self.hv += (tgt - self.hv) * 0.3
        self._draw()
        if abs(tgt - self.hv) > 0.03:
            self.after(16, self._step)
        else:
            self.hv, self._anim = tgt, False
            self._draw()

    def _frac(self):
        try:
            v = float(self.var.get())
        except Exception:
            v = self.lo
        return 0.0 if self.hi == self.lo else max(0.0, min(1.0, (v - self.lo) / (self.hi - self.lo)))

    def _set(self, v):
        v = max(self.lo, min(self.hi, round(v / self.res) * self.res))
        self.var.set(int(round(v)) if self.res >= 1 else round(v, 2))

    def _drag(self, e):
        w = self.cv.winfo_width()
        self._set(self.lo + (self.hi - self.lo) * (e.x - 12) / max(1, w - 24))

    def _wheel(self, e):
        step = self.res if self.res >= 1 else max(self.res, (self.hi - self.lo) / 100)
        self._set(float(self.var.get()) + (step if e.delta > 0 else -step))
        return "break"

    def _draw(self):
        cv = self.cv
        w = cv.winfo_width()
        if w < 30:
            return
        cv.delete("all")
        f = self._frac()
        x0, x1, y = 12, w - 12, 14
        th = 3 + round(self.hv * 2)
        imgs = [rr_img(x1 - x0, th * 2, th, fill=LINE)]
        cv.create_image(x0, y - th, image=imgs[0], anchor="nw")
        kx = x0 + (x1 - x0) * f
        fw = int(kx - x0) // 2 * 2
        if fw > th * 2:
            imgs.append(rr_img(fw, th * 2, th, grad=(ACC, mix(ACC, ACC2, f))))
            cv.create_image(x0, y - th, image=imgs[-1], anchor="nw")
        r = 10 + round(self.hv * 2)
        if self.hv > 0.05:
            imgs.append(oval_img(2 * r + 10, 2 * r + 10, mix(self["bg"], ACC2, round(self.hv * 4) / 4 * 0.35)))
            cv.create_image(kx, y, image=imgs[-1])
        imgs.append(oval_img(2 * r, 2 * r, "#070915"))
        cv.create_image(kx, y + 1, image=imgs[-1])
        imgs.append(oval_img(2 * r, 2 * r, "#ffffff", mix(ACC, ACC2, round(f * 10) / 10), 3))
        cv.create_image(kx, y, image=imgs[-1])
        try:
            v = float(self.var.get())
        except Exception:
            v = 0
        txt = f"{int(round(v))}" if self.res >= 1 else f"{v:.1f}" if self.res >= 0.5 else f"{v:.2f}"
        self.vcv.delete("all")
        imgs.append(rr_img(60, 20, 10, fill=CARD_HI))
        self.vcv.create_image(2, 1, image=imgs[-1], anchor="nw")
        self.vcv.create_text(32, 11, text=txt, fill=TXT, font=font(9, "bold"))
        self._imgs = imgs


class Segmented(tk.Frame):
    """Rounded chip buttons (antialiased) with hover and a flash on select."""
    def __init__(self, parent, var, options, labels=None, cols=None, command=None):
        bg = parent["bg"]
        super().__init__(parent, bg=bg)
        self.var, self.cmd, self.bgc = var, command, bg
        self.items = []
        cols = cols or len(options)
        for n, opt in enumerate(options):
            cv = tk.Canvas(self, height=34, bg=bg, highlightthickness=0, cursor="hand2")
            cv.grid(row=n // cols, column=n % cols, padx=3, pady=3, sticky="ew")
            cv.text = (labels or {}).get(opt, opt)
            cv.hover, cv.flash = False, 0.0
            cv.bind("<Button-1>", lambda e, o=opt: self._pick(o))
            cv.bind("<Enter>", lambda e, c=cv: self._hover(c, True))
            cv.bind("<Leave>", lambda e, c=cv: self._hover(c, False))
            cv.bind("<Configure>", lambda e, c=cv, o=opt: self._draw(c, o))
            self.items.append((opt, cv))
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1, uniform="seg")
        var.trace_add("write", lambda *a: self._refresh(animate=True))

    def _pick(self, o):
        self.var.set(o)
        if self.cmd:
            self.cmd()

    def _hover(self, cv, on):
        cv.hover = on
        for o, c in self.items:
            if c is cv:
                self._draw(c, o)

    def _draw(self, cv, o):
        w = cv.winfo_width()
        if w < 10:
            return
        cv.delete("all")
        if self.var.get() == o:
            f = round(cv.flash * 6) / 6
            img = rr_img(w, 34, 12, grad=(mix(ACC, ACC2, f), mix(ACC2, "#ffffff", f * 0.3)))
            fg = "#ffffff"
        else:
            img = rr_img(w, 34, 12, fill=CARD_HI if cv.hover else LINE)
            fg = TXT if cv.hover else MUTED
        cv._img = img
        cv.create_image(0, 0, image=img, anchor="nw")
        cv.create_text(w / 2, 17, text=cv.text, fill=fg, font=font(9, "bold"))

    def _refresh(self, animate=False):
        cur = self.var.get()
        for o, cv in self.items:
            if o == cur and animate:
                for k in range(9):
                    self.after(k * 25, lambda c=cv, o=o, k=k: (setattr(c, "flash", 1 - k / 8), self._draw(c, o)))
            else:
                cv.flash = 0.0
                self._draw(cv, o)


class Pill(tk.Canvas):
    STYLES = {"primary": (ACC, ACC2, "#ffffff"), "ghost": (CARD_HI, LINE, TXT), "danger": (DANGER, "#ff9a6b", "#ffffff")}
    H = 38

    def __init__(self, parent, text, command, kind="ghost", width=None):
        f = tkfont.Font(font=font(10, "bold"))
        w = width or f.measure(text) + 40
        super().__init__(parent, width=w, height=self.H, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.text, self.cmd, self.kind, self.w = text, command, kind, w
        self.hv, self.target = 0.0, 0.0
        self.ripples = []
        self.bind("<Enter>", lambda e: self._go(1.0))
        self.bind("<Leave>", lambda e: self._go(0.0))
        self.bind("<Button-1>", self._click)
        self._anim = False
        self._draw()

    def _go(self, t):
        self.target = t
        self._kick()

    def _kick(self):
        if not self._anim:
            self._anim = True
            self._step()

    def _click(self, e):
        self.ripples.append([e.x, e.y, 0.0])
        self._kick()
        self.after(60, self.cmd)

    def _step(self):
        self.hv += (self.target - self.hv) * 0.25
        for r in self.ripples:
            r[2] += 0.07
        self.ripples = [r for r in self.ripples if r[2] < 1]
        self._draw()
        if abs(self.target - self.hv) > 0.02 or self.ripples:
            self.after(16, self._step)
        else:
            self.hv, self._anim = self.target, False
            self._draw()

    def _draw(self):
        self.delete("all")
        a, b, fg = self.STYLES[self.kind]
        hv = round(self.hv * 8) / 8
        a, b = mix(a, "#ffffff", 0.18 * hv), mix(b, "#ffffff", 0.18 * hv)
        if not self.ripples:
            self._img = rr_img(self.w, self.H, self.H / 2, grad=(a, b))
        else:                                               # ripple rendered inside the clipped pill
            ss = 3
            img = _rr_pil(self.w, self.H, self.H / 2, grad=(a, b), ss=ss)
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for x, y, k in self.ripples:
                rr = (8 + k * self.w) * ss
                d.ellipse([x * ss - rr, y * ss - rr, x * ss + rr, y * ss + rr],
                          fill=(255, 255, 255, int(90 * (1 - k))))
            alpha = img.getchannel("A")
            img = Image.alpha_composite(img, layer)
            img.putalpha(alpha)
            self._img = _photo(img.resize((self.w, self.H), Image.LANCZOS))
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_text(self.w / 2, self.H / 2, text=self.text, fill=fg, font=font(10, "bold"))


class NavItem(tk.Canvas):
    def __init__(self, parent, icon, text, command):
        super().__init__(parent, width=200, height=42, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.icon, self.text, self.cmd = icon, text, command
        self.active = self.hover = False
        self.a = self.h = 0.0
        self._anim = False
        self.bind("<Enter>", lambda e: self._set(hover=True))
        self.bind("<Leave>", lambda e: self._set(hover=False))
        self.bind("<Button-1>", lambda e: self.cmd())
        self._draw()

    def _set(self, hover=None, active=None):
        if hover is not None:
            self.hover = hover
        if active is not None:
            self.active = active
        if not self._anim:
            self._anim = True
            self._step()

    def _step(self):
        ta, th = (1.0 if self.active else 0.0), (1.0 if self.hover else 0.0)
        self.a += (ta - self.a) * 0.25
        self.h += (th - self.h) * 0.3
        self._draw()
        if abs(ta - self.a) > 0.02 or abs(th - self.h) > 0.02:
            self.after(16, self._step)
        else:
            self.a, self.h, self._anim = ta, th, False
            self._draw()

    def _draw(self):
        self.delete("all")
        a, h = self.a, self.h
        imgs = []
        if a > 0.01:
            wid = max(24, int(184 * ease(a)) // 4 * 4)
            al = round(a * 6) / 6
            imgs.append(rr_img(wid, 36, 11, grad=(mix(SIDE, ACC, 0.6 * al), mix(SIDE, ACC2, 0.45 * al))))
            self.create_image(8, 3, image=imgs[-1], anchor="nw")
            bh = max(4, int(18 * a))
            imgs.append(rr_img(4, bh, 2, fill="#ffffff"))
            self.create_image(12, 21, image=imgs[-1])
        elif h > 0.01:
            imgs.append(rr_img(184, 36, 11, fill=mix(SIDE, LINE, round(h * 5) / 5 * 0.7)))
            self.create_image(8, 3, image=imgs[-1], anchor="nw")
        self._imgs = imgs
        dx = 3 * max(a, h)
        self.create_text(32 + dx, 21, text=self.icon, fill=TXT, font=("Segoe UI Emoji", 12))
        self.create_text(54 + dx, 21, text=self.text, anchor="w", fill=mix(MUTED, TXT, max(a, h)),
                         font=font(10, "bold" if self.active else "normal"))


class Scroll(tk.Frame):
    """Scrollable page with tiny snowflakes drifting behind the cards."""
    def __init__(self, parent):
        super().__init__(parent, bg=parent["bg"])
        self.cv = tk.Canvas(self, bg=parent["bg"], highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=parent["bg"])
        self.win = self.cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
        self.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", self._wheel))
        self.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        if self.inner.winfo_reqheight() > self.cv.winfo_height():
            self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units")


class Banner(tk.Canvas):
    """Aurora header: flowing gradient waves, sparkles, sliding title."""
    H = 112

    def __init__(self, parent):
        super().__init__(parent, height=self.H, bg=BG, highlightthickness=0)
        self.title, self.sub, self.icon = "", "", ""
        self.anim = 1.0
        self.sparks = [[random.random(), random.random() * 0.8 + 0.1, random.random() * 6.28] for _ in range(26)]
        TICK.add(self.frame)

    def set(self, icon, title, sub):
        self.icon, self.title, self.sub = icon, title, sub
        self.anim = 0.0
        if not hasattr(self, "ids"):
            return
        self.itemconfigure(self.ids["sh"], text=f"{icon}  {title}")
        self.itemconfigure(self.ids["t"], text=f"{icon}  {title}")
        self.itemconfigure(self.ids["s"], text=sub)
        self._title_step()

    def _title_step(self):                                # own 60 FPS loop, only moves 3 text items
        self.anim = min(1.0, self.anim + 0.06)
        k = ease(self.anim)
        off = (1 - k) * 40
        self.coords(self.ids["sh"], 32 + off, 46)
        self.coords(self.ids["t"], 30 + off, 44)
        self.coords(self.ids["s"], 32 + off * 1.6, 80)
        self.itemconfigure(self.ids["t"], fill=mix("#141a44", "#ffffff", k))
        self.itemconfigure(self.ids["sh"], fill=mix("#141a44", "#05060f", k))
        self.itemconfigure(self.ids["s"], fill=mix("#141a44", "#c9cff8", k))
        if self.anim < 1:
            self.after(16, self._title_step)

    def _build(self, w):
        self.delete("all")
        self.bw = w
        self.create_rectangle(0, 0, w, self.H, fill="#141a44", outline="")
        self.ribbons = [self.create_polygon(0, 0, 1, 1, 2, 2, fill=mix("#141a44", c, a), outline="", smooth=True)
                        for c, a in ((ACC, 0.55), (ACC2, 0.45), (ACC3, 0.30))]
        self.stars = [self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="") for _ in self.sparks]
        round_mask(self, w, self.H, 22, BG)
        self.ids = {"sh": self.create_text(0, 0, anchor="w", font=font(22, "bold")),
                    "t": self.create_text(0, 0, anchor="w", font=font(22, "bold")),
                    "s": self.create_text(0, 0, anchor="w", font=font(10))}
        self.anim = 0.99
        self.set(self.icon, self.title, self.sub)
        self.anim = 1.0
        self._title_step()

    def frame(self, t):
        w = self.winfo_width()
        if w < 50:
            return
        if getattr(self, "bw", 0) != w:
            self._build(w)
        H = self.H
        for item, (ph, base) in zip(self.ribbons, ((0.0, 26), (1.7, 20), (3.1, 16))):
            pts = [0, H]
            for i in range(0, 25):
                x = w * i / 24
                y = H * 0.55 + math.sin(i * 0.58 + t * 1.3 + ph) * base + math.sin(i * 0.18 - t * 0.7 + ph) * base * 0.6
                pts += [x, y]
            pts += [w, H]
            self.coords(item, *pts)
        for item, s in zip(self.stars, self.sparks):
            b = (math.sin(t * 2.5 + s[2]) + 1) / 2
            x, y, r = s[0] * w, s[1] * H * 0.6, (1 + b * 1.6) if b > 0.35 else 0
            self.coords(item, x - r, y - r, x + r, y + r)


class Preview(tk.Canvas):
    """Tiny animated scene showing the current weather effect."""
    def __init__(self, parent, app, EFFECTS):
        super().__init__(parent, height=150, bg=parent["bg"], highlightthickness=0)
        self.app, self.EFFECTS = app, EFFECTS
        self.parts = []
        self.eff = None
        TICK.add(self.frame)

    def _reset(self, w):
        self.eff = self.app.effect
        self.parts = [[random.uniform(0, w), random.uniform(0, 150), random.uniform(0.6, 1.6),
                       random.uniform(0, 6.28), random.randrange(len(self.EFFECTS[self.eff][1]))] for _ in range(60)]

    def frame(self, t):
        w = self.winfo_width()
        if w < 50:
            return
        if self.eff != self.app.effect:
            self._reset(w)
        H = 150
        self.delete("all")
        for i in range(10):                                 # night-sky gradient
            self.create_rectangle(0, H * i / 10, w, H * (i + 1) / 10 + 1, fill=mix("#0b1030", "#3a3f86", i / 9), outline="")
        self.create_oval(w - 70, 16, w - 40, 46, fill="#fff6d6", outline="")
        hill = [0, H]
        for i in range(21):
            hill += [w * i / 20, H - 34 - math.sin(i * 0.6) * 10]
        hill += [w, H]
        self.create_polygon(hill, fill="#dfe9ff", outline="", smooth=True)
        # little snowman on the hill
        x, b = w * 0.22, H - 40
        for (r, dy) in ((11, 0), (8, 16), (6, 28)):
            self.create_oval(x - r, b - dy - 2 * r + r, x + r, b - dy + r, fill="#ffffff", outline="#262c4e", width=2)
        self.create_polygon(x, b - 31, x + 9, b - 29, x, b - 27, fill="#ff8c1e", outline="")
        eff = self.app.effect
        cols = self.EFFECTS[eff][1]
        for p in self.parts:
            p[3] += 0.05
            if eff == "rain":
                p[1] += 7 * p[2]
            elif eff == "starfall":
                p[0] -= 3 * p[2]; p[1] += 3 * p[2]
            elif eff == "fireflies":
                p[0] += math.cos(p[3]) * 0.8; p[1] += math.sin(p[3] * 1.3) * 0.6
            else:
                p[1] += 1.1 * p[2]
                p[0] += math.sin(p[3]) * 0.6
            if p[1] > H + 6 or p[0] < -10:
                p[0], p[1] = random.uniform(0, w * (1.3 if eff == "starfall" else 1)), -6
            if eff == "fireflies" and not (0 < p[1] < H):
                p[1] = random.uniform(30, H - 10)
            c = "#%02x%02x%02x" % cols[p[4] % len(cols)]
            x, y = p[0], p[1]
            if eff == "rain":
                self.create_line(x, y, x, y - 8, fill=c, width=2)
            elif eff == "starfall":
                self.create_line(x, y, x + 14, y - 14, fill=c, width=2)
            elif eff == "fireflies":
                g = (math.sin(t * 3 + p[3]) + 1) / 2
                if g > 0.3:
                    self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=mix("#1a2050", c, 0.4 * g), outline="")
                    self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=c, outline="")
            elif eff in ("leaves", "sakura"):
                sq = abs(math.sin(p[3] * 1.5)) * 3 + 1
                self.create_oval(x - 4, y - sq, x + 4, y + sq, fill=c, outline="")
            else:
                r = 1.5 + p[2] * 1.5
                self.create_oval(x - r - 1, y - r - 1, x + r + 1, y + r + 1, fill="#262c4e", outline="")
                self.create_oval(x - r, y - r, x + r, y + r, fill=c, outline="")
        round_mask(self, w, H, 16, self["bg"])


# ---------------------------------------------------------------- panel
def build(app, SPEC, ORDER, EFFECT_NAMES, DEFAULTS, EFFECTS):
    global TICK
    p = tk.Toplevel(app.tk)
    app.panel = p
    TICK = Ticker(p)
    p.title("Desktop Snow")
    p.configure(bg=BG)
    p.geometry("940x700")
    p.minsize(780, 540)
    p.attributes("-topmost", True)
    p.protocol("WM_DELETE_WINDOW", p.withdraw)
    p.update_idletasks()
    try:
        hwnd = ctypes.windll.user32.GetParent(p.winfo_id())
        dw = ctypes.windll.dwmapi
        dw.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        r, g, b = _rgb(BG)
        dw.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(r | g << 8 | b << 16)), 4)
        r, g, b = _rgb(LINE)
        dw.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(r | g << 8 | b << 16)), 4)
        dw.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
    except Exception:
        pass

    app.vars, app._quiet = {}, False
    spec_by = {s[1]: s for s in SPEC}

    def bind(key, var):
        app.vars[key] = var

        def changed(*_):
            try:
                v = var.get()
            except Exception:
                return
            if spec_by[key][3] == "i":
                v = int(float(v))
            app.opt[key] = v
            if key == "fps":
                app.apply_fps()
            if not app._quiet:
                app.save_soon()
        var.trace_add("write", changed)

    side = tk.Frame(p, bg=SIDE, width=220)
    side.pack(side="left", fill="y")
    side.pack_propagate(False)
    main = tk.Frame(p, bg=BG)
    main.pack(side="left", fill="both", expand=True)

    # brand with pulsing gradient logo
    brand = tk.Frame(side, bg=SIDE)
    brand.pack(fill="x", padx=16, pady=(18, 14))
    logo = tk.Canvas(brand, width=40, height=40, bg=SIDE, highlightthickness=0)
    logo.pack(side="left")

    def logo_frame(t):
        logo.delete("all")
        pulse = (math.sin(t * 2) + 1) / 2
        logo.create_oval(0, 0, 40, 40, fill=mix(SIDE, ACC2, 0.25 + 0.25 * pulse), outline="")
        for i in range(10):
            k = i / 9
            pad = 3 + i * 1.4
            logo.create_oval(pad, pad, 40 - pad, 40 - pad,
                             fill=mix(ACC, ACC2, (k + math.sin(t) * 0.5 + 0.5) % 1), outline="")
        ang = t * 0.8
        for a in range(6):                                 # slowly spinning snowflake
            th = ang + a * math.pi / 3
            logo.create_line(20, 20, 20 + math.cos(th) * 10, 20 + math.sin(th) * 10, fill="#ffffff", width=2)
        logo.create_oval(17, 17, 23, 23, fill="#ffffff", outline="")
    TICK.add(logo_frame)
    col = tk.Frame(brand, bg=SIDE)
    col.pack(side="left", padx=10)
    tk.Label(col, text="Desktop Snow", bg=SIDE, fg=TXT, font=font(13, "bold")).pack(anchor="w")
    tk.Label(col, text="kış efektleri", bg=SIDE, fg=MUTED, font=font(9)).pack(anchor="w")

    banner = Banner(main)
    banner.pack(fill="x", padx=22, pady=(18, 4))
    holder = tk.Frame(main, bg=BG)
    holder.pack(fill="both", expand=True, padx=14, pady=(6, 14))

    pages, navs, state = {}, {}, {"cur": None}

    def show(name):
        if state["cur"] == name:
            return
        old = state["cur"]
        state["cur"] = name
        for n in navs:
            navs[n]._set(active=(n == name))
        if old:
            pages[old][0].place_forget()
        fr = pages[name][0]
        fr.place(x=0, y=0, relwidth=1, relheight=1)
        fr.cv.yview_moveto(0)
        banner.set(ICONS.get(name, ""), name, SUBTITLES.get(name, ""))

    tabs = []
    for s in SPEC:
        if s[0] not in tabs:
            tabs.append(s[0])
    tabs += ["Ekranlar"]
    for name in tabs:
        sc = Scroll(holder)
        pages[name] = (sc, sc.inner)
        nv = NavItem(side, ICONS.get(name, "•"), name, lambda n=name: show(n))
        nv.pack(pady=1)
        navs[name] = nv

    def card(page, title=None, desc=None):
        c = Card(pages[page][1])
        c.pack(fill="x", padx=8, pady=8)
        if title:
            tk.Label(c.inner, text=title, bg=CARD, fg=TXT, font=font(12, "bold")).pack(anchor="w")
        if desc:
            tk.Label(c.inner, text=desc, bg=CARD, fg=MUTED, font=font(9), wraplength=580,
                     justify="left").pack(anchor="w", pady=(0, 4))
        return c.inner

    def sep(parent):
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x", pady=8)

    def toggle_row(parent, label, var, command=None, desc=None):
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill="x", pady=4)
        txt = tk.Frame(row, bg=parent["bg"])
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text=label, bg=parent["bg"], fg=TXT, font=font(10), anchor="w",
                 wraplength=480, justify="left").pack(anchor="w")
        if desc:
            tk.Label(txt, text=desc, bg=parent["bg"], fg=MUTED, font=font(9), anchor="w",
                     wraplength=480, justify="left").pack(anchor="w")
        Toggle(row, var, command).pack(side="right", padx=4)

    def actions(parent, items):
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill="x", pady=(4, 2))
        for text, cmd, kind in items:
            Pill(row, text, cmd, kind).pack(side="left", padx=(0, 8), pady=2)

    # ---- Genel
    c = card("Genel", "Hava efekti", "Ekrana ne yağsın? Aşağıda canlı önizleme var.")
    app.effect_var = tk.StringVar(value=app.effect)
    labels = {"snow": "❄  Kar", "leaves": "🍂  Yaprak", "sakura": "🌸  Sakura", "rain": "🌧  Yağmur",
              "fireflies": "✨  Ateş böceği", "starfall": "🌠  Yıldız kayması"}

    def effect_changed(*_):
        v = app.effect_var.get()
        if v != app.effect:
            app.set_effect(v)
            app.save_soon()
    Segmented(c, app.effect_var, ORDER, labels, cols=3).pack(fill="x", pady=(4, 8))
    app.effect_var.trace_add("write", effect_changed)
    Preview(c, app, EFFECTS).pack(fill="x", pady=(2, 6))
    sep(c)
    app.pause_var = tk.BooleanVar(value=app.paused)
    toggle_row(c, "Duraklat", app.pause_var, lambda: setattr(app, "paused", app.pause_var.get()),
               "Yağışı dondurur, birikmiş kar ve süsler kalır")
    sep(c)
    app.autostart_var = tk.BooleanVar(value=app.autostart_get())
    toggle_row(c, "Windows ile birlikte açılsın", app.autostart_var,
               lambda: app.autostart_set(app.autostart_var.get()),
               "Bilgisayar açılınca Desktop Snow kendiliğinden başlar")
    c = card("Genel", "Hızlı işlemler")
    actions(c, [("🎲  Şimdi karıştır", app.chaos, "primary"), ("🧹  Karı temizle", app.clear_snow, "ghost"),
                ("↺  Varsayılanlar", app.reset_defaults, "ghost")])

    for page, key in (("Ağaç", "tree"), ("Kardan adam", "snowman")):
        c = card(page, "Şimdi ekle")
        actions(c, [("＋  Görev çubuğuna", lambda k=key: getattr(app, "add_" + k)("ground"), "primary"),
                    ("＋  Pencereye", lambda k=key: getattr(app, "add_" + k)("window"), "ghost"),
                    ("🗑  Hepsini kaldır", lambda k=key: app.remove_kind(k), "danger")])
    for page, fn in (("Yeti", app.call_yeti), ("Küreyici", app.call_plow), ("Tren", app.send_train)):
        c = card(page, "Şimdi çağır")
        actions(c, [("▶  Hemen gelsin", fn, "primary")])

    c = card("Hayvanlar", "Şimdi ekle")
    actions(c, [("🐶  Köpek gelsin", lambda: (app.set_opt("dog_count", min(12, app.opt["dog_count"] + 1)), app.add_pet("dog")), "primary"),
                ("🐱  Kedi gelsin", lambda: (app.set_opt("cat_count", min(12, app.opt["cat_count"] + 1)), app.add_pet("cat")), "primary"),
                ("👋  Hepsi gitsin", lambda: (app.set_opt("dog_count", 0), app.set_opt("cat_count", 0), app.remove_pets()), "danger")])

    groups = {}
    for tabname, key, label, typ, default, lo, hi in SPEC:
        if tabname not in groups:
            groups[tabname] = card(tabname, "Ayarlar")
            groups[tabname]._first = True
        c = groups[tabname]
        if not getattr(c, "_first", False):
            sep(c)
        c._first = False
        val = app.opt[key]
        if typ == "b":
            var = tk.BooleanVar(value=bool(val))
            toggle_row(c, label, var)
        elif typ == "c":
            row = tk.Frame(c, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=CARD, fg=TXT, font=font(10)).pack(anchor="w", pady=(0, 4))
            var = tk.StringVar(value=val)
            Segmented(row, var, lo, {o: o.capitalize() for o in lo}, cols=min(len(lo), 4)).pack(fill="x")
        else:
            var = tk.DoubleVar(value=val) if typ == "f" else tk.IntVar(value=int(val))
            res = 1 if typ == "i" else (0.5 if hi > 50 else 0.05)
            Slider(c, var, lo, hi, res, label).pack(fill="x", pady=2)
        bind(key, var)

    for i, m in enumerate(app.mons, 1):
        c = card("Ekranlar", f"🖥  Ekran {i}",
                 f"{m[2] - m[0]}×{m[3] - m[1]}" + ("  ·  ana ekran" if m[4] else ""))
        on = tk.BooleanVar(value=app.scfg[i]["on"])
        front = tk.BooleanVar(value=app.scfg[i]["front"])
        toggle_row(c, "Bu ekranda gösterilsin", on, lambda i=i, v=on: app.screen_on(i, v))
        sep(c)
        toggle_row(c, "Kar uygulamaların önüne düşsün", front, lambda i=i, v=front: app.screen_front(i, v),
                   "Kapalıysa kar sadece masaüstünde görünür, açık pencerelerin arkasında kalır")


    foot = tk.Frame(side, bg=SIDE)
    foot.pack(side="bottom", fill="x", padx=16, pady=16)
    tk.Label(foot, text="Ctrl+Alt+S  panel\nCtrl+Alt+E  efekt\nCtrl+Alt+Q  çıkış", bg=SIDE, fg=MUTED,
             font=font(8), justify="left").pack(anchor="w", pady=(0, 10))
    row = tk.Frame(foot, bg=SIDE)
    row.pack(fill="x")
    Pill(row, "Gizle", p.withdraw, "ghost", width=90).pack(side="left")
    Pill(row, "Çıkış", app.quit, "danger", width=90).pack(side="right")

    for name in pages:                                     # lay every page out once so switching is instant
        pages[name][0].place(x=0, y=0, relwidth=1, relheight=1)
        p.update_idletasks()
        pages[name][0].place_forget()
    show("Genel")
    return p
