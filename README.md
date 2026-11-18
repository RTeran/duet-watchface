<div align="center">

<img src="store/icon-240.png" width="120" alt="Duet icon">

# Duet

**Floating hands and a digital heart.**
A hybrid analog + digital watch face for Zepp OS.

![Zepp OS 3.0](https://img.shields.io/badge/Zepp_OS-3.0-ff6a00)
![Amazfit Active 2 Round](https://img.shields.io/badge/Amazfit-Active_2_Round-222)
![Amazfit GTR 4](https://img.shields.io/badge/Amazfit-GTR_4-222)
![Version](https://img.shields.io/badge/version-1.1.2-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

<img src="store/preview-animated.gif" width="360" alt="Duet cycling through its color themes, complications and Always-On mode">

</div>

---

## Why Duet

Duet pairs two ways of telling time on one dial. Two short, floating hands sweep around the edge, while large digital hours and minutes sit in the center. You read the time at a glance either way — and three small round badges keep your day's data in view.

## Gallery

<table>
  <tr>
    <td align="center"><img src="store/preview-champagne.png" width="240" alt="Champagne theme"><br><sub><b>Champagne</b> (default)</sub></td>
    <td align="center"><img src="store/preview-emerald.png" width="240" alt="Emerald theme"><br><sub><b>Emerald</b></sub></td>
    <td align="center"><img src="store/preview-sapphire.png" width="240" alt="Sapphire theme"><br><sub><b>Sapphire</b></sub></td>
  </tr>
</table>

### Always-On Display

<img src="store/preview-aod.png" width="240" alt="Always-On Display">

A dimmed, gray version with only the hands and the digits — easy on the battery, still easy to read.

## Features

- **Hybrid time** — analog hands and big digital digits on the same dial
- **8 color themes** — the accent tints the minute hand and the digits
- **3 editable complications** — left, right and bottom badges with progress rings
- **Live weather** — the weather badge shows the current temperature and a condition icon
- **Always-On Display** and **lockscreen** support
- **Everything set on the watch** — long-press the face to edit; no companion app

## Color themes

<table>
  <tr>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-champagne.png" width="90" alt="Champagne"><br><sub>Champagne</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-rose.png" width="90" alt="Rose Gold"><br><sub>Rose Gold</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-copper.png" width="90" alt="Copper"><br><sub>Copper</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-amethyst.png" width="90" alt="Amethyst"><br><sub>Amethyst</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-sapphire.png" width="90" alt="Sapphire"><br><sub>Sapphire</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-turquoise.png" width="90" alt="Turquoise"><br><sub>Turquoise</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-emerald.png" width="90" alt="Emerald"><br><sub>Emerald</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-color-ivory.png" width="90" alt="Ivory"><br><sub>Ivory</sub></td>
  </tr>
</table>

## Complications

Each of the three slots (left, right, bottom) can show any of these:

<table>
  <tr>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-date.png" width="72" alt="Date"><br><sub>Date</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-battery.png" width="72" alt="Battery"><br><sub>Battery</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-steps.png" width="72" alt="Steps"><br><sub>Steps</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-calories.png" width="72" alt="Calories"><br><sub>Calories</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-hr.png" width="72" alt="Heart rate"><br><sub>Heart rate</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-weather.png" width="72" alt="Weather"><br><sub>Weather</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-pai.png" width="72" alt="PAI"><br><sub>PAI</sub></td>
    <td align="center"><img src="assets/466x466-amazfit-active-2-round/edit/preview-comp-empty.png" width="72" alt="None"><br><sub>None</sub></td>
  </tr>
</table>

Defaults: **Date** on the left, **Battery** on the right, **Steps** at the bottom.

## Supported devices

| Device | Screen | Target |
| --- | --- | --- |
| Amazfit Active 2 Round | 466 × 466 | `466x466-amazfit-active-2-round` |
| Amazfit GTR 4 | 466 × 466 | `466x466-amazfit-gtr-4` |

Requires Zepp OS API level 3.0.

## Install

Install **Duet** from the watch face store in the Zepp app.

## Build from source

You need the [Zeus CLI](https://docs.zepp.com/docs/guides/tools/cli/) (`npm i -g @zeppos/zeus-cli`).

```bash
git clone https://github.com/RTeran/duet-watchface.git
cd duet-watchface

zeus dev       # run it in the Zepp OS simulator
zeus preview   # install it on your watch through a QR code in the Zepp app
zeus build     # write the .zab package to dist/
```

### Regenerating the images

The images under `assets/` and `store/` are rendered by Python scripts, not drawn by hand. They need Python 3 with Pillow and fontTools (`pip install pillow fonttools`).

```bash
python3 tools/render-assets.py         # dial, hands, rings and edit-mode previews
python3 tools/render-store-assets.py   # store icon, screenshots and animated GIF
python3 tools/make-icon-font.py        # icon font for the complication badges
```

### Tests

```bash
node --test test/*.mjs
```

## Project structure

```
app.json                 app manifest: targets, permissions, version
watchface/index.js       the watch face: layout, themes, edit groups, data
watchface/weather-icon.js  maps the weather code to an icon glyph
assets/<target>/         per-device images and fonts
tools/                   image and font generators
store/                   store icon, screenshots and GIF (466 px and 360 px)
test/                    unit tests (node:test)
```

## Credits

- [Jost](https://github.com/indestructible-type/Jost) and [Rubik](https://github.com/googlefonts/rubik) — SIL Open Font License 1.1
- [Material Icons](https://github.com/google/material-design-icons) and [Material Symbols](https://github.com/google/material-design-icons) — Apache License 2.0

The license texts ship in the repo: the OFL files in `assets/*/fonts/` and the Apache License in `tools/LICENSE-material-icons.txt`.

## License

The code is released under the [MIT License](LICENSE). Fonts keep their own licenses (see [Credits](#credits)).
