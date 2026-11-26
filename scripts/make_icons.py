#!/usr/bin/env python3
"""Génère les icônes de Poolette (Paulette qui nage, bonnet à fleurs rétro, sans texte).

Écrit icon.svg (logo du site et favicon) puis les PNG de l'écran d'accueil.
MOT garde le mot POOLETTE vectorisé (Bebas Neue, licence SIL OFL) pour une éventuelle version avec texte.
Dépendance pour les PNG : pip install cairosvg
"""
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "icons"

BONNET = "#F2A7B8"
FOND = "#0F4C6B"
EAU = "#2F86A6"
ECUME = "#8ED3C7"
TRAIT = "#12324A"
PEAU = "#F3C9A8"
TEXTE = "#FBF6EE"

# « POOLETTE » en Bebas Neue, contours vectorisés (largeur 3264, hauteur de capitale 700, unités de police)
MOT_L, MOT_H = 3264, 700
MOT = "M41 -700H203Q285 -700 326.0 -656.0Q367 -612 367 -527V-458Q367 -373 326.0 -329.0Q285 -285 203 -285H151V0H41ZM203 -385Q230 -385 243.5 -400.0Q257 -415 257 -451V-534Q257 -570 243.5 -585.0Q230 -600 203 -600H151V-385ZM459 -166V-534Q459 -618 502.0 -664.0Q545 -710 626 -710Q707 -710 750.0 -664.0Q793 -618 793 -534V-166Q793 -82 750.0 -36.0Q707 10 626 10Q545 10 502.0 -36.0Q459 -82 459 -166ZM683 -159V-541Q683 -610 626 -610Q569 -610 569 -541V-159Q569 -90 626 -90Q683 -90 683 -159ZM899 -166V-534Q899 -618 942.0 -664.0Q985 -710 1066 -710Q1147 -710 1190.0 -664.0Q1233 -618 1233 -534V-166Q1233 -82 1190.0 -36.0Q1147 10 1066 10Q985 10 942.0 -36.0Q899 -82 899 -166ZM1123 -159V-541Q1123 -610 1066 -610Q1009 -610 1009 -541V-159Q1009 -90 1066 -90Q1123 -90 1123 -159ZM1347 -700H1457V-100H1638V0H1347ZM1731 -700H2031V-600H1841V-415H1992V-315H1841V-100H2031V0H1731ZM2220 -600H2105V-700H2445V-600H2330V0H2220ZM2624 -600H2509V-700H2849V-600H2734V0H2624ZM2942 -700H3242V-600H3052V-415H3203V-315H3052V-100H3242V0H2942Z"

FLEUR = f"""<g id="fl">
<circle cx="0" cy="-10" r="9" fill="#fff" stroke="{TRAIT}" stroke-width="2.5"/>
<circle cx="9.5" cy="-3.1" r="9" fill="#fff" stroke="{TRAIT}" stroke-width="2.5"/>
<circle cx="5.9" cy="8.1" r="9" fill="#fff" stroke="{TRAIT}" stroke-width="2.5"/>
<circle cx="-5.9" cy="8.1" r="9" fill="#fff" stroke="{TRAIT}" stroke-width="2.5"/>
<circle cx="-9.5" cy="-3.1" r="9" fill="#fff" stroke="{TRAIT}" stroke-width="2.5"/>
<circle cx="0" cy="0" r="5.5" fill="#F6C945" stroke="{TRAIT}" stroke-width="2.5"/>
</g>"""

