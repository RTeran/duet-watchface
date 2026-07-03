"""
Renders every image asset of the Duet watchface into both device targets:

  background.png       466x466 dial: Jost numerals at 12/3/6/9 + hour batons
  hands/hour.png       floating hour hand (ivory, outer segment only)
  hands/minute.png     floating minute hand — Champagne (the default theme)
  hands/minute-<key>.png   the minute hand pre-rendered in each editable theme
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

SIZE = 466
CX = SIZE / 2  # 233
S = 3  # supersampling factor for the dial / preview

IVORY = (255, 251, 240, 255)
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
NUMERAL_SIZE = 60
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
DIGIT_SIZE = 64
DIGIT_ROW_DY = 32  # each row's center offset from CY — mirrored in index.js

PREVIEW_HOUR = 10
PREVIEW_MINUTE = 9

# Edit-mode chrome
EDIT_THUMB = 192  # color-picker thumbnail size (downscaled from the full dial)
EDIT_ZONE = 200   # select/un_select ring canvas — matches the edit zone w/h
RING_FRAC = 0.92  # ring radius as a fraction of the zone half-width
RING_W = 3        # ring stroke width (px at 1x) — thin and minimal


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


def minute_hand_name(key):
    return "hands/minute.png" if key == DEFAULT_THEME else f"hands/minute-{key}.png"


def main():
    background = render_background()
    # Hour hand stays ivory across every theme.
    hour_hand = render_hand(HOUR_TIP_R, HOUR_VIS_R, HOUR_W, IVORY)

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
    transparent_mask = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    for target in TARGETS:
        root = os.path.join(BASE, target)
        os.makedirs(os.path.join(root, "hands"), exist_ok=True)
        os.makedirs(os.path.join(root, "images"), exist_ok=True)
        os.makedirs(os.path.join(root, "edit"), exist_ok=True)

        background.save(os.path.join(root, "background.png"))
        hour_hand[0].save(os.path.join(root, "hands", "hour.png"))
        for key, _ in THEMES:
            minute_hands[key][0].save(os.path.join(root, minute_hand_name(key)))
        store_preview.save(os.path.join(root, "images", "preview.png"))

        for key, _ in THEMES:
            edit_previews[key].save(
                os.path.join(root, "edit", f"preview-color-{key}.png")
            )
        select_ring.save(os.path.join(root, "edit", "select.png"))
        unselect_ring.save(os.path.join(root, "edit", "un_select.png"))
        transparent_mask.save(os.path.join(root, "edit", "mask100.png"))
        transparent_mask.save(os.path.join(root, "edit", "mask70.png"))

        print(
            f"{target}: background, hour + {len(THEMES)} minute hands, preview, "
            f"{len(THEMES)} edit thumbnails, ring + masks"
        )

    print(
        "hour hand posX/posY = "
        f"{hour_hand[1]}/{hour_hand[2]}, minute = "
        f"{minute_hands[DEFAULT_THEME][1]}/{minute_hands[DEFAULT_THEME][2]}"
    )


if __name__ == "__main__":
    main()
