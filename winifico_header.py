"""
Header Winifico pentru aplicația Streamlit.

Cum se folosește:
1. Copiază acest fișier lângă app.py (sau lipește funcția direct în app.py)
2. La începutul aplicației (imediat după st.set_page_config), apelează:

    from winifico_header import render_header
    render_header()

Necesită: streamlit
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from zoneinfo import ZoneInfo


def render_header():
    st.markdown(
        """
        <style>
        /* Ascunde header-ul default Streamlit ca bara noastră să fie chiar în vârf */
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* Aplica fontul Outfit in toata aplicatia, nu doar in logo */
        html, body, [class*="css"], .stApp {
            font-family: 'Outfit', sans-serif !important;
        }

        .winifico-header {
            width: 100%;
            background-color: #20241F;
            padding: 8px 32px;
            display: flex;
            justify-content: flex-start;
            align-items: center;
            box-sizing: border-box;
            margin: 0 0 1.5rem 0;
        }

        iframe {
            border: none !important;
            background: transparent !important;
        }

        .winifico-logo {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-family: 'Outfit', sans-serif;
        }

        .winifico-bracket {
            color: #5FBE84;
            font-weight: 700;
            font-size: 36px;
        }

        .winifico-wordmark {
            color: #F2F4F1;
            font-weight: 600;
            font-size: 40px;
            letter-spacing: 0.3px;
        }

        .winifico-version {
            color: #5FBE84;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 16px;
            letter-spacing: 0.5px;
            margin-left: 6px;
            align-self: flex-end;
            padding-bottom: 6px;
        }

        .winifico-col-header {
            background-color: #20241F;
            color: #F2F4F1;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 20px;
            letter-spacing: 0.3px;
            padding: 10px 16px;
            border-radius: 6px;
            margin-top: 8px;
            margin-bottom: 16px;
            box-sizing: border-box;
        }

        .winifico-moment-label {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 22px;
            margin: 10px 0 4px 0;
        }

        .winifico-thin-divider {
            height: 2px;
            background-color: #5FBE84;
            border: none;
            margin: 4px 0 14px 0;
        }

        /* Etichetele "1" / "X" / "2" de deasupra campurilor de cote:
           acelasi corp de font ca eticheta momentului (T24/TZero), alb
           bold pe fundal verde Winifico. */
        .winifico-odds-tag {
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 22px;
            color: #fff;
            background-color: #5FBE84;
            border-radius: 4px;
            text-align: center;
            padding: 2px 0;
            margin-bottom: 2px;
        }

        /* Butonul de salvare a pariului: fundal verde Winifico, text alb bold.
           Scopat strict la butonul de submit al formularului, ca sa nu
           afecteze alte butoane (ex. "Sterge definitiv"). */
        [data-testid="stFormSubmitButton"] button,
        button[kind="primary"] {
            background-color: #5FBE84 !important;
            color: #fff !important;
            font-weight: 700 !important;
            border: none !important;
        }
        </style>

        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )

    # Ceasul e primul element, deasupra logo-ului — un simplu bloc separat,
    # fara nicio incercare de suprapunere peste bara neagra (mult mai robust
    # decat variantele anterioare, care depindeau de structura interna,
    # imprevizibila, a Streamlit).
    components.html(
        """
        <div id="winifico-clock" style="
            color: #F2F4F1;
            font-family: 'Outfit', sans-serif;
            font-weight: 500;
            font-size: 15px;
            letter-spacing: 0.2px;
            text-align: right;
            white-space: nowrap;
            padding-right: 4px;
        "></div>
        <script>
        function winificoUpdateClock() {
            const el = document.getElementById('winifico-clock');
            if (!el) return;
            const now = new Date();
            const options = {
                timeZone: 'Europe/Bucharest',
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
                hour12: false
            };
            el.textContent = new Intl.DateTimeFormat('ro-RO', options).format(now) + ' (ROU)';
        }
        winificoUpdateClock();
        setInterval(winificoUpdateClock, 1000);
        </script>
        """,
        height=25,
    )

    st.markdown(
        """
        <div class="winifico-header">
            <div class="winifico-logo">
                <span class="winifico-bracket">[</span>
                <span class="winifico-wordmark">Winifico</span>
                <span class="winifico-bracket">]</span>
                <span class="winifico-version">1.5</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
