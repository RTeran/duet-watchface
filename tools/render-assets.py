"""
Renders every image asset of the Duet watchface into both device targets:

  background.png       466x466 dial: Jost numerals at 12/3/6/9 + hour batons
  hands/hour.png       floating hour hand (ivory, outer segment only)
  hands/minute.png     floating minute hand — Champagne (the default theme)
  hands/minute-<key>.png   the minute hand pre-rendered in each editable theme
  hands/hour-aod.png   hour hand dimmed to gray (0x999999) for AOD
  hands/minute-aod.png minute hand dimmed to gray (0x999999) for AOD
  images/preview.png   full-dial circular thumbnail at 10:09 (store convention)

  edit/preview-color-<key>.png  a faithful mini-dial per theme, shown in the
                                on-watch color picker (WATCHFACE_EDIT_GROUP)
  edit/select.png / un_select.png  the selection ring drawn on the editable zone
  edit/mask100.png / mask70.png    firmware-mandated edit masks, kept fully
                                   transparent so the dial stays crisp in edit mode

The accent color (minute hand + digital digits) is the only thing that varies
between themes; the hour hand and the dial numerals stay ivory. Because
TIME_POINTER cannot tint a PNG at runtime, the minute hand is baked once per
theme and watchface/index.js swaps `minute_path` based on the on-watch selection.

Geometry constants here MUST stay in sync with watchface/index.js (HAND_*).
Theme colors here MUST stay in sync with the THEMES map in watchface/index.js.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(__file__)
TARGETS = [
    "../assets/466x466-amazfit-active-2-round",
    "../assets/466x466-amazfit-gtr-4",
]
NUMERAL_FONT_PATH = os.path.join(BASE, "fonts", "Jost-Light.ttf")
DIGIT_FONT_PATH = os.path.join(BASE, TARGETS[0], "fonts", "Jost-Light.ttf")
# Material Icons Outlined, subset to Duet's glyphs + converted CFF→glyf by
# tools/make-icon-font.py. Used here only to draw the edit-mode preview icons;
# the watch bundles the same file and renders the glyphs live as TEXT widgets.
ICONS_FONT_PATH = os.path.join(BASE, "fonts", "icons-outlined.ttf")

SIZE = 466
CX = SIZE / 2  # 233
S = 3  # supersampling factor for the dial / preview

IVORY = (255, 251, 240, 255)
AOD_GRAY = (153, 153, 153, 255)  # 0x999999 — dimmed hands in AOD, matching AOD_GRAY digits in index.js
TICK = (150, 146, 136, 255)  # dimmed ivory: batons sit below numerals in hierarchy

# Editable accent themes (minute hand + digital digits). Champagne is the default
# and reuses hands/minute.png; every other theme gets hands/minute-<key>.png.
# Keys and colors MUST match the THEMES map in watchface/index.js.
THEMES = [
    ("champagne", (232, 201, 126)),  # e8c97e — default
    ("rose", (224, 168, 153)),       # e0a899
    ("copper", (201, 138, 94)),      # c98a5e
    ("amethyst", (182, 156, 214)),   # b69cd6
    ("sapphire", (127, 166, 217)),   # 7fa6d9
    ("turquoise", (111, 194, 194)),  # 6fc2c2
    ("emerald", (108, 191, 154)),    # 6cbf9a
    ("ivory", (255, 251, 240)),      # fffbf0 — monochrome: matches the dial ivory
]
DEFAULT_THEME = "champagne"

# Dial
NUMERAL_SIZE = 52
NUMERAL_R = 197  # radius of each numeral's center — hugging the rim
TICK_R_OUT = 222
TICK_R_IN = 202
TICK_W = 4

# Hands — tip radius, visible-from radius, bar width (px at 1x).
# Mirrored in watchface/index.js as HAND_* constants.
MINUTE_TIP_R = 205
MINUTE_VIS_R = 100
MINUTE_W = 6
HOUR_TIP_R = 155
HOUR_VIS_R = 100  # aligned with the minute hand so the empty ring reads as one
HOUR_W = 10

# Digital center (preview only; the watch renders live TEXT widgets)
DIGIT_SIZE = 84
DIGIT_ROW_DY = 42  # each row's center offset from CY — mirrored in index.js

PREVIEW_HOUR = 10
PREVIEW_MINUTE = 9

# Edit-mode chrome. All three tap zones are the SAME size, so ONE ring/preview
# size renders 1:1 on every zone (matches the official ZeppOS pattern: the ring
# image and preview equal the zone's w/h; a mismatched size renders scaled/
# overflowing — the bug the first pass had). tips is the name-tag background.
EDIT_ZONE = 92    # tap-zone w/h AND select/un_select ring + preview canvas
EDIT_THUMB = 92   # edit-mode preview size = the zone (renders 1:1, no overflow)
RING_FRAC = 0.92  # ring radius as a fraction of the zone half-width
RING_W = 3        # ring stroke width (px at 1x) — thin and minimal
TIPS_W = 124      # name-tag background width  (index.js tips_width)
TIPS_H = 36       # name-tag background height
# Edit-mode dim. WATCHFACE_EDIT_MASK sits BELOW the edit groups, so a dark veil
# there dims only the live dial — the preview thumbnails (opaque discs) and their
# name tags stay crisp on top. WATCHFACE_EDIT_FG_MASK sits ABOVE the edit UI, so
# ANY opacity there veils the previews + names (the "todo apagado" bug); it MUST
# stay transparent. Only the background mask carries the dimming.
MASK_BG_ALPHA = 210   # WATCHFACE_EDIT_MASK — near-opaque black, dims the dial only
MASK_FG_ALPHA = 0     # WATCHFACE_EDIT_FG_MASK — transparent; a veil here dims the edit UI

# Complications — two circular badges (top y=108, bottom y=358 in index.js). The
# ring is baked here as a PNG (crisp, reliable) for both the closed border and the
# gray progress track; index.js overlays the live progress fill with ARC_PROGRESS.
# COMP_RING_CENTER_R MUST equal the ARC_PROGRESS `radius` in index.js so the fill
# sits exactly on the baked track.
COMP_R_OUTER = 31                              # badge radius → 62px PNG
COMP_RING_W = 3                                # ring stroke width
COMP_RING_CENTER_R = COMP_R_OUTER - COMP_RING_W / 2  # 29.5 — ring centerline
TRACK_GRAY = (67, 64, 58, 255)                 # #43403a — progress track under the ivory fill

# Edit-mode preview thumbnails, one per datum (shared by the top & bottom groups).
# Tuple: (datum, kind, value, sub, icon_char, level%). `sub` is stacked text
# (weekday / wordmark); `icon_char` is a glyph from icons-outlined.ttf.
COMP_PREVIEW_SPECS = [
    ("empty",    "empty",    None,       None,  None,      0),
    ("date",     "closed",   "3",        "FRI", None,      0),
    ("battery",  "progress", "87",       None,  "",  87),
    ("steps",    "progress", "6.2k",     None,  "",  62),
    ("calories", "progress", "430",      None,  "",  45),
    ("hr",       "closed",   "72",       None,  "",  0),
    ("weather",  "closed",   "21°", None,  "",  0),
    ("pai",      "progress", "80",       "PAI", None,      80),
]


def polar(r, deg):
    """Clock angle (0 = 12 o'clock, clockwise) to canvas x,y at 1x scale."""
    rad = math.radians(deg - 90)
    return CX + r * math.cos(rad), CX + r * math.sin(rad)


def render_background():
    img = Image.new("RGBA", (SIZE * S, SIZE * S), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(NUMERAL_FONT_PATH, NUMERAL_SIZE * S)

    for hour in range(1, 13):
        deg = hour * 30
        if hour % 3 == 0:
            label = str(hour if hour != 0 else 12)
            x, y = polar(NUMERAL_R, deg)
            draw.text((x * S, y * S), label, font=font, fill=IVORY, anchor="mm")
        else:
            x1, y1 = polar(TICK_R_IN, deg)
            x2, y2 = polar(TICK_R_OUT, deg)
            draw.line(
                (x1 * S, y1 * S, x2 * S, y2 * S), fill=TICK, width=TICK_W * S
            )

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def render_hand(tip_r, vis_r, width, fill):
    """Hand image pointing to 12: tip at row 0, rotation point at (w/2, tip_r).

    Image height is tip_r + 1 so posY = tip_r (the dial center) is the last row.
    Only the outer segment [0, tip_r - vis_r] is painted; the rest stays
    transparent, which is what makes the hand float.
    """
    hs = 4  # hands get extra supersampling: they are small and rotate
    pad = 2  # transparent border so LANCZOS never clips the antialiased edge
    w = width + pad * 2
    h = tip_r + 1
    img = Image.new("RGBA", (w * hs, h * hs), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (pad * hs, 0, (pad + width) * hs, (tip_r - vis_r) * hs),
        radius=(width / 2) * hs,
        fill=fill,
    )
    return img.resize((w, h), Image.LANCZOS), w // 2, tip_r


def paste_hand_rotated(canvas, hand, pos_x, pos_y, deg):
    """Composites a hand on the 1x canvas rotated deg clockwise about the center."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(hand, (int(CX - pos_x), int(CX - pos_y)))
    layer = layer.rotate(-deg, center=(CX, CX), resample=Image.BICUBIC)
    canvas.alpha_composite(layer)


def circular_mask(img):
    mask = Image.new("L", (SIZE * S, SIZE * S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, SIZE * S - 1, SIZE * S - 1), fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask.resize((SIZE, SIZE), Image.LANCZOS))
    return out


def render_preview(background, hour_hand, minute_hand, accent):
    """Full-dial mini watchface at 10:09, circular-cropped. `accent` (RGB) tints
    the digital digits; the minute hand is already rendered in that accent."""
    canvas = background.convert("RGBA")

    hour_deg = (PREVIEW_HOUR % 12 + PREVIEW_MINUTE / 60) * 30
    minute_deg = PREVIEW_MINUTE * 6
    (hour_img, hx, hy) = hour_hand
    (minute_img, mx, my) = minute_hand
    paste_hand_rotated(canvas, hour_img, hx, hy, hour_deg)
    paste_hand_rotated(canvas, minute_img, mx, my, minute_deg)

    hi = Image.new("RGBA", (SIZE * S, SIZE * S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hi)
    font = ImageFont.truetype(DIGIT_FONT_PATH, DIGIT_SIZE * S)
    for text, dy in (
        (f"{PREVIEW_HOUR:02d}", -DIGIT_ROW_DY),
        (f"{PREVIEW_MINUTE:02d}", DIGIT_ROW_DY),
    ):
        draw.text(
            ((CX) * S, (CX + dy) * S), text, font=font, fill=accent + (255,), anchor="mm"
        )
    canvas.alpha_composite(hi.resize((SIZE, SIZE), Image.LANCZOS))

    return circular_mask(canvas)


def render_edit_ring(alpha):
    """A thin ivory ring on transparency — the affordance drawn on the editable
    zone in edit mode. A real, non-empty image is required: a transparent
    placeholder makes the picker fall back to a broken-image icon."""
    ss = 3
    n = EDIT_ZONE * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = n * (1 - RING_FRAC) / 2
    d.ellipse(
        [m, m, n - m - 1, n - m - 1],
        outline=(255, 251, 240, alpha),
        width=RING_W * ss,
    )
    return img.resize((EDIT_ZONE, EDIT_ZONE), Image.LANCZOS)


def render_tips():
    """The name-tag background behind the option title in edit mode. The firmware
    draws the option title on top in a FIXED DARK color (not configurable) — the
    official color-world sample uses a bright, opaque pill for exactly this reason.
    A dark pill therefore hides the text (the "names don't show" bug); the pill MUST
    be light. Opaque ivory with a thin dark hairline so it reads as a tag over the
    dimmed dial and the dark firmware text stays legible."""
    ss = 3
    w, h = TIPS_W * ss, TIPS_H * ss
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [ss, ss, w - ss, h - ss], radius=(h / 2 - ss),
        fill=(255, 251, 240, 255), outline=(18, 16, 12, 160), width=ss,
    )
    return img.resize((TIPS_W, TIPS_H), Image.LANCZOS)


def minute_hand_name(key):
    return "hands/minute.png" if key == DEFAULT_THEME else f"hands/minute-{key}.png"


def render_comp_ring(color):
    """A 62px badge ring (annulus) in `color`: the closed ivory border, or the
    gray progress track over which index.js draws the ARC_PROGRESS fill."""
    n = COMP_R_OUTER * 2
    img = Image.new("RGBA", (n * S, n * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n * S / 2
    ro = (COMP_RING_CENTER_R + COMP_RING_W / 2) * S
    ri = (COMP_RING_CENTER_R - COMP_RING_W / 2) * S
    d.ellipse([c - ro, c - ro, c + ro, c + ro], fill=color)
    d.ellipse([c - ri, c - ri, c + ri, c + ri], fill=(0, 0, 0, 0))
    return img.resize((n, n), Image.LANCZOS)


def render_comp_preview(kind, value, sub, icon_char, level):
    """An EDIT_THUMB-px edit-mode thumbnail: the badge on a dark disc, so each
    option reads clearly in the on-watch picker. Mirrors the runtime badge layout
    (value above, icon/weekday below); progress fills clockwise from 12 o'clock.
    All geometry is a fraction of the canvas so it scales with EDIT_THUMB."""
    ss = 3
    n = EDIT_THUMB * ss
    face = (6, 6, 7, 255)
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    d.ellipse([0, 0, n - 1, n - 1], fill=face)

    r = 0.44 * n              # ring centerline radius (fraction of the thumb)
    w = max(2, round(0.055 * n))

    def annulus(col):
        d.ellipse([c - r - w / 2, c - r - w / 2, c + r + w / 2, c + r + w / 2], fill=col)
        d.ellipse([c - r + w / 2, c - r + w / 2, c + r - w / 2, c + r - w / 2], fill=face)

    if kind == "empty":
        dash_w = max(1, round(0.022 * n))
        for k in range(0, 32, 2):  # dashed faint ring — a tappable-but-off slot
            d.arc([c - r, c - r, c + r, c + r], k / 32 * 360, (k + 1) / 32 * 360,
                  fill=(90, 86, 76, 255), width=dash_w)
        return img.resize((EDIT_THUMB, EDIT_THUMB), Image.LANCZOS)

    if kind == "progress":
        annulus(TRACK_GRAY)
        if level and level > 0:                      # fill clockwise from 12 o'clock
            end = -90 + 360 * min(level, 100) / 100.0
            d.arc([c - r, c - r, c + r, c + r], -90, end, fill=IVORY, width=w)
    else:
        annulus(IVORY)

    fval = ImageFont.truetype(DIGIT_FONT_PATH, round(0.30 * n))
    d.text((c, c - 0.08 * n), value, font=fval, fill=IVORY, anchor="mm")
    if sub:
        fsub = ImageFont.truetype(DIGIT_FONT_PATH, round(0.15 * n))
        d.text((c, c + 0.17 * n), sub, font=fsub, fill=(201, 195, 180, 255), anchor="mm")
    elif icon_char:
        fic = ImageFont.truetype(ICONS_FONT_PATH, round(0.22 * n))
        d.text((c, c + 0.17 * n), icon_char, font=fic, fill=IVORY, anchor="mm")
    return img.resize((EDIT_THUMB, EDIT_THUMB), Image.LANCZOS)


def main():
    background = render_background()
    # Hour hand stays ivory across every theme.
    hour_hand = render_hand(HOUR_TIP_R, HOUR_VIS_R, HOUR_W, IVORY)

    # AOD hands — one dimmed-gray pair, theme-independent, matching the AOD digits.
    aod_hour = render_hand(HOUR_TIP_R, HOUR_VIS_R, HOUR_W, AOD_GRAY)
    aod_minute = render_hand(MINUTE_TIP_R, MINUTE_VIS_R, MINUTE_W, AOD_GRAY)

    # Minute hand + faithful color-picker thumbnail, one per theme.
    minute_hands = {}
    edit_previews = {}
    for key, rgb in THEMES:
        mh = render_hand(MINUTE_TIP_R, MINUTE_VIS_R, MINUTE_W, rgb + (255,))
        minute_hands[key] = mh
        edit_previews[key] = render_preview(background, hour_hand, mh, rgb).resize(
            (EDIT_THUMB, EDIT_THUMB), Image.LANCZOS
        )

    # Store preview keeps the default (Champagne) look.
    default_rgb = dict(THEMES)[DEFAULT_THEME]
    store_preview = render_preview(
        background, hour_hand, minute_hands[DEFAULT_THEME], default_rgb
    )

    select_ring = render_edit_ring(235)
    unselect_ring = render_edit_ring(90)
    # Edit-mode dim masks (darken the live face) + the name-tag background.
    mask_bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, MASK_BG_ALPHA))
    mask_fg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, MASK_FG_ALPHA))
    tips_tag = render_tips()

    # Complication badge rings + one edit-preview thumbnail per datum (shared by
    # the top and bottom edit groups, since both offer the same catalog).
    comp_ring_closed = render_comp_ring(IVORY)
    comp_ring_track = render_comp_ring(TRACK_GRAY)
    comp_previews = {
        datum: render_comp_preview(kind, value, sub, icon, level)
        for (datum, kind, value, sub, icon, level) in COMP_PREVIEW_SPECS
    }

    for target in TARGETS:
        root = os.path.join(BASE, target)
        os.makedirs(os.path.join(root, "hands"), exist_ok=True)
        os.makedirs(os.path.join(root, "images"), exist_ok=True)
        os.makedirs(os.path.join(root, "edit"), exist_ok=True)
        os.makedirs(os.path.join(root, "comp"), exist_ok=True)

        background.save(os.path.join(root, "background.png"))
        hour_hand[0].save(os.path.join(root, "hands", "hour.png"))
        aod_hour[0].save(os.path.join(root, "hands", "hour-aod.png"))
        aod_minute[0].save(os.path.join(root, "hands", "minute-aod.png"))
        for key, _ in THEMES:
            minute_hands[key][0].save(os.path.join(root, minute_hand_name(key)))
        store_preview.save(os.path.join(root, "images", "preview.png"))

        for key, _ in THEMES:
            edit_previews[key].save(
                os.path.join(root, "edit", f"preview-color-{key}.png")
            )
        select_ring.save(os.path.join(root, "edit", "select.png"))
        unselect_ring.save(os.path.join(root, "edit", "un_select.png"))
        mask_bg.save(os.path.join(root, "edit", "mask100.png"))
        mask_fg.save(os.path.join(root, "edit", "mask70.png"))
        tips_tag.save(os.path.join(root, "edit", "tips.png"))

        comp_ring_closed.save(os.path.join(root, "comp", "ring-closed.png"))
        comp_ring_track.save(os.path.join(root, "comp", "ring-track.png"))
        for datum, thumb in comp_previews.items():
            thumb.save(os.path.join(root, "edit", f"preview-comp-{datum}.png"))

        print(
            f"{target}: background, hour + {len(THEMES)} minute hands, "
            f"2 AOD hands, preview, {len(THEMES)} edit thumbnails, ring + masks"
        )

    print(
        "hour hand posX/posY = "
        f"{hour_hand[1]}/{hour_hand[2]}, minute = "
        f"{minute_hands[DEFAULT_THEME][1]}/{minute_hands[DEFAULT_THEME][2]}"
    )


if __name__ == "__main__":
    main()
