"""Interface palettes; the OpenGL board has its own independent colours."""

import re


# Roles correspond to the original Blue stylesheet's colours. Replacement is
# performed in one pass so shared colours never cascade into other roles.
BLUE_ROLES = {
    "#171b22": "window", "#e8eaf0": "text", "#1e242e": "chrome",
    "#384354": "menu_hover", "#242c38": "menu", "#414b5b": "border",
    "#1b212b": "sidebar", "#a3afc1": "muted", "#2b3543": "button",
    "#3b4759": "button_border", "#39475b": "hover", "#748095": "disabled",
    "#d5944a": "accent", "#161a20": "accent_text", "#e5a65c": "accent_hover",
    "#252e3a": "clock", "#364152": "clock_border", "#333127": "active_clock",
    "#80bfab": "waiting", "#202834": "alternate", "#364253": "selection",
    "#303a49": "divider", "#111720": "input", "#4a5668": "scrollbar",
}

_ROLES = tuple(BLUE_ROLES.values())


def palette(colours):
    values = colours.split()
    assert len(values) == len(_ROLES)
    return dict(zip(_ROLES,values))


THEMES = {
    "Light": palette("""
        #f4f5f7 #20242b #e8ebef #d5e4f5 #ffffff #bbc3ce
        #eef1f5 #536174 #e1e6ed #b8c2cf #d2ddeb #7b8492
        #2463a6 #ffffff #174e88 #ffffff #c2cad5 #dceafb
        #16745a #e5eaf1 #c5dbf4 #cbd2dc #ffffff #99a6b8
    """),
    "Dark": palette("""
        #181818 #ededed #202020 #3b3b3b #272727 #494949
        #202020 #b0b0b0 #303030 #484848 #414141 #858585
        #78b7ec #101820 #9bcdf6 #292929 #464646 #243748
        #84c9a6 #262626 #354c60 #383838 #141414 #595959
    """),
    "Blue": {role: colour for colour,role in BLUE_ROLES.items()},
    "Cyberpunk": palette("""
        #100d20 #f3eaff #19132d #49305d #241a38 #5c3e76
        #171127 #c4addd #30203f #64417b #49305d #897699
        #f4e34f #191323 #fff58a #251936 #563970 #3b2450
        #56f1d5 #21172f #573363 #3e2a52 #0c0917 #79528f
    """),
    "Pink/Lollipop": palette("""
        #fff2f7 #49243b #f9dfea #edbed6 #fff8fc #d5a2bd
        #fce7f1 #82576f #f4d3e5 #d4a0bc #ecc0d8 #a77f95
        #a92b70 #ffffff #8c205c #fff8fc #ddb0c9 #f5cee4
        #347e77 #f6ddea #e8b4d1 #e3bbd1 #fffafd #c990b1
    """),
}


def themed_stylesheet(base, name):
    colours = THEMES.get(name,THEMES["Blue"])
    return re.sub(r"#[0-9a-fA-F]{6}",
                  lambda match: colours[BLUE_ROLES[match.group().lower()]],base)
