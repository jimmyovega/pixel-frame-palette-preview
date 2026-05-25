# Pixel Frame — Palette Preview

A Streamlit prototype tool for **Project Retro Vision** — upload any photo and see it rendered through five bespoke retro color palettes with real-time parameter control.

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser, upload an image, and start tweaking.

## Features

- **5 launch palettes** with individually tuned defaults
- **11 adjustable parameters** per palette, all persisted independently per session
- Side-by-side original vs. processed preview
- Color swatch display for each palette
- PNG download of the processed image
- Fully offline — no API calls, no cloud

## Palettes

| Palette | Inspiration | Colors | Character |
|---|---|---|---|
| SPIRIT LENS | Fatal Frame | 8 | Somber blue shadow, ghostly desaturation |
| JADE SCREEN | Game Boy DMG | 4 | Classic green phosphor, chunky pixels |
| ONETT DAYS | EarthBound / SNES | 16 | Vibrant 16-bit nostalgia, saturated brights |
| INFERNAL GRID | Doom 2 | 12 | Dark reds and browns, oppressive atmosphere |
| SKETCH NOIR | Hotel Dusk | 5 | Pencil-sketch B&W, high contrast linework |

## Parameters

| Parameter | Description |
|---|---|
| **Pixel size** | Grid block size in pixels (1–16). Larger = chunkier retro look |
| **Dither mode** | Bayer (ordered pattern), Floyd-Steinberg (error diffusion), or None |
| **Dither strength** | 0 = no dithering, 1 = full strength |
| **Saturation** | 0 = grayscale, 1 = original, >1 = boosted |
| **Hue shift** | Rotate all hues ±180° |
| **Brightness** | Additive offset applied before quantisation |
| **Contrast** | Scaled around midpoint (128); <1 = low contrast, >1 = high |
| **Gamma** | Tone curve correction; >1 = darker mids, <1 = lighter mids |
| **Chromatic aberration** | Pixel offset between R and B channels — VHS fringing effect |
| **Scanline spacing** | Darken every Nth row to simulate CRT scanlines |
| **Scanline opacity** | Darkness of the scanline overlay |

## Default Values

| Palette | px | Dither | Str | Sat | Hue | Bri | Con | γ | CA | SL sp | SL op |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPIRIT LENS | 1 | FS | 0.75 | 0.35 | -25° | -15 | 0.75 | 1.30 | 2 | 3 | 20% |
| JADE SCREEN | 3 | Bayer | 0.65 | 1.80 | +15° | +10 | 1.10 | 0.85 | 0 | 2 | 35% |
| ONETT DAYS | 4 | Bayer | 0.45 | 2.00 | 0° | +15 | 1.40 | 0.90 | 1 | 2 | 30% |
| INFERNAL GRID | 5 | Bayer | 0.65 | 0.50 | -15° | -5 | 1.50 | 1.20 | 3 | 3 | 50% |
| SKETCH NOIR | 2 | FS | 0.85 | 0.00 | 0° | +5 | 1.60 | 1.15 | 0 | 5 | 8% |

## Processing Pipeline

```
Upload → Pre-process (brightness → contrast → gamma → saturation → hue)
       → Downscale to pixel grid
       → Colour quantisation + dithering
       → Upscale nearest-neighbour
       → Scanline overlay
       → Chromatic aberration
       → Display
```

## Tech Stack

- **Streamlit** — UI framework
- **Pillow** — image quantisation (C-level Floyd-Steinberg)
- **NumPy** — vectorised pre-processing, Bayer dithering, scanlines, chromatic aberration

## Relation to Project Retro Vision

This tool is a design reference for the Flutter mobile app. Each palette's parameter set will be baked into the app's Dart code as the `config` object for each preset palette. The GLSL fragment shader (real-time preview) and Dart `image` package (capture processing) will replicate this pipeline on-device.
