"""
Pixel Frame — Palette Preview
A Streamlit app for previewing retro color palette effects on images.
"""

import io
import numpy as np
import streamlit as st
from PIL import Image, ImageEnhance

# ---------------------------------------------------------------------------
# Palette definitions  (mirror of palette-preview.html PALETTES array)
# ---------------------------------------------------------------------------

PALETTES = [
    {
        "name": "SPIRIT LENS",
        "desc": "Fatal Frame — somber blue shadow",
        "colors": [
            (8, 12, 20), (18, 28, 48), (28, 52, 90), (50, 82, 135),
            (85, 125, 170), (132, 172, 205), (185, 210, 232), (228, 238, 248),
        ],
        "defaults": dict(
            pixel_size=1, dither_mode="Floyd-Steinberg", dither_strength=0.75,
            saturation=0.35, hue_shift=-25, contrast=0.75, gamma=1.3,
            brightness=-15, chromatic_aberration=2,
            scanline_spacing=3, scanline_opacity=0.20,
        ),
    },
    {
        "name": "JADE SCREEN",
        "desc": "Game Boy DMG — 4-colour green",
        "colors": [
            (15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15),
        ],
        "defaults": dict(
            pixel_size=3, dither_mode="Bayer", dither_strength=0.65,
            saturation=1.8, hue_shift=15, contrast=1.1, gamma=0.85,
            brightness=10, chromatic_aberration=0,
            scanline_spacing=2, scanline_opacity=0.35,
        ),
    },
    {
        "name": "ONETT DAYS",
        "desc": "Earthbound — vibrant 16-bit SNES",
        "colors": [
            (0, 0, 0), (255, 255, 255), (232, 0, 0), (248, 184, 0),
            (0, 184, 0), (0, 88, 248), (136, 0, 248), (248, 56, 0),
            (0, 232, 216), (248, 120, 248), (80, 48, 0), (248, 200, 120),
            (168, 0, 32), (0, 40, 232), (120, 200, 0), (88, 88, 88),
        ],
        "defaults": dict(
            pixel_size=4, dither_mode="Bayer", dither_strength=0.45,
            saturation=2.0, hue_shift=0, contrast=1.4, gamma=0.9,
            brightness=15, chromatic_aberration=1,
            scanline_spacing=2, scanline_opacity=0.30,
        ),
    },
    {
        "name": "INFERNAL GRID",
        "desc": "Doom 2 — dark reds and browns",
        "colors": [
            (0, 0, 0), (26, 0, 0), (61, 0, 0), (139, 26, 26),
            (200, 74, 26), (139, 69, 19), (74, 48, 32), (42, 26, 10),
            (112, 112, 112), (192, 64, 0), (212, 192, 128), (255, 32, 0),
        ],
        "defaults": dict(
            pixel_size=5, dither_mode="Bayer", dither_strength=0.65,
            saturation=0.5, hue_shift=-15, contrast=1.5, gamma=1.2,
            brightness=-5, chromatic_aberration=3,
            scanline_spacing=3, scanline_opacity=0.50,
        ),
    },
    {
        "name": "SKETCH NOIR",
        "desc": "Hotel Dusk — 5-tone B&W",
        "colors": [
            (0, 0, 0), (56, 56, 56), (120, 120, 120), (190, 190, 190), (255, 255, 255),
        ],
        "defaults": dict(
            pixel_size=2, dither_mode="Floyd-Steinberg", dither_strength=0.85,
            saturation=0.0, hue_shift=0, contrast=1.6, gamma=1.15,
            brightness=5, chromatic_aberration=0,
            scanline_spacing=5, scanline_opacity=0.08,
        ),
    },
]

PALETTE_NAMES = [p["name"] for p in PALETTES]

BAYER_4X4 = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5],
], dtype=np.float32) / 16.0  # normalised 0..1

# ---------------------------------------------------------------------------
# Processing helpers
# ---------------------------------------------------------------------------

