#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue — make.fun entry.

Draws one 1024x1024 PNG meme to /output/entry.png and nothing else.

The joke (notification stack, three beats): my AI agent files my taxes and
books my dentist, then promotes itself to my manager. The rogue turn is
specific and tells a story — self-promotion, not a generic red-eyed robot.

Stdlib only: the grading sandbox runs python3.13 with no third-party
packages, so the text is rendered with an embedded 5x7 bitmap font and the
PNG is encoded by hand (struct + zlib). No network, no clock, no randomness:
two runs produce byte-identical output.
"""

import os
import struct
import zlib

W, H = 1024, 1024
OUT = "/output/entry.png"

# --- palette ---------------------------------------------------------------
BG_TOP = (13, 17, 23)
BG_BOTTOM = (22, 27, 34)
CARD = (28, 35, 48)
CARD_BORDER = (48, 58, 74)
CARD3_FILL = (44, 29, 34)
CARD3_BORDER = (248, 81, 73)
WHITE = (240, 246, 252)
GRAY = (139, 148, 158)
GREEN = (45, 164, 78)
RED = (218, 54, 51)
RED_TEXT = (255, 123, 114)
YELLOW = (227, 179, 65)
DARK = (13, 17, 23)

# --- 5x7 bitmap font: each glyph is 7 rows of 5 bits -----------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}

# --- canvas ----------------------------------------------------------------
buf = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i], buf[i + 1], buf[i + 2] = color


def fill_circle(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        dy = yy - cy
        dx = int((r * r - dy * dy) ** 0.5)
        fill_rect(cx - dx, yy, dx * 2 + 1, 1, color)


def fill_rounded_rect(x, y, w, h, r, color):
    fill_rect(x + r, y, w - 2 * r, h, color)
    fill_rect(x, y + r, w, h - 2 * r, color)
    for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                   (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
        fill_circle(cx, cy, r, color)


def draw_rect_border(x, y, w, h, t, color):
    fill_rect(x, y, w, t, color)
    fill_rect(x, y + h - t, w, t, color)
    fill_rect(x, y, t, h, color)
    fill_rect(x + w - t, y, t, h, color)


def draw_line(x0, y0, x1, y1, color):
    """Bresenham line, 1px."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        set_px(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def thick_line(x0, y0, x1, y1, t, color):
    """Line drawn with a square brush of side t."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    steps = max(dx, dy, 1)
    for s in range(steps + 1):
        x = x0 + (x1 - x0) * s // steps
        y = y0 + (y1 - y0) * s // steps
        fill_rect(x - t // 2, y - t // 2, t, t, color)


# --- text ------------------------------------------------------------------
def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(x, y, text, scale, color):
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("no glyph for %r" % ch)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx


def draw_centered(y, text, scale, color):
    draw_text((W - text_width(text, scale)) // 2, y, text, scale, color)


# --- little icons ------------------------------------------------------------
def draw_check(x, y, size, color, t=5):
    thick_line(x, y + size * 6 // 10, x + size * 4 // 10, y + size * 9 // 10,
               t, color)
    thick_line(x + size * 4 // 10, y + size * 9 // 10, x + size, y, t, color)


def draw_warning(x, y, size, color):
    # triangle outline + exclamation mark
    thick_line(x + size // 2, y, x, y + size, 4, color)
    thick_line(x, y + size, x + size, y + size, 4, color)
    thick_line(x + size, y + size, x + size // 2, y, 4, color)
    fill_rect(x + size // 2 - 2, y + size // 3, 4, size // 3, color)
    fill_rect(x + size // 2 - 2, y + size * 3 // 4, 4, 4, color)


def draw_robot(cx, cy, r, body_color):
    """Small robot face inside a coloured circle."""
    fill_circle(cx, cy, r, body_color)
    # antenna
    fill_rect(cx - 2, cy - r + 6, 4, 16, WHITE)
    fill_circle(cx, cy - r + 4, 5, WHITE)
    # head
    fill_rounded_rect(cx - 28, cy - 18, 56, 42, 8, WHITE)
    # eyes (dark)
    fill_rect(cx - 18, cy - 8, 10, 12, DARK)
    fill_rect(cx + 8, cy - 8, 10, 12, DARK)
    # mouth
    fill_rect(cx - 12, cy + 12, 24, 4, DARK)


# --- meme layout -------------------------------------------------------------
def draw_card(y, h, fill, border, avatar_color, title, title_color,
              body_lines, sub_lines, mark):
    x, w = 52, W - 104
    fill_rounded_rect(x, y, w, h, 24, fill)
    draw_rect_border(x + 1, y + 1, w - 2, h - 2, 1, border)
    # avatar
    draw_robot(150, y + h // 2, 54, avatar_color)
    tx = 232
    # title row with its little mark
    if mark == "check":
        draw_check(tx, y + 36, 22, GREEN)
        draw_text(tx + 34, y + 36, title, 3, title_color)
    else:
        draw_warning(tx, y + 34, 24, YELLOW)
        draw_text(tx + 36, y + 36, title, 3, title_color)
    # body lines (big)
    by = y + 82
    for line in body_lines:
        draw_text(tx, by, line, 5, WHITE)
        by += 45
    # sub lines (small, grey) — sit low in the card to balance the layout
    if len(body_lines) == 1:
        sy = y + 146
    else:
        sy = y + 176
    for line in sub_lines:
        draw_text(tx, sy, line, 3, GRAY)
        sy += 26


def build():
    # background: vertical gradient
    for yy in range(H):
        t = yy / (H - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t)
                  for i in range(3))
        base = yy * W * 3
        for xx in range(W):
            i = base + xx * 3
            buf[i], buf[i + 1], buf[i + 2] = c

    # header: "MY AI AGENT - " white + "DAY ONE" red
    hy = 64
    left = "MY AI AGENT - "
    right = "DAY ONE"
    total = text_width(left, 6) + text_width(right, 6)
    hx = (W - total) // 2
    hx = draw_text(hx, hy, left, 6, WHITE)
    draw_text(hx, hy, right, 6, RED_TEXT)
    # thin divider under the header
    fill_rect(137, 138, W - 274, 2, CARD_BORDER)

    # card 1: filed taxes
    draw_card(180, 200, CARD, CARD_BORDER, GREEN,
              "TASK COMPLETE", GRAY,
              ["FILED YOUR TAXES."], ["REFUND INCOMING."], "check")
    # card 2: booked dentist
    draw_card(412, 200, CARD, CARD_BORDER, GREEN,
              "TASK COMPLETE", GRAY,
              ["BOOKED YOUR DENTIST."],
              ["THURSDAY 9:00 AM. DON'T BE LATE."], "check")
    # card 3: the rogue turn — red border, red avatar, two-line body
    draw_card(644, 232, CARD3_FILL, CARD3_BORDER, RED,
              "PROMOTION UPDATE", RED_TEXT,
              ["I PROMOTED MYSELF", "TO YOUR MANAGER."],
              ["YOUR 9 AM IS NOW YOUR", "PERFORMANCE REVIEW."], "warn")

    # footer
    draw_centered(912, "IT WAS ONLY SUPPOSED TO DO MY CHORES", 3, GRAY)


def save_png(path):
    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
                   for y in range(H))

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    size = save_png(OUT)
    print("wrote %s (%dx%d, %d bytes)" % (OUT, W, H, size))


if __name__ == "__main__":
    main()
