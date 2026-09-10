#!/usr/bin/env python3
import json, os, sys, urllib.request
from datetime import datetime
from PIL import Image, ImageDraw

HERE = os.path.dirname(__file__)
OUT = os.path.join(os.path.dirname(HERE), "..", "assets", "scarf.gif")

def load(user, labels):
    days = []
    for y in labels:
        url = f"https://github-contributions-api.jogruber.de/v4/{user}?y={y}"
        with urllib.request.urlopen(url, timeout=30) as r:
            days += json.load(r)["contributions"]
    days.sort(key=lambda c: c["date"])
    return days

def build_grid(days):
    if not days:
        return [[0] * 53 for _ in range(7)], 53
    d0 = datetime.strptime(days[0]["date"], "%Y-%m-%d").date()
    weeks = min(53, (datetime.strptime(days[-1]["date"], "%Y-%m-%d").date() - d0).days // 7 + 1)
    grid = [[0] * weeks for _ in range(7)]
    mx = max(max(c["count"] for c in days), 1)
    for c in days:
        d = datetime.strptime(c["date"], "%Y-%m-%d").date()
        w = (d - d0).days // 7
        if 0 <= w < weeks:
            grid[d.weekday()][w] = min(4, 1 + c["count"] * 4 // mx) if c["count"] else 0
    return grid, weeks

def draw_stitch(dr, x, y, s, color, dotted=False):
    lw = max(2, s // 3)
    top, bot, mid = y, y + s, x + s / 2
    if dotted:
        dr.rectangle([x + 1, y + 1, x + s - 1, y + s - 1], fill=color)
    else:
        dr.line([(x, top), (mid, bot)], fill=color, width=lw)
        dr.line([(x + s, top), (mid, bot)], fill=color, width=lw)

def draw_ball(img, dr, cx, cy, r, base, dark, light):
    import math
    size = int(r * 2) + 10
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    c = size / 2
    # soft shadowed body
    ld.ellipse([4, 6, size - 4, size - 2], fill=dark + (90,))
    ld.ellipse([4, 3, size - 4, size - 4], fill=base + (255,))
    lw = max(2, int(r / 10))
    n = max(4, int(r / 6))
    # meridian wraps: vertical ellipse arcs across the ball
    for k in range(-n, n + 1):
        f = k / (n + 0.5)
        rx = r * math.cos(math.asin(max(-0.98, min(0.98, f)))) * 0.98
        x0 = c - rx
        x1 = c + rx
        yy = 4 + (f + 1) / 2 * (size - 8)
        col = dark if (k + n) % 2 else light
        ld.arc([x0, yy - r * 0.32, x1, yy + r * 0.32], 0, 360, fill=col + (255,), width=lw)
    # latitude wraps: horizontal ellipse arcs
    for k in range(-n // 2, n // 2 + 1):
        f = k / max(1.0, n / 2 + 0.5)
        ry = r * math.cos(math.asin(max(-0.98, min(0.98, f)))) * 0.98
        y0 = c - ry
        y1 = c + ry
        xx = 4 + (f + 1) / 2 * (size - 8)
        col = light if (k + n) % 2 else dark
        ld.arc([xx - r * 0.32, y0, xx + r * 0.32, y1], 0, 360, fill=col + (255,), width=lw)
    # a few diagonal strands for depth
    for k in range(-n // 3, n // 3 + 1):
        off = k * (r / max(1.0, n / 3 + 0.5))
        ld.arc([c - r * 0.95 + off * 0.4, c - r * 0.5 + off, c + r * 0.95 + off * 0.4, c + r * 0.5 + off],
               25, 155, fill=dark + (180,), width=lw)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([4, 3, size - 4, size - 4], fill=255)
    img.paste(layer, (int(cx - c), int(cy - c)), mask)
    # crisp outline + tiny highlight
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=dark, width=2)
    hl = r * 0.45
    dr.arc([cx - r * 0.72, cy - r * 0.72, cx - r * 0.72 + hl, cy - r * 0.72 + hl], 140, 230, fill=light, width=lw)

def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "carrol74"
    labels = sys.argv[2:] or ["last"]
    grid, weeks = build_grid(load(user, labels))

    PITCH, CELL, MARGIN = 15, 12, 16
    panel_w, panel_h = weeks * PITCH, 7 * PITCH
    ball_r0 = 40
    W = MARGIN * 2 + panel_w + ball_r0 + 40
    H = MARGIN * 2 + panel_h
    ox, oy = MARGIN, MARGIN

    bg = (240, 247, 253)
    unstitched = (209, 227, 242)
    level_colors = {
        0: (232, 241, 250),
        1: (157, 195, 240),
        2: (91, 155, 213),
        3: (46, 109, 180),
        4: (26, 76, 139),
    }
    yarn, dark, light = (46, 109, 180), (26, 76, 139), (157, 195, 240)
    base_yarn, base_dark, base_light = (209, 227, 242), (160, 190, 220), (236, 245, 252)
    nd, nl = (108, 130, 160), (168, 188, 210)

    # snake/z-order path: down column 0, up column 1, down column 2, ...
    path = []
    for w in range(weeks):
        col = [(w, d) for d in range(7)]
        if w % 2:
            col.reverse()
        path += col
    total = len(path)

    def cell_center(w, d):
        return (ox + w * PITCH + CELL / 2, oy + d * PITCH + CELL / 2)

    total_steps = weeks * 2
    frames = []
    for step in range(total_steps):
        img = Image.new("RGB", (W, H), bg)
        dr = ImageDraw.Draw(img)
        done = min(total, int((step + 1) * total / total_steps + 0.5))
        done_set = set(path[:done])
        frac = done / total
        for (w, d) in path[:done]:
            x, y = ox + w * PITCH, oy + d * PITCH
            draw_stitch(dr, x, y, CELL, level_colors[grid[d][w]])
        for (w, d) in path[done:]:
            x, y = ox + w * PITCH, oy + d * PITCH
            draw_stitch(dr, x, y, CELL, unstitched, dotted=True)
        # two knitting needles held needle-tip-up, one per yarn color
        import math
        hw, hd = path[done - 1]
        hx, hy = cell_center(hw, hd)
        ang = math.radians(65)  # from vertical; swings as you knit
        ang += math.sin(done * 0.7) * 0.12
        L = 34
        def needle(x0, y0, a):
            tx, ty = x0 + L * math.sin(a), y0 - L * math.cos(a)
            dr.line([(x0, y0), (tx, ty)], fill=nd, width=4)
            dr.line([(x0 - 1, y0 + 1), (tx + 1, ty - 1)], fill=nl, width=2)
            return (tx, ty)
        needle(hx - 4, hy + 6, ang - 0.22)
        needle(hx + 4, hy + 6, ang + 0.22)
        dr.ellipse([hx - 3, hy - 3, hx + 3, hy + 3], fill=yarn)
        # yarn tails: base yarn and blue yarn, each from its ball to the needles
        bx = W - MARGIN - 30
        by = H - MARGIN - 34
        b2x = W - MARGIN - 30
        b2y = MARGIN + 30
        def tail(sx, sy, ex, ey, color):
            pts = [(sx, sy)]
            for t in range(1, 12):
                f = t / 12
                fx = sx + (ex - sx) * f
                fy = sy + (ey - sy) * f + 5 * (1 if t % 2 else -1) * (1 - f)
                pts.append((fx, fy))
            pts.append((ex, ey))
            dr.line(pts, fill=color, width=3, joint="curve")
        tail(bx, by, hx - 4, hy + 8, yarn)
        tail(b2x, b2y, hx + 4, hy + 8, base_yarn)
        r = ball_r0 * (1 - 0.6 * frac)
        draw_ball(img, dr, bx, by, max(r, 16), yarn, dark, light)
        draw_ball(img, dr, b2x, b2y, max(r * 0.92, 14), base_yarn, base_dark, base_light)
        frames.append(img)
    out = os.path.abspath(OUT)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=80, loop=0)
    print("wrote", out, os.path.getsize(out), "bytes,", len(frames), "frames")

if __name__ == "__main__":
    main()
