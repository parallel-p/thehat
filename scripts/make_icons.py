# -*- coding: utf-8 -*-
"""Generate every icon the site and the PWA ask for, in both themes.

    python -m scripts.make_icons

The source of truth is `assets/icon-hat.png`: the hat alone, on alpha. Every
file below is composed from it, so the icons cannot drift apart — change the
hat, run this, commit what it writes.

Two things this does that a plain resize would not:

*Colour follows the theme.* The hat is re-inked onto a ramp built from the
theme's own rose (`--slip-rose` on felt, `--rose-deep` on porcelain) rather
than being pasted at its original pink, which would come out as a washed
stain on a light background. The ramp keeps the shading: the hat's own
luminance picks the point on it, so the crown still turns and the brim still
catches light.

*The mark fills the tile.* The render it came from left half the frame empty,
which at 16px is a hat four pixels tall. Here the hat is laid out to a fixed
fraction of the tile, and the maskable icon gets its own smaller fraction so
that Android's circle crop cannot take the brim off.

Light and dark are separate files because that is the only way a browser can
choose between them — `<link rel="icon" media="...">`. A web app manifest has
no equivalent, so the PWA gets the dark tile, which is what its
`background_color` and `theme_color` already are.
"""

import os

from PIL import Image
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(HERE, "assets", "icon-hat.png")

# The two papers and the two roses, straight out of hat.css.
THEMES = {
    "dark":  {"paper": (0x17, 0x25, 0x1D), "rose": (0xE8, 0xA7, 0x9B)},
    "light": {"paper": (0xF4, 0xF5, 0xF1), "rose": (0x9C, 0x4A, 0x43)},
}

# How much of the tile's width the hat spans. The maskable icon keeps to the
# safe zone: Android may crop anything outside the middle 80%, and it crops to
# a circle, which takes the corners of the brim first.
FILL = 0.78
FILL_MASKABLE = 0.52


def ramp(rose):
    """Shadow -> rose -> highlight, as a 256-entry lookup on luminance.

    Hinged in the middle so the rose itself lands on the hat's mid tone. A
    straight shadow-to-highlight line would put the average of the two there
    instead, and the average of a dark rose and a pale one is mauve.
    """
    rose = np.array(rose, dtype=np.float32)
    shadow = rose * 0.72
    highlight = rose + (255 - rose) * 0.40
    t = np.linspace(0, 1, 256)[:, None]
    lower = shadow + (rose - shadow) * (t / 0.5)
    upper = rose + (highlight - rose) * ((t - 0.5) / 0.5)
    return np.where(t < 0.5, lower, upper)


def ink(hat, rose):
    """Re-ink the hat onto a theme's rose, keeping its own shading."""
    rgb = np.asarray(hat, dtype=np.float32)[:, :, :3]
    alpha = np.asarray(hat, dtype=np.float32)[:, :, 3]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    solid = alpha > 160
    lit = lum[solid]
    # The hat's own range, not 0..255: the art never goes near black, and
    # stretching it to the full ramp is what keeps the shading readable once
    # the tile is 16 pixels across.
    low, high = np.percentile(lit, 2), np.percentile(lit, 98)
    t = np.clip((lum - low) / max(high - low, 1e-3), 0, 1)
    # Along the matted edge the colour was divided by an alpha near zero, so
    # it is amplified noise — dark enough to have drawn a halo round the hat.
    # Only the alpha carries the edge; the colour under it is the mid tone.
    t = np.where(solid, t, np.median(t[solid]))
    inked = ramp(rose)[(t * 255).astype(np.uint8)]
    return Image.fromarray(
        np.dstack([inked, alpha]).astype(np.uint8), "RGBA")


def tile(hat, size, paper, fill):
    """One square icon: the hat centred on the theme's paper.

    Laid out at the art's own resolution and reduced to `size` in a single
    step. Composing at a fixed multiple of the target instead would mean
    enlarging the hat past its native width for the big icons and shrinking
    it back again, which costs sharpness at exactly the sizes that show it.

    Hamming, not Lanczos: reducing a rose hat on dark felt by seven times is
    the sharp edge Lanczos rings on, and its undershoot drew a band round the
    hat darker than the felt itself (measured: paper is luma 89, the band
    reached 83). Hamming has no negative lobe and reads just as sharp here.
    """
    big = round(hat.width / fill)
    canvas = Image.new("RGB", (big, big), paper)
    canvas.paste(hat, ((big - hat.width) // 2, (big - hat.height) // 2), hat)
    return canvas.resize((size, size), Image.HAMMING)


def write(image, *path):
    out = os.path.join(HERE, *path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    image.save(out)
    print(os.path.relpath(out, HERE), image.size)


def main():
    hat = Image.open(SOURCE).convert("RGBA")
    inked = {name: ink(hat, theme["rose"]) for name, theme in THEMES.items()}

    for name, theme in THEMES.items():
        paper = theme["paper"]
        # The tab. 16 and 32 are what browsers actually pick; 48 and 96 are
        # for the places that scale one up — bookmarks bars, Windows tiles.
        for size in (16, 32, 48, 96):
            write(tile(inked[name], size, paper, FILL),
                  "assets", "icons", "favicon-%d-%s.png" % (size, name))

    dark, paper = inked["dark"], THEMES["dark"]["paper"]

    # iOS home screen. Safari picks one icon and ignores the colour scheme,
    # so it gets the felt tile the app itself opens on.
    write(tile(dark, 180, paper, FILL), "assets", "icons", "apple-touch-icon.png")

    # The PWA.
    for size in (192, 512):
        write(tile(dark, size, paper, FILL), "static", "play", "icons",
              "hat-%d.png" % size)
    write(tile(dark, 512, paper, FILL_MASKABLE), "static", "play", "icons",
          "hat-maskable-512.png")

    # The fallback every browser knows how to ask for. One file, three sizes,
    # felt: an .ico cannot carry a media query, so it is the dark one.
    ico = tile(dark, 48, paper, FILL)
    ico.save(os.path.join(HERE, "favicon.ico"),
             sizes=[(16, 16), (32, 32), (48, 48)])
    print("favicon.ico 16/32/48")


if __name__ == "__main__":
    main()
