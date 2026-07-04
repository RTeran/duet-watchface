"""
Renders the Zepp Console (store) image pack into store/ at the repo root.
Everything is circular (alpha-masked) per the store requirement:

  store/icon-240.png            240x240 app icon — circular, transparent bg,
                                no margins (Zepp Console icon spec)
  store/preview-<theme>.png     466x466 dial at 10:09 with the DEFAULT
                                complications (Date left, Battery right)
  store/preview-aod.png         466x466 AOD look: gray hands + digits only
  store/preview-animated.gif    every theme + complication configs + AOD,
                                900ms/frame, circular (1-bit transparency)
  store/360/<same names>        360x360 copies — the documented size for
                                circular-screen store screenshots

Reuses the renderer in render-assets.py (backgrounds, hands, rings, fonts).
Badge geometry mirrors the runtime widgets in watchface/index.js
(makeComplication): value 26px centered at cy-7, weekday 13px / icon 17px
centered at cy+13, progress fill clockwise from 12 o'clock.
"""

import importlib.util
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(__file__)
STORE = os.path.join(BASE, "..", "store")

spec = importlib.util.spec_from_file_location(
    "render_assets", os.path.join(BASE, "render-assets.py")
)
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

# Runtime badge layout — MUST stay in sync with watchface/index.js.
COMP_LEFT_X = 120
COMP_RIGHT_X = 346
COMP_AXIS_Y = ra.CX  # 233 — the horizontal centerline
COMP_VALUE_SIZE = 26
COMP_SUB_SIZE = 13
COMP_ICON_SIZE = 17
VALUE_DY = -7   # value box y [cy-22, cy+8] -> center
SUB_DY = 13     # weekday box y [cy+3, cy+23] / icon box y [cy+2, cy+24] -> center

SCREENSHOT_THEMES = ["champagne", "sapphire", "emerald"]
SMALL = 360  # documented circular-screen screenshot size

SPEC_BY_DATUM = {s[0]: s for s in ra.COMP_PREVIEW_SPECS}


