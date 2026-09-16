"""Board colour presets shared by UI menus and the game controller."""


def rgb(value):
    return tuple(int(value[i:i+2],16)/255 for i in (0,2,4))


BOARD_COLOR_THEMES = {
    "Wood": ((.77,.68,.53),(.31,.20,.12),(.22,.11,.05)),
    "Tournament Green": ((.92,.90,.78),(.30,.48,.34),(.16,.22,.14)),
    "Blue": ((.88,.90,.92),(.31,.43,.57),(.14,.18,.24)),
    "Grey": ((.82,.82,.82),(.35,.35,.35),(.18,.18,.18)),
    **{name:tuple(rgb(c) for c in colours.split()) for name,colours in {
        "Ivory & Onyx": "eeeae0 30343b 171b22",
        "Walnut & Maple": "e7cea2 745035 402c21",
        "Rosewood": "efd8b7 803f45 41262d",
        "Sage": "e5e7d0 71896b 354a39",
        "Ocean": "dceaf0 387a94 193b50",
        "Amethyst": "e9dff0 88689e 443151",
        "Terracotta": "f0dcc1 b16d50 603e32",
        "Slate & Silver": "dce1e5 59697a 2d3846",
        "Honey & Espresso": "f2d392 845c33 3c2b1f",
        "Blush": "f7e5e8 b5748b 633e50",
    }.items()},
}