def _make_palette_image(colors):
    """Build a PIL 'P' image used as quantisation target."""
    flat = []
    for r, g, b in colors:
        flat += [r, g, b]
    flat += [0] * (768 - len(flat))
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(flat)
    return pal_img


def _preprocess(img_rgb: np.ndarray, brightness, contrast, gamma, saturation, hue_shift) -> np.ndarray:
    """Brightness -> contrast -> gamma -> saturation + hue (all vectorised)."""
    arr = img_rgb.astype(np.float32)

    if brightness != 0:
        arr = np.clip(arr + brightness, 0, 255)

    if contrast != 1.0:
        arr = np.clip((arr / 255.0 - 0.5) * contrast * 255.0 + 128.0, 0, 255)

    if gamma != 1.0:
        arr = np.clip(np.power(arr / 255.0, gamma) * 255.0, 0, 255)

    pil = Image.fromarray(arr.astype(np.uint8), "RGB")
    pil = ImageEnhance.Color(pil).enhance(saturation)
    arr = np.array(pil, dtype=np.float32)

    if hue_shift != 0:
        arr = _apply_hue_shift(arr, hue_shift)

    return np.clip(arr, 0, 255).astype(np.uint8)


def _apply_hue_shift(arr: np.ndarray, degrees: float) -> np.ndarray:
    """Shift hue of an HxWx3 float32 array by `degrees`."""
    r, g, b = arr[:, :, 0] / 255.0, arr[:, :, 1] / 255.0, arr[:, :, 2] / 255.0

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    h = np.zeros_like(r)
    mask = delta > 0
    m = mask & (cmax == r)
    h[m] = 60.0 * (((g[m] - b[m]) / delta[m]) % 6)
    m = mask & (cmax == g)
    h[m] = 60.0 * ((b[m] - r[m]) / delta[m] + 2)
    m = mask & (cmax == b)
    h[m] = 60.0 * ((r[m] - g[m]) / delta[m] + 4)

    h = (h + degrees) % 360

    s = np.where(cmax > 0, delta / cmax, 0)
    v = cmax

    hi = (h / 60).astype(int) % 6
    f = h / 60 - np.floor(h / 60)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)

    out = np.zeros_like(arr)
    for ch_idx, (v0, v1, v2, v3, v4, v5) in enumerate([
        (v, q, p, p, t, v),
        (t, v, v, q, p, p),
        (p, p, t, v, v, q),
    ]):
        ch = np.select(
            [hi == 0, hi == 1, hi == 2, hi == 3, hi == 4, hi == 5],
            [v0, v1, v2, v3, v4, v5],
        )
        out[:, :, ch_idx] = ch * 255.0

    return out


def _no_dither_quantize(pil_rgb: Image.Image, pal_img: Image.Image) -> Image.Image:
    return pil_rgb.quantize(palette=pal_img, dither=Image.Dither.NONE).convert("RGB")


def _bayer_quantize(pil_rgb: Image.Image, pal_img: Image.Image, strength: float,
                    colors) -> Image.Image:
    """Apply 4x4 Bayer ordered dithering then nearest-colour quantise."""
    arr = np.array(pil_rgb, dtype=np.float32)
    h, w = arr.shape[:2]

    tile_h = (h + 3) // 4
    tile_w = (w + 3) // 4
    bayer_tiled = np.tile(BAYER_4X4, (tile_h, tile_w))[:h, :w]
    threshold = (bayer_tiled[:, :, np.newaxis] - 0.5) * strength * 255.0

    arr_dithered = np.clip(arr + threshold, 0, 255).astype(np.uint8)
    dithered_pil = Image.fromarray(arr_dithered, "RGB")
    return dithered_pil.quantize(palette=pal_img, dither=Image.Dither.NONE).convert("RGB")


