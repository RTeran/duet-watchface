"""
Renders every image asset of the Duet watchface into both device targets:

  background.png   466x466 dial: Prata numerals at 12/3/6/9 + hour batons between
  hands/hour.png   floating hour hand (outer segment only, points to 12 o'clock)
  hands/minute.png floating minute hand (outer segment only, points to 12 o'clock)
  images/preview.png  full-dial circular thumbnail at 10:09 (store convention)

The hands are drawn with a transparent inner half: TIME_POINTER rotates the full
image around (posX, posY), so leaving the inner segment blank makes the visible
bar orbit the center like a traditional hand without an anchored axis.

Geometry constants here MUST stay in sync with watchface/index.js (HAND_*).
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(__file__)
TARGETS = [
    "../assets/466x466-amazfit-active-2-round",
    "../assets/466x466-amazfit-gtr-4",
]
# Dial numerals: Jost Light (geometric, Bauhaus/Futura lineage) — only baked
# into background.png, so it lives in tools/, not in the device assets.
# Digital heart: Rubik Bold — bundled per target because the live TEXT widgets
# render it on the watch; the preview must use the same file.
NUMERAL_FONT_PATH = os.path.join(BASE, "fonts", "Jost-Light.ttf")
# Trial: the digital heart shares the dial's Jost Light (one voice for both
# layers). Rubik-Bold.ttf stays bundled for a quick A/B revert.
DIGIT_FONT_PATH = os.path.join(BASE, TARGETS[0], "fonts", "Jost-Light.ttf")

SIZE = 466
CX = SIZE / 2  # 233
S = 3  # supersampling factor for the dial / preview

IVORY = (255, 251, 240, 255)
TICK = (150, 146, 136, 255)  # dimmed ivory: batons sit below numerals in hierarchy
CHAMPAGNE = (232, 201, 126, 255)  # digital center accent (theme "luxury" gold)

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


def render_preview(background, hands):
    canvas = background.convert("RGBA")

    hour_deg = (PREVIEW_HOUR % 12 + PREVIEW_MINUTE / 60) * 30
    minute_deg = PREVIEW_MINUTE * 6
    (hour_img, hx, hy), (minute_img, mx, my) = hands
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
            ((CX) * S, (CX + dy) * S), text, font=font, fill=CHAMPAGNE, anchor="mm"
        )
    canvas.alpha_composite(hi.resize((SIZE, SIZE), Image.LANCZOS))

    return circular_mask(canvas)


def main():
    background = render_background()
    # Minute hand in champagne: it pairs with the digital digits (both track
    # the minutes), while the hour hand stays ivory with the dial numerals.
    hour_hand = render_hand(HOUR_TIP_R, HOUR_VIS_R, HOUR_W, IVORY)
    minute_hand = render_hand(MINUTE_TIP_R, MINUTE_VIS_R, MINUTE_W, CHAMPAGNE)
    preview = render_preview(background, (hour_hand, minute_hand))

    for target in TARGETS:
        root = os.path.join(BASE, target)
        background.save(os.path.join(root, "background.png"))
        hour_hand[0].save(os.path.join(root, "hands", "hour.png"))
        minute_hand[0].save(os.path.join(root, "hands", "minute.png"))
        preview.save(os.path.join(root, "images", "preview.png"))
        print(f"{target}: background, hands/hour, hands/minute, images/preview")

    print(
        "hour hand posX/posY = "
        f"{hour_hand[1]}/{hour_hand[2]}, minute = {minute_hand[1]}/{minute_hand[2]}"
    )


if __name__ == "__main__":
    main()
