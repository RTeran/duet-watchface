"""Build assets/*/fonts/icons-outlined.ttf — the icon set the complications use.

The watchface renders each complication's identifier as a TEXT widget in this
font (tintable, scalable, one glyph per datum). It is Google's "Material Icons
Outlined" subset to the ten glyphs Duet needs and, crucially, converted from CFF
(the .otf Google ships) to glyf outlines — ZeppOS renders glyf TTFs (sfntVersion
0x00010000); a CFF-flavoured .ttf shows nothing on device.

Glyphs (classic Material Icons codepoints; the runtime chars live in
watchface/index.js for data and watchface/weather-icon.js for weather):
    data     e536 directions_walk · ef55 local_fire_department
             e1a4 battery_full     · e87d favorite
    weather  e430 wb_sunny · e42d wb_cloudy · e2bd cloud
             f1ad umbrella · eb3b ac_unit   · ebdb thunderstorm

umbrella is re-mapped to e1ad (see CODEPOINT_REMAP): at f1ad it drew blank on
the Active 2 and in the simulator, while the same outline at a lower codepoint
drew fine.

Run:  pip install fonttools  &&  python3 tools/make-icon-font.py
Only needs re-running when the glyph set changes; the output is committed.
"""
import io
import os
import urllib.request

from fontTools.ttLib import TTFont, newTable
from fontTools.subset import Subsetter, Options
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "MaterialIconsOutlined-Regular.otf")
SRC_URL = (
    "https://github.com/google/material-design-icons/raw/master/font/"
    "MaterialIconsOutlined-Regular.otf"
)
UNICODES = [0xE536, 0xEF55, 0xE1A4, 0xE87D,
            0xE430, 0xE42D, 0xE2BD, 0xF1AD, 0xEB3B, 0xEBDB]
OUTPUTS = [
    os.path.join(BASE, "..", "assets", "466x466-amazfit-active-2-round", "fonts", "icons-outlined.ttf"),
    os.path.join(BASE, "..", "assets", "466x466-amazfit-gtr-4", "fonts", "icons-outlined.ttf"),
    os.path.join(BASE, "fonts", "icons-outlined.ttf"),  # source copy for render-assets.py previews
]
CODEPOINT_REMAP = {0xF1AD: 0xE1AD}
MAX_ERR = 1.0  # cu2qu cubic→quadratic error, in 1000-upm font units (sub-pixel)


def subset_otf(path, unicodes):
    font = TTFont(path)
    opts = Options()
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.recalc_bounds = True
    ss = Subsetter(options=opts)
    ss.populate(unicodes=unicodes)
    ss.subset(font)
    return font


def otf_to_ttf(font, max_err=MAX_ERR):
    """Replace CFF cubic outlines with quadratic glyf outlines, in place."""
    glyph_set = font.getGlyphSet()
    glyf = newTable("glyf")
    glyf.glyphOrder = font.getGlyphOrder()
    glyf.glyphs = {}
    for name in glyf.glyphOrder:
        pen = TTGlyphPen(glyph_set)
        # reverse_direction: glyf uses the opposite contour winding from CFF.
        glyph_set[name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        glyf.glyphs[name] = pen.glyph()
    font["glyf"] = glyf
    for g in glyf.glyphs.values():
        g.recalcBounds(glyf)  # maxp.recalc reads each glyph's xMin/etc.
    font["loca"] = newTable("loca")  # rebuilt from glyf on compile

    maxp = font["maxp"]
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    for attr in ("maxTwilightPoints", "maxStorage", "maxFunctionDefs",
                 "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions",
                 "maxComponentElements", "maxComponentDepth", "maxPoints",
                 "maxContours", "maxCompositePoints", "maxCompositeContours"):
        setattr(maxp, attr, 0)
    maxp.recalc(font)

    if "post" in font:
        font["post"].formatType = 3.0  # no glyph names → smaller file
    for tag in ("CFF ", "VORG"):
        if tag in font:
            del font[tag]
    font.sfntVersion = "\x00\x01\x00\x00"
    return font


def recenter_glyphs_h(font):
    """Center each glyph's ink within a uniform em-wide advance.

    Material Icons cells aren't all symmetric, so a glyph can sit off-center in
    its advance box. The watch centers a TEXT widget by ADVANCE, so an off-center
    ink reads as a shifted icon. Recentering the ink here makes advance-centering
    (device) and bbox-centering (PIL previews) agree — the icon looks centered."""
    upm = font["head"].unitsPerEm
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    for name in glyf.glyphOrder:
        g = glyf[name]
        if getattr(g, "numberOfContours", 0) <= 0:
            continue
        g.recalcBounds(glyf)
        dx = round(upm / 2 - (g.xMin + g.xMax) / 2)
        if dx:
            g.coordinates.translate((dx, 0))
            g.recalcBounds(glyf)
        hmtx[name] = (upm, g.xMin)  # advance = em, so text_size sets the icon size
    return font


def remap_codepoints(font, remap):
    for table in font["cmap"].tables:
        if table.isUnicode():
            for old, new in remap.items():
                table.cmap[new] = table.cmap.pop(old)
    return font


def main():
    if not os.path.exists(SRC):
        print(f"downloading {SRC_URL}")
        urllib.request.urlretrieve(SRC_URL, SRC)

    font = remap_codepoints(recenter_glyphs_h(otf_to_ttf(subset_otf(SRC, UNICODES))), CODEPOINT_REMAP)

    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    out = TTFont(buf)
    cmap = out.getBestCmap()
    assert "glyf" in out and out.sfntVersion == "\x00\x01\x00\x00", "not a glyf TTF"
    expected = [CODEPOINT_REMAP.get(u, u) for u in UNICODES]
    missing = [hex(u) for u in expected if u not in cmap]
    assert not missing, f"missing glyphs: {missing}"
    print(f"OK: glyf TTF, {len(cmap)} glyphs")

    data = buf.getvalue()
    for path in OUTPUTS:
        with open(path, "wb") as fh:
            fh.write(data)
        print(f"wrote {len(data)} bytes -> {os.path.relpath(path, BASE)}")


if __name__ == "__main__":
    main()
