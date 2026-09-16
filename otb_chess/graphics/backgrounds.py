"""Small, procedural backdrops; no external image assets are required."""

import math
import random

from PIL import Image
from OpenGL.GL import (
    GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE, GL_RGB,
    GL_UNSIGNED_BYTE, glGenTextures, glBindTexture, glTexParameteri, glTexImage2D,
)


BACKGROUNDS = {
    "solid": "Solid colour",
    "slate": "Slate gradient",
    "warm": "Warm grey gradient",
    "midnight": "Midnight blue",
    "studio": "Studio glow",
    "felt": "Soft felt",
    "paper": "Warm paper",
    "match": "Match board",
}


def background_image(style, board_color):
    palettes = {
        "slate": ((24, 29, 37), (57, 67, 79)),
        "warm": ((36, 32, 30), (76, 69, 62)),
        "midnight": ((12, 19, 33), (29, 45, 65)),
        "studio": ((19, 22, 28), (66, 73, 84)),
        "felt": ((23, 39, 34), (37, 57, 48)),
        "paper": ((116, 109, 96), (144, 137, 122)),
        "match": (tuple(12 + c * 24 for c in board_color),
                  tuple(32 + c * 65 for c in board_color)),
    }
    low, high = palettes[style]
    rng = random.Random(17)
    size = 256
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            if style in ("studio", "match"):
                mix = math.exp(-3 * (((x / 255 - .5) / .65) ** 2
                                    + ((y / 255 - .48) / .65) ** 2))
            else:
                mix = 1 - y / 255
            grain = rng.uniform(-2, 2) if style in ("felt", "paper") else 0
            pixels.extend(max(0, min(255, round(a + (b-a)*mix + grain)))
                          for a,b in zip(low, high))
    return Image.frombytes("RGB", (size, size), bytes(pixels))


def upload_background(style, board_color):
    image = background_image(style, board_color).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    texture = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, texture)
    for parameter in (GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER):
        glTexParameteri(GL_TEXTURE_2D, parameter, GL_LINEAR)
    for parameter in (GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T):
        glTexParameteri(GL_TEXTURE_2D, parameter, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, *image.size, 0, GL_RGB,
                 GL_UNSIGNED_BYTE, image.tobytes())
    return texture, image.size
