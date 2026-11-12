"""Build assets/*/fonts/icons-outlined.ttf — the icon set the complications use.

The watchface renders each complication's identifier as a TEXT widget in this
font (tintable, scalable, one glyph per datum). It merges the four data glyphs
from Google's "Material Icons Outlined" with the six weather glyphs from
"Material Symbols Outlined", and, crucially, converts the Material Icons CFF
outlines (the .otf Google ships) to glyf — ZeppOS renders glyf TTFs (sfntVersion
0x00010000); a CFF-flavoured .ttf shows nothing on device.

Glyphs (runtime chars: watchface/index.js for data, watchface/weather-icon.js
for weather):
    data     Material Icons Outlined
             e536 directions_walk · ef55 local_fire_department
             e1a4 battery_full     · e87d favorite
    weather  Material Symbols Outlined, instanced at FILL 0 / wght 400 / opsz 24
             e81a sunny · f172 partly_cloudy_day · f15c cloud
             f176 rainy · e2cd weather_snowy     · ebdb thunderstorm

Codepoints at U+F000 and above are re-mapped 0x1000 lower (f172 → e172, …): at
f1ad a glyph drew blank on the Active 2 and in the simulator, while the same
outline at a lower codepoint drew fine. Both sources are Apache 2.0 (see
LICENSE-material-icons.txt).

The Symbols source is committed as a small static subset
(MaterialSymbolsOutlined-weather-subset.ttf); when it is missing, the full
variable font is downloaded from a pinned commit and the subset rebuilt.

Run:  pip install fonttools  &&  python3 tools/make-icon-font.py
Only needs re-running when the glyph set changes; the output is committed.
"""
import io
import os
import tempfile
import urllib.request

from fontTools.ttLib import TTFont, newTable
from fontTools.subset import Subsetter, Options
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib import instancer

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "MaterialIconsOutlined-Regular.otf")
SRC_URL = (
    "https://github.com/google/material-design-icons/raw/"
    "f7bd4f25f3764883717c09a1fd867f560c9a9581/font/MaterialIconsOutlined-Regular.otf"
)
UNICODES = [0xE536, 0xEF55, 0xE1A4, 0xE87D]
SYMBOLS_SUBSET = os.path.join(BASE, "MaterialSymbolsOutlined-weather-subset.ttf")
SYMBOLS_URL = (
    "https://github.com/google/material-design-icons/raw/"
    "10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7/variablefont/"
    "MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.ttf"
)
SYMBOLS_AXES = {"FILL": 0, "GRAD": 0, "opsz": 24, "wght": 400}
SYMBOLS_UNICODES = [0xE81A, 0xF172, 0xF15C, 0xF176, 0xE2CD, 0xEBDB]
REMAP_FROM = 0xF000
REMAP_OFFSET = 0x1000
OUTPUTS = [
    os.path.join(BASE, "..", "assets", "466x466-amazfit-active-2-round", "fonts", "icons-outlined.ttf"),
    os.path.join(BASE, "..", "assets", "466x466-amazfit-gtr-4", "fonts", "icons-outlined.ttf"),
    os.path.join(BASE, "fonts", "icons-outlined.ttf"),  # source copy for render-assets.py previews
]
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


def build_symbols_subset(variable_path, out_path, unicodes, axes):
    font = instancer.instantiateVariableFont(TTFont(variable_path), axes)
    opts = Options()
    opts.glyph_names = True
    opts.notdef_outline = True
    ss = Subsetter(options=opts)
    ss.populate(unicodes=unicodes)
    ss.subset(font)
    font.save(out_path)


def add_symbols(font, path, unicodes):
    """Copy the given Material Symbols glyphs, scaled to font's em, into font."""
    src = TTFont(path)
    scale = font["head"].unitsPerEm / src["head"].unitsPerEm
    src_cmap = src.getBestCmap()
    src_glyphs = src.getGlyphSet()
    glyf = font["glyf"]
    order = font.getGlyphOrder()
    added = {}
    for u in unicodes:
        name = f"sym{u:04X}"
        pen = TTGlyphPen(None)
        src_glyphs[src_cmap[u]].draw(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        glyf.glyphs[name] = pen.glyph()
        glyf.glyphs[name].recalcBounds(glyf)
        font["hmtx"][name] = (font["head"].unitsPerEm, glyf.glyphs[name].xMin)
        order.append(name)
        added[u] = name
    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update(added)
    return font


def remap_high_codepoints(font):
    """Move every codepoint at REMAP_FROM or above REMAP_OFFSET lower."""
    remap = {}
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        for u in [u for u in table.cmap if u >= REMAP_FROM]:
            new = u - REMAP_OFFSET
            assert new not in table.cmap, f"remap of {u:#x} collides with {new:#x}"
            table.cmap[new] = table.cmap.pop(u)
            remap[u] = new
    return font, remap


def main():
    if not os.path.exists(SRC):
        print(f"downloading {SRC_URL}")
        urllib.request.urlretrieve(SRC_URL, SRC)

    if not os.path.exists(SYMBOLS_SUBSET):
        with tempfile.TemporaryDirectory() as tmp:
            variable = os.path.join(tmp, "MaterialSymbolsOutlined.ttf")
            print(f"downloading {SYMBOLS_URL}")
            urllib.request.urlretrieve(SYMBOLS_URL, variable)
            build_symbols_subset(variable, SYMBOLS_SUBSET, SYMBOLS_UNICODES, SYMBOLS_AXES)

    font = otf_to_ttf(subset_otf(SRC, UNICODES))
    font = recenter_glyphs_h(add_symbols(font, SYMBOLS_SUBSET, SYMBOLS_UNICODES))
    font, remap = remap_high_codepoints(font)

    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    out = TTFont(buf)
    cmap = out.getBestCmap()
    assert "glyf" in out and out.sfntVersion == "\x00\x01\x00\x00", "not a glyf TTF"
    expected = [remap.get(u, u) for u in UNICODES + SYMBOLS_UNICODES]
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