PAULETTE = f"""<ellipse cx="0" cy="30" rx="95" ry="112" fill="{PEAU}" stroke="{TRAIT}" stroke-width="4"/>
<path d="M-105 62 C-122 -40 -80 -152 0 -152 C80 -152 122 -40 105 62 C96 74 80 70 78 52 C70 2 40 -20 0 -22 C-40 -20 -70 2 -78 52 C-80 70 -96 74 -105 62 Z" fill="{BONNET}" stroke="{TRAIT}" stroke-width="4"/>
<use href="#fl" transform="translate(-66 -96) scale(1.45)"/>
<use href="#fl" transform="translate(2 -122) scale(1.25)"/>
<use href="#fl" transform="translate(66 -94) scale(1.45)"/>
<use href="#fl" transform="translate(-92 -6) scale(0.95)"/>
<use href="#fl" transform="translate(92 -6) scale(0.95)"/>
<path d="M-66 30 L-104 22" stroke="{TRAIT}" stroke-width="7" stroke-linecap="round"/>
<path d="M66 30 L104 22" stroke="{TRAIT}" stroke-width="7" stroke-linecap="round"/>
<ellipse cx="-36" cy="30" rx="30" ry="21" fill="{ECUME}" stroke="{TRAIT}" stroke-width="4"/>
<ellipse cx="36" cy="30" rx="30" ry="21" fill="{ECUME}" stroke="{TRAIT}" stroke-width="4"/>
<path d="M-6 28 Q0 22 6 28" fill="none" stroke="{TRAIT}" stroke-width="4"/>
<circle cx="-36" cy="32" r="6" fill="{TRAIT}"/>
<circle cx="36" cy="32" r="6" fill="{TRAIT}"/>
<path d="M-460 74 q25 -14 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 V400 H-260 Z" fill="{EAU}"/>
<path d="M-460 74 q25 -14 50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0 t50 0" fill="none" stroke="{ECUME}" stroke-width="5" stroke-linecap="round"/>
<circle cx="132" cy="36" r="8" fill="none" stroke="{ECUME}" stroke-width="3"/>
<circle cx="150" cy="8" r="5" fill="none" stroke="{ECUME}" stroke-width="3"/>
<circle cx="-136" cy="28" r="6" fill="none" stroke="{ECUME}" stroke-width="3"/>"""


# Paulette agrandie et arrondie : élargie (SX) plus que haute (SY), sans le mot.
SX, SY, CY = 1.85, 1.52, 294.5   # échelle horizontale, verticale, centre vertical (repère 512)
NIVEAU_EAU = 408.8               # hauteur de la ligne d'eau dans le repère 512


def paulette_ronde():
    """Le dessin, avec fleurs et pupilles compensées pour rester rondes malgré l'élargissement."""
    k = SY / SX
    d = PAULETTE
    d = re.sub(r'(<use href="#fl" transform="translate\([^)]*\) scale\()([\d.]+)\)',
               lambda m: f"{m.group(1)}{float(m.group(2)) * k:.3f} {m.group(2)})", d)
    d = re.sub(r'<circle cx="(-?\d+)" cy="32" r="6" fill="([^"]+)"/>',
               lambda m: f'<ellipse cx="{m.group(1)}" cy="32" rx="{6 * k:.2f}" ry="6" fill="{m.group(2)}"/>', d)
    d = re.sub(r'<circle cx="[-\d]+" cy="\d+" r="\d+" fill="none"[^>]*/>\n?', "", d)  # pas de bulles
    d = d.replace('stroke-width="4"', 'stroke-width="3.5"')
    return d.replace("M-460 74 ", f"M-460 {(NIVEAU_EAU - CY) / SY:.1f} ")


def svg(full_bleed=False, zoom=1.0):
    """full_bleed : carré plein (iOS et Android arrondissent eux-mêmes). zoom < 1 : zone de sécurité."""
    rx = 0 if full_bleed else 112
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<title>Poolette</title>
<defs>
{FLEUR}
<clipPath id="c"><rect width="512" height="512" rx="{rx}"/></clipPath>
</defs>
<g clip-path="url(#c)">
<rect width="512" height="512" fill="{FOND}"/>
<g transform="translate(256 256) scale({zoom}) translate(-256 -256)">
<g transform="translate(256 {CY}) scale({SX} {SY})">
{paulette_ronde()}
</g>
</g>
</g>
</svg>
"""


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "icon.svg").write_text(svg(), encoding="utf-8")
    print("écrit icon.svg")
    import cairosvg
    for name, size, full, zoom in (("icon-192.png", 192, False, 1.0),
                                   ("icon-512.png", 512, False, 1.0),
                                   ("icon-maskable-512.png", 512, True, 0.8),
                                   ("apple-touch-icon.png", 180, True, 0.9)):
        cairosvg.svg2png(bytestring=svg(full, zoom).encode(), write_to=str(OUT / name),
                         output_width=size, output_height=size)
        print("écrit", name)