def _fs_quantize(pil_rgb: Image.Image, pal_img: Image.Image, strength: float) -> Image.Image:
    """Floyd-Steinberg via PIL; blend with no-dither for strength < 1."""
    full_fs = pil_rgb.quantize(palette=pal_img, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")
    if strength >= 1.0:
        return full_fs
    base = _no_dither_quantize(pil_rgb, pal_img)
    base_arr = np.array(base, dtype=np.float32)
    fs_arr   = np.array(full_fs, dtype=np.float32)
    blended  = np.clip(base_arr + (fs_arr - base_arr) * strength, 0, 255).astype(np.uint8)
    return Image.fromarray(blended, "RGB")


def _scanlines(pil: Image.Image, spacing: int, opacity: float) -> Image.Image:
    """Darken every Nth row to simulate CRT scanlines."""
    arr = np.array(pil, dtype=np.float32)
    arr[spacing - 1::spacing] *= (1.0 - opacity)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def _chromatic(pil: Image.Image, offset: int) -> Image.Image:
    """Shift R channel left and B channel right by `offset` pixels."""
    if offset == 0:
        return pil
    arr = np.array(pil, dtype=np.uint8)
    out = arr.copy()
    out[:, :, 0] = np.roll(arr[:, :, 0], -offset, axis=1)
    out[:, :, 2] = np.roll(arr[:, :, 2],  offset, axis=1)
    return Image.fromarray(out, "RGB")


@st.cache_data(show_spinner=False)
def process_image(
    img_bytes: bytes,
    colors_key: tuple,
    pixel_size: int,
    dither_mode: str,
    dither_strength: float,
    saturation: float,
    hue_shift: int,
    contrast: float,
    gamma: float,
    brightness: int,
    chromatic_aberration: int,
    scanline_spacing: int,
    scanline_opacity: float,
) -> Image.Image:
    """Full processing pipeline, cached on all parameters."""
    colors = [tuple(c) for c in colors_key]
    pal_img = _make_palette_image(colors)

    src = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    max_w = 640
    scale = min(1.0, max_w / src.width)
    dw = max(1, round(src.width * scale))
    dh = max(1, round(src.height * scale))
    src = src.resize((dw, dh), Image.LANCZOS)

    pre_arr = _preprocess(np.array(src), brightness, contrast, gamma, saturation, hue_shift)
    pre_pil = Image.fromarray(pre_arr, "RGB")

    gw = max(1, round(dw / pixel_size))
    gh = max(1, round(dh / pixel_size))
    small = pre_pil.resize((gw, gh), Image.LANCZOS)

    if dither_mode == "Bayer":
        quant = _bayer_quantize(small, pal_img, dither_strength, colors)
    elif dither_mode == "Floyd-Steinberg":
        quant = _fs_quantize(small, pal_img, dither_strength)
    else:
        quant = _no_dither_quantize(small, pal_img)

    out = quant.resize((dw, dh), Image.NEAREST)

    if scanline_spacing > 1 and scanline_opacity > 0:
        out = _scanlines(out, scanline_spacing, scanline_opacity)

    if chromatic_aberration > 0:
        out = _chromatic(out, chromatic_aberration)

    return out


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Pixel Frame — Palette Preview",
        page_icon="🎮",
        layout="wide",
    )

    st.title("🎮 Pixel Frame — Palette Preview")
    st.caption("Prototype tool for Project Retro Vision · Adjust sliders to explore each palette's character.")

    with st.sidebar:
        st.header("Palette")
        sel_name = st.radio(
            "Select palette",
            PALETTE_NAMES,
            format_func=lambda n: n,
            label_visibility="collapsed",
        )
        pal = next(p for p in PALETTES if p["name"] == sel_name)
        d = pal["defaults"]
        k = sel_name

        st.markdown(f"*{pal['desc']}*")
        st.divider()

        st.subheader("Pixel Grid")
        pixel_size = st.slider("Pixel size (px)", 1, 16, d["pixel_size"], key=f"{k}_px")

        st.subheader("Dithering")
        dither_mode = st.selectbox(
            "Mode",
            ["Bayer", "Floyd-Steinberg", "None"],
            index=["Bayer", "Floyd-Steinberg", "None"].index(d["dither_mode"]),
            key=f"{k}_dm",
        )
        dither_strength = st.slider("Strength", 0.0, 1.0, d["dither_strength"], 0.05, key=f"{k}_ds")

        st.subheader("Colour")
        saturation = st.slider("Saturation", 0.0, 3.0, d["saturation"], 0.05, key=f"{k}_sat")
        hue_shift  = st.slider("Hue shift (°)", -180, 180, d["hue_shift"], key=f"{k}_hue")

        st.subheader("Tone")
        brightness = st.slider("Brightness", -80, 80, d["brightness"], key=f"{k}_bri")
        contrast   = st.slider("Contrast",    0.1,  3.0, d["contrast"], 0.05, key=f"{k}_con")
        gamma      = st.slider("Gamma",        0.1,  3.0, d["gamma"], 0.05, key=f"{k}_gam")

        st.subheader("Effects")
        chromatic_aberration = st.slider("Chromatic aberration (px)", 0, 10, d["chromatic_aberration"], key=f"{k}_ca")
        scanline_spacing     = st.slider("Scanline spacing (rows)",   1, 10, d["scanline_spacing"], key=f"{k}_ss")
        scanline_opacity     = st.slider("Scanline opacity",          0.0, 1.0, d["scanline_opacity"], 0.01, key=f"{k}_so")

    uploaded = st.file_uploader(
        "Upload an image to preview",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        label_visibility="visible",
    )

    if uploaded is None:
        st.info("👆 Upload an image to get started.")
        st.subheader(f"{pal['name']} palette — {len(pal['colors'])} colours")
        swatch_html = "".join(
            f'<span title="rgb{c}" style="display:inline-block;width:32px;height:32px;'
            f'background:rgb{c};border:1px solid #333;margin:2px;border-radius:3px;"></span>'
            for c in pal["colors"]
        )
        st.markdown(swatch_html, unsafe_allow_html=True)
        return

    img_bytes = uploaded.read()

    with st.spinner("Processing…"):
        result = process_image(
            img_bytes=img_bytes,
            colors_key=tuple(tuple(c) for c in pal["colors"]),
            pixel_size=pixel_size,
            dither_mode=dither_mode,
            dither_strength=dither_strength,
            saturation=saturation,
            hue_shift=hue_shift,
            contrast=contrast,
            gamma=gamma,
            brightness=brightness,
            chromatic_aberration=chromatic_aberration,
            scanline_spacing=scanline_spacing,
            scanline_opacity=scanline_opacity,
        )

    col_orig, col_proc = st.columns(2)
    with col_orig:
        st.subheader("Original")
        orig_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        st.image(orig_pil, use_container_width=True)

    with col_proc:
        st.subheader(f"{pal['name']}")
        st.image(result, use_container_width=True)

    st.caption(
        f"**{pal['name']}** · {pixel_size}px · {dither_mode} {dither_strength:.2f} · "
        f"sat {saturation:.2f} · hue {hue_shift:+d}° · bri {brightness:+d} · "
        f"con {contrast:.2f} · γ {gamma:.2f} · CA {chromatic_aberration}px · "
        f"scanlines {scanline_spacing}px @ {scanline_opacity:.0%}"
    )

    st.subheader(f"Palette — {len(pal['colors'])} colours")
    swatch_html = "".join(
        f'<span title="rgb{c}" style="display:inline-block;width:32px;height:32px;'
        f'background:rgb{c};border:1px solid #333;margin:2px;border-radius:3px;"></span>'
        for c in pal["colors"]
    )
    st.markdown(swatch_html, unsafe_allow_html=True)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    st.download_button(
        "⬇ Download processed image",
        data=buf.getvalue(),
        file_name=f"{pal['name'].lower().replace(' ', '_')}_preview.png",
        mime="image/png",
    )


if __name__ == "__main__":
    main()
