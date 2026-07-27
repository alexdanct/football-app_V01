# -*- coding: utf-8 -*-
"""
app.py

Interfata Streamlit a aplicatiei de analiza fotbalistica.
Layout pe 4 coloane:
    1. Competitie — selectare competitie
    2. Analiza    — cote curente (introduse manual) + istoricul lor
    3. Predictie  — (deocamdata goala, structura de baza)
    4. Istoric    — (deocamdata goala, structura de baza)

Rulare locala:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd

from database import (
    create_tables, seed_initial_competitions, fetch_all_competitions, fetch_matches,
    fetch_teams_for_competition, insert_manual_odds, fetch_manual_odds, delete_manual_odds,
    set_bet_result, archive_all_active_bets, reset_all_bets,
)
from winifico_header import render_header
from flags import FLAG_INFO, flag_img_tag

st.set_page_config(
    page_title="Winifico 1.5",
    page_icon="⚽",
    layout="wide",
)

render_header()

# Ne asiguram ca baza de date exista si are competitiile initiale
create_tables()
seed_initial_competitions()

col_competitie, col_analiza, col_predictie, col_istoric = st.columns([1, 2, 2, 2])

# ============================================================
# COLOANA 1 — COMPETITIE
# ============================================================
with col_competitie:
    st.markdown('<div class="winifico-col-header">Competiție</div>', unsafe_allow_html=True)
    with st.container(border=True):

        competitions = fetch_all_competitions()

        if not competitions:
            st.warning("Nu exista inca nicio competitie in baza de date.")
            st.stop()

        # Cod de 3 litere afisat in text, luat din modulul flags.py.
        #
        # Nota: nu folosim emoji de steag in text, pentru ca Windows nu are
        # glife de steag in fontul sau de emoji si afiseaza literele brute din
        # spatele codului Unicode (ex. "DE" in loc de steagul Germaniei) — o
        # limitare a sistemului de operare, nu ceva ce se poate repara din cod.
        # Solutia robusta, care arata identic pe orice sistem: un steag SVG
        # inclus local (flags.py), afisat separat, sub selector.

        # Iconite generice (nu logo-uri oficiale, protejate prin drepturi de autor)
        # pentru turneele multinationale. Acestea NU sunt afectate de limitarea
        # Windows de mai sus — sunt emoji obisnuite (stea, trofeu, glob), nu
        # secvente de steag, deci se afiseaza corect peste tot.
        TOURNAMENT_ICONS = {
            "uefa champions league": "⭐",
            "uefa europa league": "🏆",
            "campionatul european (euro)": "🏆",
            "campionatul mondial": "🌍",
        }

        def build_label(c):
            name, comp_type, country = c["name"], c["type"], c.get("country")

            if comp_type == "club_league" and country:
                entry = FLAG_INFO.get(country.strip().lower())
                if entry:
                    _, code = entry
                    return f"({code}) {name}"

            icon = TOURNAMENT_ICONS.get(name.strip().lower())
            if icon:
                return f"{icon} {name} ({comp_type})"

            return f"{name} ({comp_type})"


        comp_labels = {build_label(c): c["id"] for c in competitions}
        comp_by_id = {c["id"]: c for c in competitions}

        selected_label = st.selectbox("Alege competitia", options=list(comp_labels.keys()))
        selected_id = comp_labels[selected_label]

        # Afisam steagul real al tarii (SVG inclus local, nu emoji), pentru
        # competitiile de club — sub selector, ca sa se vada indiferent de
        # sistemul de operare al utilizatorului.
        selected_country = comp_by_id[selected_id].get("country")
        if selected_country:
            img_tag = flag_img_tag(selected_country)
            if img_tag:
                st.markdown(img_tag, unsafe_allow_html=True)

        matches = fetch_matches(competition_id=selected_id)

        st.metric("Total meciuri in baza de date", len(matches))

        if matches:
            seasons = sorted({m["season"] for m in matches if m.get("season")})
            st.caption(f"Sezoane acoperite: {len(seasons)}")
            if seasons:
                st.caption(f"{seasons[0]} → {seasons[-1]}")
        else:
            st.info(
                "Nu exista inca meciuri importate pentru aceasta competitie.\n\n"
                "Foloseste `import_batch.py` pentru a importa date "
                "(vezi instructiunile din README.md)."
            )

        st.divider()

        # Buton de reset complet: sterge TOATE pariurile (Predictie + Istoric),
        # din toate competitiile. Confirmare in 2 pasi, ca sa nu se piarda
        # accidental istoricul cu un singur click gresit.
        if not st.session_state.get("confirm_reset"):
            if st.button("Default Reset", key="default_reset_button", type="primary"):
                st.session_state["confirm_reset"] = True
                st.rerun()
        else:
            st.warning("Sigur vrei sa stergi TOATE pariurile din Predictie si Istoric? Actiunea nu poate fi anulata.")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("Da, sterge tot", key="confirm_reset_yes"):
                    reset_all_bets()
                    st.session_state["confirm_reset"] = False
                    st.rerun()
            with rc2:
                if st.button("Anuleaza", key="confirm_reset_no"):
                    st.session_state["confirm_reset"] = False
                    st.rerun()

# ============================================================
# COLOANA 2 — ANALIZA
# ============================================================
with col_analiza:
    st.markdown('<div class="winifico-col-header">Analiză</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.caption(selected_label)

        known_teams = fetch_teams_for_competition(selected_id)

        with st.form("manual_odds_form", clear_on_submit=True, border=False):
            st.markdown("**Cote curente (introduse manual)**")

            if known_teams:
                home_team = st.selectbox("Echipa gazda", options=known_teams, key="home_team_select")
            else:
                home_team = st.text_input("Echipa gazda")

            if known_teams:
                away_team = st.selectbox("Echipa oaspete", options=known_teams, key="away_team_select")
            else:
                away_team = st.text_input("Echipa oaspete")

            match_date = st.date_input("Data meciului")

            st.markdown("**Momente cote**")

            st.markdown('<p class="winifico-moment-label">T24</p>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<p class="winifico-odds-tag">1</p>', unsafe_allow_html=True)
                odds_home_t24 = st.number_input("Cota 1", min_value=1.01, step=0.01, format="%.2f",
                                                 key="odds_home_t24", label_visibility="collapsed")
            with c2:
                st.markdown('<p class="winifico-odds-tag">X</p>', unsafe_allow_html=True)
                odds_draw_t24 = st.number_input("Cota X", min_value=1.01, step=0.01, format="%.2f",
                                                 key="odds_draw_t24", label_visibility="collapsed")
            with c3:
                st.markdown('<p class="winifico-odds-tag">2</p>', unsafe_allow_html=True)
                odds_away_t24 = st.number_input("Cota 2", min_value=1.01, step=0.01, format="%.2f",
                                                 key="odds_away_t24", label_visibility="collapsed")

            st.markdown('<p class="winifico-moment-label">TZero</p>', unsafe_allow_html=True)
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown('<p class="winifico-odds-tag">1</p>', unsafe_allow_html=True)
                odds_home_t0 = st.number_input("Cota 1", min_value=1.01, step=0.01, format="%.2f",
                                                key="odds_home_t0", label_visibility="collapsed")
            with c5:
                st.markdown('<p class="winifico-odds-tag">X</p>', unsafe_allow_html=True)
                odds_draw_t0 = st.number_input("Cota X", min_value=1.01, step=0.01, format="%.2f",
                                                key="odds_draw_t0", label_visibility="collapsed")
            with c6:
                st.markdown('<p class="winifico-odds-tag">2</p>', unsafe_allow_html=True)
                odds_away_t0 = st.number_input("Cota 2", min_value=1.01, step=0.01, format="%.2f",
                                                key="odds_away_t0", label_visibility="collapsed")

            st.markdown('<p class="winifico-moment-label">Predictie</p>', unsafe_allow_html=True)
            r1, r2, r3 = st.columns(3)
            # Placeholder deocamdata — urmeaza sa fie inlocuit cu rezultatul
            # algoritmului de predictie (diferenta T24 vs TZero), cand acesta
            # va fi definit. Campurile sunt needitabile (disabled).
            with r1:
                st.markdown('<p class="winifico-odds-tag">1</p>', unsafe_allow_html=True)
                st.text_input("Cota 1", value="—", disabled=True, label_visibility="collapsed", key="result_home")
            with r2:
                st.markdown('<p class="winifico-odds-tag">X</p>', unsafe_allow_html=True)
                st.text_input("Cota X", value="—", disabled=True, label_visibility="collapsed", key="result_draw")
            with r3:
                st.markdown('<p class="winifico-odds-tag">2</p>', unsafe_allow_html=True)
                st.text_input("Cota 2", value="—", disabled=True, label_visibility="collapsed", key="result_away")

            st.markdown('<p class="winifico-moment-label">Alegerea ta</p>', unsafe_allow_html=True)
            pick_label_to_code = {"1 (Victorie gazde)": "1", "X (Egal)": "X", "2 (Victorie oaspeti)": "2"}
            pick_label = st.radio(
                "Pe ce pariezi?",
                options=list(pick_label_to_code.keys()),
                horizontal=True,
                index=None,
                label_visibility="collapsed",
                key="pick_selector",
            )

            submitted = st.form_submit_button("Salveaza pariul")

            source = st.text_input("Sursa (optional)", placeholder="ex. Superbet, 17 iulie")

            if submitted:
                if not home_team or not away_team:
                    st.error("Completeaza numele ambelor echipe inainte de a salva.")
                elif not pick_label:
                    st.error("Alege pe ce pariezi (1 / X / 2) inainte de a salva.")
                else:
                    pick_code = pick_label_to_code[pick_label]
                    insert_manual_odds(
                        competition_id=selected_id,
                        home_team=home_team,
                        away_team=away_team,
                        match_date=str(match_date),
                        snapshot="T24h",
                        odds_home=odds_home_t24,
                        odds_draw=odds_draw_t24,
                        odds_away=odds_away_t24,
                        source=source.strip() if source.strip() else "manual",
                        pick=pick_code,
                    )
                    insert_manual_odds(
                        competition_id=selected_id,
                        home_team=home_team,
                        away_team=away_team,
                        match_date=str(match_date),
                        snapshot="T0h",
                        odds_home=odds_home_t0,
                        odds_draw=odds_draw_t0,
                        odds_away=odds_away_t0,
                        source=source.strip() if source.strip() else "manual",
                        pick=pick_code,
                    )
                    st.success(f"Salvat: {home_team} vs {away_team}")
                    st.rerun()

        manual_entries = fetch_manual_odds(competition_id=selected_id)

        if manual_entries:
            with st.expander("Sterge o intrare gresita"):
                entry_labels = {
                    f"#{e['id']} — {e['home_team']} vs {e['away_team']} ({e['match_date']}, {e['snapshot']})": e["id"]
                    for e in manual_entries
                }
                entry_to_delete = st.selectbox("Alege intrarea de sters", options=list(entry_labels.keys()))
                if st.button("Sterge definitiv"):
                    delete_manual_odds(entry_labels[entry_to_delete])
                    st.success("Intrare stearsa.")
                    st.rerun()
        else:
            st.caption("Nu ai introdus inca nicio cota manual pentru aceasta competitie.")

# ============================================================
# COLOANA 3 — PREDICTIE
# ============================================================
with col_predictie:
    st.markdown('<div class="winifico-col-header">Predicție</div>', unsafe_allow_html=True)
    with st.container(border=True):

        # Pariurile se afiseaza din TOATE competitiile deodata (nu doar cea
        # selectata in coloana Competitie), in ordine cronologica dupa momentul
        # in care au fost salvate — indiferent de data meciului sau campionat.
        all_entries = fetch_manual_odds()

        RESULT_LABELS = {"1": "1 (Victorie gazde)", "X": "X (Egal)", "2": "2 (Victorie oaspeti)"}
        RESULT_CODES_BY_LABEL = {v: k for k, v in RESULT_LABELS.items()}

        def render_bet_card(bet, editable=True):
            """Afiseaza un card de pariu: competitie, echipe, cote 1/X/2, rezultat, status."""
            st.caption(bet["competition"])
            st.markdown(f"**{bet['home_team']} vs {bet['away_team']}** ({bet['match_date']})")

            b1, b2, b3 = st.columns(3)
            odds_by_code = {"1": bet["odds_home"], "X": bet["odds_draw"], "2": bet["odds_away"]}
            for col, code in zip((b1, b2, b3), ("1", "X", "2")):
                with col:
                    tag_text = f"{code} ✓" if bet["pick"] == code else code
                    st.markdown(f'<p class="winifico-odds-tag">{tag_text}</p>', unsafe_allow_html=True)
                    value = odds_by_code[code]
                    st.text_input(
                        code, value=f"{value:.2f}" if value is not None else "—",
                        disabled=True, label_visibility="collapsed", key=f"bet_odds_{bet['id']}_{code}",
                    )

            if editable:
                st.markdown('<p class="winifico-moment-label">Rezultat</p>', unsafe_allow_html=True)
                current_label = RESULT_LABELS.get(bet.get("actual_result"))
                result_label = st.selectbox(
                    "Rezultatul meciului", options=list(RESULT_LABELS.values()),
                    index=list(RESULT_LABELS.values()).index(current_label) if current_label else None,
                    placeholder="Alege rezultatul...", label_visibility="collapsed",
                    key=f"result_select_{bet['id']}",
                )

                if result_label and st.button("Salveaza rezultatul", key=f"save_result_{bet['id']}"):
                    set_bet_result(bet["id"], RESULT_CODES_BY_LABEL[result_label])
                    st.rerun()

            if bet.get("actual_result"):
                st.markdown('<p class="winifico-moment-label">Status pariu</p>', unsafe_allow_html=True)
                if bet["pick"] == bet["actual_result"]:
                    st.success("Castigator!")
                else:
                    st.error("Nasol, ghinion....")

        active_bets = sorted(
            (e for e in all_entries if e["snapshot"] == "T0h" and e.get("pick") and not e.get("archived")),
            key=lambda e: e["entered_at"],
        )

        if not active_bets:
            st.caption("Niciun pariu activ momentan.")
        else:
            from datetime import date
            st.markdown(f"**{date.today().isoformat()}**")
            st.markdown('<hr class="winifico-thin-divider" />', unsafe_allow_html=True)

            for bet in active_bets:
                render_bet_card(bet, editable=True)
                st.divider()

            if st.button("Salveaza istoric", key="save_history_button", type="primary"):
                archive_all_active_bets()
                st.rerun()

# ============================================================
# COLOANA 4 — ISTORIC
# ============================================================
with col_istoric:
    st.markdown('<div class="winifico-col-header">Istoric</div>', unsafe_allow_html=True)
    with st.container(border=True):

        archived_bets = [e for e in all_entries if e["snapshot"] == "T0h" and e.get("pick") and e.get("archived")]

        if not archived_bets:
            st.caption("Niciun istoric salvat inca.")
        else:
            # Gruparea in Istoric se face dupa sesiunea de arhivare (momentul
            # apasarii "Salveaza istoric"), nu dupa data meciului — ca sa
            # corespunda cu "ziua de lucru" in care ai plasat pariurile.
            sessions = sorted({e["archived_at"] for e in archived_bets}, key=lambda s: s or "", reverse=True)
            for session in sessions:
                session_day = session[:10] if session else "necunoscut"
                st.markdown(f"**{session_day}**")
                st.markdown('<hr class="winifico-thin-divider" />', unsafe_allow_html=True)

                session_bets = sorted(
                    (e for e in archived_bets if e["archived_at"] == session),
                    key=lambda e: e["entered_at"],
                )
                for bet in session_bets:
                    render_bet_card(bet, editable=False)
                    st.divider()

                # --- Acuratete predictie: procent rezultate corecte vs gresite ---
                # Se ia in calcul doar din pariurile care au deja un rezultat
                # introdus (actual_result) — cele fara rezultat nu intra la numarator
                # nici la numitor.
                resolved = [b for b in session_bets if b.get("actual_result")]
                correct = [b for b in resolved if b["pick"] == b["actual_result"]]

                st.markdown('<p class="winifico-moment-label">Acuratete predictie</p>', unsafe_allow_html=True)
                if resolved:
                    accuracy = len(correct) / len(resolved) * 100
                    st.metric(
                        "Acuratete",
                        f"{accuracy:.0f}%",
                        label_visibility="collapsed",
                        help=f"{len(correct)} corecte din {len(resolved)} pariuri cu rezultat cunoscut",
                    )
                    st.caption(f"{len(correct)} corecte din {len(resolved)} cu rezultat introdus")
                else:
                    st.caption("Niciun pariu din aceasta sesiune nu are inca un rezultat introdus.")
