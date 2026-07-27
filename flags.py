# -*- coding: utf-8 -*-
"""
flags.py

Steaguri de tara, ca SVG simplificat, incluse direct in cod — fara nicio
dependenta de un CDN extern (care ar putea fi blocat de un firewall
corporate, sau indisponibil la un moment dat).

De ce SVG si nu emoji: Windows nu are glife de steag in fontul sau de emoji
si afiseaza literele brute din spatele codului Unicode (ex. "DE" in loc de
steagul Germaniei) — o limitare a sistemului de operare, nu ceva reparabil
din cod. SVG-ul se randeaza identic pe orice sistem si browser.

Fiecare steag e o reprezentare simplificata (culori si proportii oficiale,
fara steme/embleme detaliate), suficienta pentru identificare vizuala rapida
intr-o interfata mica.

FLAG_INFO: cheie (engleza SAU romana, litere mici) -> (svg_markup, cod_3_litere)
"""

_VB = 'viewBox="0 0 90 60"'

_germany = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="90" height="20" fill="#000"/><rect y="20" width="90" height="20" fill="#DD0000"/><rect y="40" width="90" height="20" fill="#FFCE00"/></svg>'

_belgium = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="30" height="60" fill="#000"/><rect x="30" width="30" height="60" fill="#FDDA24"/><rect x="60" width="30" height="60" fill="#EF3340"/></svg>'

_france = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="30" height="60" fill="#0055A4"/><rect x="30" width="30" height="60" fill="#fff"/><rect x="60" width="30" height="60" fill="#EF4135"/></svg>'

_italy = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="30" height="60" fill="#009246"/><rect x="30" width="30" height="60" fill="#fff"/><rect x="60" width="30" height="60" fill="#CE2B37"/></svg>'

_romania = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="30" height="60" fill="#002B7F"/><rect x="30" width="30" height="60" fill="#FCD116"/><rect x="60" width="30" height="60" fill="#CE1126"/></svg>'

_netherlands = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="90" height="20" fill="#AE1C28"/><rect y="20" width="90" height="20" fill="#fff"/><rect y="40" width="90" height="20" fill="#21468B"/></svg>'

_portugal = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="90" height="60" fill="#FF0000"/><rect width="36" height="60" fill="#046A38"/></svg>'

_spain = f'<svg xmlns="http://www.w3.org/2000/svg" {_VB}><rect width="90" height="60" fill="#AA151B"/><rect y="15" width="90" height="30" fill="#F1BF00"/></svg>'

_greece = f'''<svg xmlns="http://www.w3.org/2000/svg" {_VB}>
<rect width="90" height="60" fill="#0D5EAF"/>
<rect y="6.7" width="90" height="6.7" fill="#fff"/>
<rect y="20" width="90" height="6.7" fill="#fff"/>
<rect y="33.3" width="90" height="6.7" fill="#fff"/>
<rect y="46.7" width="90" height="6.7" fill="#fff"/>
<rect width="34" height="34" fill="#0D5EAF"/>
<rect x="13.6" width="6.8" height="34" fill="#fff"/>
<rect y="13.6" width="34" height="6.8" fill="#fff"/>
</svg>'''

_turkey = f'''<svg xmlns="http://www.w3.org/2000/svg" {_VB}>
<rect width="90" height="60" fill="#E30A17"/>
<circle cx="34" cy="30" r="14" fill="#fff"/>
<circle cx="39" cy="30" r="11.5" fill="#E30A17"/>
<polygon points="52,30 46,26.5 47.8,32.8 42.5,28.5 49,28.7" fill="#fff"/>
</svg>'''

_england = f'''<svg xmlns="http://www.w3.org/2000/svg" {_VB}>
<rect width="90" height="60" fill="#fff"/>
<rect x="37" width="16" height="60" fill="#CE1124"/>
<rect y="22" width="90" height="16" fill="#CE1124"/>
</svg>'''

_scotland = f'''<svg xmlns="http://www.w3.org/2000/svg" {_VB}>
<rect width="90" height="60" fill="#005EB8"/>
<polygon points="0,0 8,0 90,54 90,60 82,60 0,6" fill="#fff"/>
<polygon points="82,0 90,0 90,6 8,60 0,60 0,54" fill="#fff"/>
</svg>'''

FLAG_INFO = {
    "germany": (_germany, "GER"), "germania": (_germany, "GER"),
    "belgium": (_belgium, "BEL"), "belgia": (_belgium, "BEL"),
    "france": (_france, "FRA"), "franta": (_france, "FRA"),
    "italy": (_italy, "ITA"), "italia": (_italy, "ITA"),
    "romania": (_romania, "ROU"),
    "netherlands": (_netherlands, "NED"), "olanda": (_netherlands, "NED"),
    "portugal": (_portugal, "POR"), "portugalia": (_portugal, "POR"),
    "spain": (_spain, "ESP"), "spania": (_spain, "ESP"),
    "greece": (_greece, "GRE"), "grecia": (_greece, "GRE"),
    "turkey": (_turkey, "TUR"), "turcia": (_turkey, "TUR"),
    "england": (_england, "ENG"), "anglia": (_england, "ENG"),
    "scotland": (_scotland, "SCO"), "scotia": (_scotland, "SCO"),
}


def flag_img_tag(country: str, width: int = 48) -> str:
    """
    Returneaza un tag <img> HTML gata de afisat cu st.markdown(...,
    unsafe_allow_html=True), cu steagul tarii date, incorporat direct ca
    SVG (fara nicio cerere de retea).
    """
    import base64

    entry = FLAG_INFO.get(country.strip().lower())
    if not entry:
        return ""

    svg, _ = entry
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{width}" style="border-radius:3px;" />'