def render_badge(datum):
    """One 62px badge on transparency, mirroring the runtime widget stack:
    ring PNG (closed or track+fill), value text, weekday/icon below."""
    _, kind, value, sub, icon, level = SPEC_BY_DATUM[datum]
    n = ra.COMP_R_OUTER * 2
    ss = ra.S
    img = Image.new("RGBA", (n * ss, n * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n * ss / 2

    ring = ra.render_comp_ring(ra.TRACK_GRAY if kind == "progress" else ra.IVORY)
    img.alpha_composite(ring.resize((n * ss, n * ss), Image.LANCZOS))
    if kind == "progress" and level:
        r = ra.COMP_RING_CENTER_R * ss
        end = -90 + 360 * min(level, 100) / 100.0
        d.arc([c - r, c - r, c + r, c + r], -90, end,
              fill=ra.IVORY, width=ra.COMP_RING_W * ss)

    fval = ImageFont.truetype(ra.DIGIT_FONT_PATH, COMP_VALUE_SIZE * ss)
    d.text((c, c + VALUE_DY * ss), value, font=fval, fill=ra.IVORY, anchor="mm")
    if sub:
        fsub = ImageFont.truetype(ra.DIGIT_FONT_PATH, COMP_SUB_SIZE * ss)
        d.text((c, c + SUB_DY * ss), sub, font=fsub, fill=ra.IVORY, anchor="mm")
    elif icon:
        fic = ImageFont.truetype(ra.ICONS_FONT_PATH, COMP_ICON_SIZE * ss)
        d.text((c, c + SUB_DY * ss), icon, font=fic, fill=ra.IVORY, anchor="mm")

    return img.resize((n, n), Image.LANCZOS)


DEFAULT_COMPS = ("date", "battery")


def background_with_badges(background, comps=DEFAULT_COMPS):
    """Badges composite onto the background so render_preview draws the hands
    ON TOP — same z-order as the watch (badge widgets precede TIME_POINTER).
    `comps` is (left_datum, right_datum); None leaves that slot empty."""
    bg = background.convert("RGBA").copy()
    for datum, cx in zip(comps, (COMP_LEFT_X, COMP_RIGHT_X)):
        if datum is None:
            continue
        badge = render_badge(datum)
        bg.alpha_composite(
            badge, (int(cx - ra.COMP_R_OUTER), int(COMP_AXIS_Y - ra.COMP_R_OUTER))
        )
    return bg


def render_aod():
    """AOD scene: black dial, gray hands + gray digits, no numerals, no badges —
    only the show_level AOD widgets from index.js."""
    black = Image.new("RGBA", (ra.SIZE, ra.SIZE), (0, 0, 0, 255))
    hour = ra.render_hand(ra.HOUR_TIP_R, ra.HOUR_VIS_R, ra.HOUR_W, ra.AOD_GRAY)
    minute = ra.render_hand(ra.MINUTE_TIP_R, ra.MINUTE_VIS_R, ra.MINUTE_W, ra.AOD_GRAY)
    return ra.render_preview(black, hour, minute, ra.AOD_GRAY[:3])


def to_gif_frames(images):
    """GIF has 1-bit transparency: quantize to 255 colors and reserve index 255
    for pixels outside the circle (alpha < 128 — the antialiased rim collapses
    to a hard edge, an unavoidable GIF limitation). All frames MUST share one
    global palette: Pillow re-encodes appended frames whose palette differs
    from the first, which visibly erodes the circular rim."""
    sheet = Image.new("RGB", (images[0].width * len(images), images[0].height))
    for i, img in enumerate(images):
        sheet.paste(img.convert("RGB"), (i * img.width, 0))
    palette = sheet.quantize(colors=255)

    frames = []
    for img in images:
        frame = img.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
        hole = img.getchannel("A").point(lambda a: 255 if a < 128 else 0)
        frame.paste(255, hole)
        frames.append(frame)
    return frames


def render_gif_frames(hour_hand, plain_background, themes):
    """Story: every theme with the default complications, then the champagne
    theme across configurations (no badges, activity pair, ambient pair), AOD."""
    default_bg = background_with_badges(plain_background)
    frames = []

    for key, rgb in ra.THEMES:
        minute = ra.render_hand(
            ra.MINUTE_TIP_R, ra.MINUTE_VIS_R, ra.MINUTE_W, rgb + (255,)
        )
        frames.append(ra.render_preview(default_bg, hour_hand, minute, rgb))

    champagne_rgb = themes[ra.DEFAULT_THEME]
    champagne_minute = ra.render_hand(
        ra.MINUTE_TIP_R, ra.MINUTE_VIS_R, ra.MINUTE_W, champagne_rgb + (255,)
    )
    for comps in ((None, None), ("steps", "hr"), ("weather", "pai")):
        bg = background_with_badges(plain_background, comps)
        frames.append(
            ra.render_preview(bg, hour_hand, champagne_minute, champagne_rgb)
        )

    frames.append(render_aod())
    return frames


def save_gif(frames, path, size):
    scaled = to_gif_frames(
        [f.resize((size, size), Image.LANCZOS) for f in frames]
    )
    scaled[0].save(
        path,
        save_all=True,
        append_images=scaled[1:],
        duration=900,
        loop=0,
        disposal=2,
        transparency=255,
        optimize=False,
    )


def main():
    os.makedirs(os.path.join(STORE, "360"), exist_ok=True)

    plain_background = ra.render_background()
    background = background_with_badges(plain_background)
    hour_hand = ra.render_hand(ra.HOUR_TIP_R, ra.HOUR_VIS_R, ra.HOUR_W, ra.IVORY)

    images = {}
    themes = dict(ra.THEMES)
    for key in SCREENSHOT_THEMES:
        rgb = themes[key]
        minute = ra.render_hand(
            ra.MINUTE_TIP_R, ra.MINUTE_VIS_R, ra.MINUTE_W, rgb + (255,)
        )
        images[f"preview-{key}.png"] = ra.render_preview(
            background, hour_hand, minute, rgb
        )
    images["preview-aod.png"] = render_aod()

    # Icon: the clean default dial (no badges) — busier art muddies 240px.
    default_minute = ra.render_hand(
        ra.MINUTE_TIP_R, ra.MINUTE_VIS_R, ra.MINUTE_W,
        themes[ra.DEFAULT_THEME] + (255,),
    )
    icon = ra.render_preview(
        plain_background, hour_hand, default_minute, themes[ra.DEFAULT_THEME]
    ).resize((240, 240), Image.LANCZOS)
    icon.save(os.path.join(STORE, "icon-240.png"))

    for name, img in images.items():
        img.save(os.path.join(STORE, name))
        img.resize((SMALL, SMALL), Image.LANCZOS).save(
            os.path.join(STORE, "360", name)
        )

    gif_frames = render_gif_frames(hour_hand, plain_background, themes)
    save_gif(gif_frames, os.path.join(STORE, "preview-animated.gif"), ra.SIZE)
    save_gif(gif_frames, os.path.join(STORE, "360", "preview-animated.gif"), SMALL)

    print(
        f"store/: icon-240 + {len(images)} previews (466) + {len(images)} at 360 "
        f"+ animated gif ({len(gif_frames)} frames, 466 & 360)"
    )


if __name__ == "__main__":
    main()
