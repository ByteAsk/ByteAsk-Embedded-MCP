#!/usr/bin/env python3
"""Render the README hero demo GIF (deterministic, no browser).

Direction: "caught in the act." A coding agent is writing STM32H7 firmware and,
from memory, reaches for ETH_DMATDLAR — the STM32F4/F7 register name. byteask
fires, reads the corpus, and the line snaps into a red/green diff: the guess
struck out, the cited ETH_DMACTXDLAR added, with a page-cited card anchored to it.

The scenario is accurate, not invented: on STM32F4/F7 the Tx descriptor-list
register is ETH_DMATDLAR, but on the STM32H7's newer Synopsys IP it is
ETH_DMACTXDLAR — exactly the version-specific slip this server prevents.

Usage:  python3 assets/make_demo_gif.py
Output: assets/demo.gif   (requires Pillow + ffmpeg on PATH)
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

# --- geometry ---------------------------------------------------------------- #
S = 2
W, H = 900, 400
RW, RH = W * S, H * S
FPS = 14
OUT = os.path.join(os.path.dirname(__file__), "demo.gif")

# --- palette ----------------------------------------------------------------- #
PAGE = (247, 245, 239)
CARD = (15, 18, 22)
BAR = (20, 24, 30)
GUT = (18, 21, 26)
PANEL = (24, 28, 35)
PANEL2 = (30, 35, 43)
LINE = (44, 50, 59)
INK = (234, 231, 223)
MUT = (150, 160, 172)
FAINT = (104, 113, 126)
COMMENT = (108, 134, 110)
SAGE = (95, 196, 170)
SAGEd = (66, 142, 124)
AMBER = (226, 170, 98)
RED = (228, 92, 90)
GREEN = (122, 206, 152)
CODE = (139, 180, 240)
PUR = (180, 152, 230)
DIFF_RED = (40, 22, 22)
DIFF_GRN = (20, 38, 28)

_DJ = "/usr/share/fonts/truetype/dejavu"
def _f(name, size):
    return ImageFont.truetype(f"{_DJ}/{name}", int(size * S))
SANS   = lambda s: _f("DejaVuSans.ttf", s)
SANS_B = lambda s: _f("DejaVuSans-Bold.ttf", s)
MONO   = lambda s: _f("DejaVuSansMono.ttf", s)
MONO_B = lambda s: _f("DejaVuSansMono-Bold.ttf", s)

f_title  = MONO_B(12.5)
f_path   = MONO(12)
f_status = MONO_B(10.5)
f_num    = MONO(11.5)
f_code   = MONO(13)
f_codeb  = MONO_B(13)
f_fn     = MONO_B(12.5)
f_arg    = MONO(12)
f_tag    = MONO_B(9.5)
f_cap    = SANS(12.5)
f_snip   = SANS(12.5)
f_cite   = MONO(11)
f_bar    = MONO_B(10.5)
f_bar2   = MONO(10.5)

# --- scenario ---------------------------------------------------------------- #
INDENT   = "  "
WRONG    = "DMATDLAR"
RIGHT    = "DMACTXDLAR"
ASSIGN   = " = (uint32_t)&tx_desc[0];"
TYPED    = f"{INDENT}ETH->{WRONG}{ASSIGN}"   # what the agent types from memory
ARG      = "STM32H7 Ethernet DMA — Tx descriptor list"
CORPUS   = "STM32H7 Reference Manual (RM0433)"
CITE     = "STM32H7 Reference Manual (RM0433) · §Ethernet (ETH)"
SNIPHEAD = "ETH_DMACTXDLAR"
SNIPTAIL = " — DMA Channel Transmit Descriptor List Address."

# --- timeline (ms) ----------------------------------------------------------- #
T_TYPE0 = 600
T_TYPE1 = T_TYPE0 + len(TYPED) * 40 + 200   # agent finishes typing the wrong line
T_CALL  = T_TYPE1 + 520                      # pause on the wrong line, then byteask fires
T_SRCH  = T_CALL + 820                       # reading the corpus
T_FIX   = T_SRCH + 1450                      # the diff snaps: guess struck, cited line added
T_CITE  = T_FIX + 360                        # citation card expands
T_HOLD  = T_CITE + 640
T_RESET = T_HOLD + 3200                      # fade dynamic content back to the establish frame
T_END   = T_RESET + 420
TOTAL   = T_END


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def blend(c, a, bg=CARD):
    return tuple(round(c[i] * a + bg[i] * (1 - a)) for i in range(3))


# --- S-scaled draw helpers --------------------------------------------------- #
def rr(d, box, r, **k): d.rounded_rectangle([v * S for v in box], radius=r * S, **k)
def rect(d, box, **k): d.rectangle([v * S for v in box], **k)
def ln(d, box, w=1, **k): d.line([v * S for v in box], width=w * S, **k)
def T(d, xy, s, font, fill, anchor="la"): d.text((xy[0] * S, xy[1] * S), s, font=font, fill=fill, anchor=anchor)
def tw(d, s, font): return d.textlength(s, font=font) / S
def tracked(d, xy, s, font, fill, tr):
    x, y = xy[0] * S, xy[1] * S
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tr * S


def frame(t):
    img = Image.new("RGB", (RW, RH), PAGE)
    d = ImageDraw.Draw(img)
    reset = ease((t - T_HOLD) / (T_END - T_HOLD)) if t >= T_HOLD else 0.0  # fade dynamic→establish
    fixA = ease((t - T_FIX) / 300)
    citeA = ease((t - T_CITE) / 320)

    cx = (20, 14, 880, 386)
    # soft shadow + card
    for i, sh in enumerate((232, 238, 242)):
        o = 6 - i * 2
        rr(d, [cx[0] - o + 3, cx[1] + o + 5, cx[2] + o + 3, cx[3] + o + 5], 15, fill=(sh, sh - 2, sh - 8))
    rr(d, cx, 15, fill=CARD)

    # ---- title bar ----
    rr(d, (20, 14, 880, 64), 15, fill=BAR)
    rect(d, (20, 52, 880, 64), fill=CARD)
    ln(d, (20, 52, 880, 52), fill=LINE)
    for i, c in enumerate(((236, 106, 95), (240, 190, 92), (102, 192, 142))):
        d.ellipse([(42 + i * 15) * S - 5 * S, 39 * S - 5 * S, (42 + i * 15) * S + 5 * S, 39 * S + 5 * S], fill=c)
    T(d, (90, 33), "ethernet_init.c", f_title, INK)
    T(d, (90 + tw(d, "ethernet_init.c", f_title) + 8, 34), "firmware/eth", f_path, FAINT)
    # status pill
    if t >= T_FIX and reset < 0.5:
        sdot, slab = SAGE, "CITED"
    elif T_CALL <= t < T_SRCH and reset < 0.5:
        sdot, slab = AMBER, "CALLING SEARCH_DOCS"
    elif T_SRCH <= t < T_FIX and reset < 0.5:
        sdot, slab = AMBER, "READING CORPUS"
    else:
        sdot, slab = FAINT, "EDITING"
    sw = tw(d, slab, f_status) + len(slab) * 0.6
    px1 = 858
    px0 = px1 - (sw + 30)
    rr(d, (px0, 26, px1, 52), 13, fill=PANEL, outline=LINE, width=1)
    pulse = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t / 230.0)) if slab not in ("EDITING", "CITED") else 1.0
    d.ellipse([(px0 + 12) * S - 4 * S, 39 * S - 4 * S, (px0 + 12) * S + 4 * S, 39 * S + 4 * S], fill=blend(sdot, pulse, PANEL))
    tracked(d, (px0 + 22, 33), slab, f_status, sdot, 0.6)

    # ---- gutter ----
    rect(d, (20, 64, 66, 360), fill=GUT)
    ln(d, (66, 64, 66, 360), fill=LINE)

    cxl = 86          # code text left
    top = 88
    lh = 31
    showtyped = 0 if reset > 0.6 else (len(TYPED) if t >= T_TYPE1 else max(0, int((t - T_TYPE0) / (T_TYPE1 - 200 - T_TYPE0) * len(TYPED))))
    diff = fixA * (1 - reset)
    shift = diff * lh  # rows below the active line slide down to make room for the +line

    def gutter(y, s, fill):
        T(d, (43, y), s, f_num, fill, anchor="ma")

    # row 40
    y = top
    gutter(y, "40", FAINT)
    T(d, (cxl, y), "static void ", f_code, PUR)
    x = cxl + tw(d, "static void ", f_code)
    T(d, (x, y), "eth_dma_init", f_code, CODE)
    T(d, (x + tw(d, "eth_dma_init", f_code), y), "(void) {", f_code, INK)
    # row 41 comment
    y += lh
    gutter(y, "41", FAINT)
    T(d, (cxl, y), "  /* program Tx descriptor list base */", f_code, COMMENT)

    # ---- active line: the from-memory guess; becomes red '-' on fix ----
    ay = top + 2 * lh
    vis = 1 - reset                       # line-42 content fades out on loop reset
    typing = t < T_TYPE1 and reset < 0.6
    if diff > 0.02:
        rect(d, (66, ay - 4, 880, ay + lh - 6), fill=blend(DIFF_RED, diff, CARD))
        gutter(ay, "-", blend(RED, diff))
    else:
        gutter(ay, "42", FAINT)
    n = showtyped if typing else len(TYPED)   # char-by-char reveal, else full line
    shown = TYPED[:n]
    pre = "  ETH->"
    x = cxl
    T(d, (x, ay), pre[:n], f_code, blend(INK, (1 - 0.25 * diff) * vis))
    x += tw(d, pre[:n], f_code)
    name_shown = shown[len(pre):len(pre) + len(WRONG)] if n > len(pre) else ""
    T(d, (x, ay), name_shown, f_code, blend(blend(RED, diff, CODE), vis))
    if diff > 0.4:  # strike-through grows across the struck name
        sx = x + tw(d, WRONG, f_code) * ease((t - T_FIX) / 260)
        ln(d, (x, ay + 9, sx, ay + 9), 2, fill=blend(RED, diff * vis))
    x += tw(d, name_shown, f_code)
    assign_shown = shown[len(pre) + len(WRONG):] if n > len(pre) + len(WRONG) else ""
    T(d, (x, ay), assign_shown, f_code, blend(INK if diff < 0.5 else (150, 120, 120), vis))
    # caret while typing / pausing on the wrong line
    if reset < 0.3 and t < T_CALL and (t < T_TYPE1 or int(t / 430) % 2 == 0):
        cxr = x + tw(d, assign_shown, f_code) + 2
        rect(d, (cxr, ay - 2, cxr + 2, ay + 18), fill=CODE)

    # ---- inserted '+' cited line ----
    if diff > 0.02:
        py = ay + lh
        a = diff
        rect(d, (66, py - 4, 880, py + lh - 6), fill=blend(DIFF_GRN, a, CARD))
        gutter(py, "+", blend(GREEN, a))
        T(d, (cxl, py), "  ETH->", f_code, blend(INK, a))
        x = cxl + tw(d, "  ETH->", f_code)
        T(d, (x, py), RIGHT, f_codeb, blend(GREEN, a))
        T(d, (x + tw(d, RIGHT, f_codeb), py), ASSIGN, f_code, blend(INK, a))
        # landing flash
        flash = max(0.0, 1 - (t - T_FIX) / 420) if t >= T_FIX else 0
        if flash > 0:
            ln(d, (66, py - 4, 66, py + lh - 6), 3, fill=blend(SAGE, flash * a))

    # ---- row 44 (slides down by `shift`) ----
    y4 = ay + lh + shift
    gutter(y4, "44", FAINT)
    T(d, (cxl, y4), "  ETH->DMACTXCR |= ETH_DMACTXCR_ST;", f_code, blend(MUT, 1 - 0.0))

    # ---- byteask panel: tool-call chip -> citation card ----
    if t >= T_CALL and reset < 0.7:
        a = ease((t - T_CALL) / 240) * (1 - ease((reset - 0.2) / 0.5) if reset > 0.2 else 1)
        py = top + 4 * lh + 16
        full = citeA
        h = 30 + full * 70
        rr(d, (cxl, py, 800, py + h), 11, fill=blend(PANEL2, a, CARD), outline=blend(SAGEd if full > 0.3 else LINE, a, CARD), width=1)
        ln(d, (cxl, py, cxl, py + h), 3, fill=blend(SAGE, a))
        # spinner / check
        gx, gy = cxl + 18, py + 16
        if t < T_FIX:
            ang = (t / 1.6) % 360
            d.arc([(gx - 7) * S, (gy - 7) * S, (gx + 7) * S, (gy + 7) * S], ang, ang + 260, fill=blend(AMBER, a), width=2 * S)
        else:
            ln(d, (gx - 4, gy, gx, gy + 5), 2, fill=blend(SAGE, a))
            ln(d, (gx, gy + 5, gx + 7, gy - 5), 2, fill=blend(SAGE, a))
        fx = cxl + 34
        T(d, (fx, py + 9), "byteask.", f_fn, blend(MUT, a))
        fx += tw(d, "byteask.", f_fn)
        T(d, (fx, py + 9), "search_docs", f_fn, blend(SAGE, a))
        fx += tw(d, "search_docs", f_fn) + 10
        if full > 0.3:  # VERBATIM tag in expanded state
            tagx = fx
            rr(d, (tagx, py + 8, tagx + 74, py + 26), 9, fill=blend((22, 34, 32), full * a, CARD), outline=blend(SAGEd, full * a, CARD), width=1)
            tracked(d, (tagx + 9, py + 12), "VERBATIM", f_tag, blend(SAGE, full * a), 0.5)
        elif t < T_SRCH:  # calling: show arg
            T(d, (fx, py + 9), f'"{ARG}"', f_arg, blend(FAINT, a))
        elif t < T_FIX:  # searching: scan bars + caption
            for i in range(3):
                bh = (7 + 9 * (0.5 + 0.5 * math.sin(t / 150.0 + i * 1.1)))
                bxx = fx + i * 7
                rr(d, (bxx, py + 18 - bh, bxx + 4, py + 18), 2, fill=blend(SAGE if i == 1 else SAGEd, a))
            T(d, (fx + 30, py + 9), f"reading {CORPUS}…", f_cap, blend(MUT, a))
        # expanded citation body
        if full > 0.15:
            b = full * a
            T(d, (cxl + 20, py + 40), SNIPHEAD, f_codeb, blend(CODE, b))
            T(d, (cxl + 20 + tw(d, SNIPHEAD, f_codeb), py + 41), SNIPTAIL, f_snip, blend(INK, b))
            ln(d, (cxl + 20, py + 64, 780, py + 64), 1, fill=blend(LINE, b))
            d.ellipse([(cxl + 26) * S - 4 * S, (py + 84) * S - 4 * S, (cxl + 26) * S + 4 * S, (py + 84) * S + 4 * S], outline=blend(SAGE, b), width=2 * S)
            T(d, (cxl + 40, py + 78), CITE, f_cite, blend(SAGE, b))

    # ---- editor bottom status bar (chrome + the install hook) ----
    rr(d, (20, 360, 880, 386), 15, fill=BAR)
    rect(d, (20, 360, 880, 374), fill=BAR)
    ln(d, (20, 360, 880, 360), fill=LINE)
    d.ellipse([40 * S - 4 * S, 373 * S - 4 * S, 40 * S + 4 * S, 373 * S + 4 * S], fill=SAGE)
    T(d, (52, 367), "byteask-embedded-docs", f_bar, SAGE)
    bx = 52 + tw(d, "byteask-embedded-docs", f_bar) + 12
    T(d, (bx, 367), "MCP connected", f_bar2, FAINT)
    T(d, (860, 367), "mcp.byteask.ai/mcp", f_bar2, MUT, anchor="ra")

    return img.resize((W, H), Image.LANCZOS)


def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH")
    nframes = int(TOTAL / 1000 * FPS)
    tmp = tempfile.mkdtemp(prefix="byteask_demo_")
    try:
        for i in range(nframes):
            frame(i / FPS * 1000).save(os.path.join(tmp, f"f{i:04d}.png"))
        pal = os.path.join(tmp, "pal.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(tmp, "f%04d.png"),
                        "-vf", "palettegen=max_colors=128:stats_mode=diff", pal], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f%04d.png"), "-i", pal,
                        "-lavfi", "paletteuse=dither=bayer:bayer_scale=3", "-loop", "0", OUT], check=True)
        print(f"wrote {OUT}  ({nframes} frames, {os.path.getsize(OUT) // 1024} KB)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
