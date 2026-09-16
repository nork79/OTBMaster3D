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
    "Forest": palette("""
        #14211c #e8f2e8 #1b2c24 #355241 #21382d #476451
        #192b22 #adc5b3 #2b4335 #486452 #3b5745 #789582
        #9dce8b #132219 #b6e2a3 #23392d #46604d #354a2a
        #e4c67c #20342a #3a5943 #334d3d #101b16 #55745d
    """),
    "Midnight Ocean": palette("""
        #0b1926 #e0f3ff #102535 #21495c #163344 #366174
        #102331 #9dbecd #1c3b4c #365b70 #295166 #688b9e
        #69d4db #08212b #9aeaf0 #163142 #30566b #204b57
        #edc986 #142c3c #23556a #284656 #08141f #426d80
    """),
    "Amethyst": palette("""
        #211a2c #f0e9fa #2a2138 #4c3b60 #322641 #655179
        #281f35 #c1afcf #3e304f #655178 #534065 #94809f
        #c4a0ee #251333 #ddc0ff #352841 #614b73 #4c355f
        #89d8bd #30253e #56406d #4a385c #191322 #78608e
    """),
    "Ember": palette("""
        #251b18 #f6ebe1 #30221d #604131 #3b2a22 #765340
        #2c201b #d0b5a3 #483226 #71503c #60412f #a28774
        #efa36b #29190f #ffc698 #3b2a21 #71503b #543721
        #bbd38b #36271f #69472e #533a2c #1b1411 #896047
    """),
    "Nordic Frost": palette("""
        #edf3f7 #263747 #dce7ef #bed4e4 #f7fbfd #aabfce
        #e4edf4 #506779 #d2e1ec #a5bdce #bfd5e4 #7c909f
        #326889 #ffffff #26516d #f7fbfd #afc5d4 #cee5ef
        #34755c #dbe7ef #b6d5e8 #bfceda #ffffff #8ca9bb
    """),
    "Warm Paper": palette("""
        #faf3e6 #41382b #ece1ce #dec9a7 #fffaf0 #c8b697
        #f2e8d7 #75664f #e8d9bd #c4af8b #dfccaa #9b8c74
        #80602b #ffffff #65491d #fffaf0 #cbbb9d #ecdfbc
        #4c7754 #ece2d0 #ddc79b #d6c7ac #fffdf7 #b4a080
    """),
    "High Contrast": palette("""
        #080808 #ffffff #101010 #303030 #141414 #b0b0b0
        #101010 #dddddd #242424 #aaaaaa #3b3b3b #999999
        #ffe66d #080808 #fff3ad #171717 #b0b0b0 #353219
        #67f5c5 #1c1c1c #364d68 #777777 #000000 #aaaaaa
    """),
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
