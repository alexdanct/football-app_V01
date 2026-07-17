# -*- coding: utf-8 -*-
"""
app.py

Interfata Streamlit a aplicatiei de analiza fotbalistica.
Layout pe 3 coloane:
    1. Competitie — selectare competitie
    2. Analiza    — tabel de meciuri + grafic goluri pe sezon
    3. Predictie  — cote curente (introduse manual) + predictii viitoare

Modelul de predictie propriu-zis va fi adaugat intr-o etapa ulterioara;
deocamdata coloana Predictie contine doar cotele introduse manual, ca baza
pentru comparatie cand modelul va fi gata.

Rulare locala:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd

from database import (
    create_tables, seed_initial_competitions, fetch_all_competitions, fetch_matches,
    fetch_teams_for_competition, insert_manual_odds, fetch_manual_odds, delete_manual_odds,
)

st.set_page_config(
    page_title="Analiza Fotbalistica",
    page_icon="⚽",
    layout="wide",
)

# Ne asiguram ca baza de date exista si are competitiile initiale
create_tables()
seed_initial_competitions()

st.title("⚽ Analiza Fotbalistica — v1.0")

col_competitie, col_analiza, col_predictie = st.columns([1, 2, 2])

# ============================================================
# COLOANA 1 — COMPETITIE
# ============================================================
with col_competitie:
    st.header("🏆 Competitie")

    competitions = fetch_all_competitions()

    if not competitions:
        st.warning("Nu exista inca nicio competitie in baza de date.")
        st.stop()

    comp_labels = {
        f"{c['name']} ({c['type']})": c["id"] for c in competitions
    }

    selected_label = st.selectbox("Alege competitia", options=list(comp_labels.keys()))
    selected_id = comp_labels[selected_label]

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

# ============================================================
# COLOANA 2 — ANALIZA
# ============================================================
with col_analiza:
    st.header("📊 Analiza")
    st.caption(selected_label)

    if not matches:
        st.info("Selecteaza o competitie cu date importate, ca sa vezi analiza aici.")
    else:
        df = pd.DataFrame(matches)
        df = df.rename(columns={
            "competition": "Competitie",
            "season": "Sezon",
            "date": "Data",
            "stage": "Faza",
            "home_team": "Gazde",
            "away_team": "Oaspeti",
            "home_goals": "Gol Gazde",
            "away_goals": "Gol Oaspeti",
            "odds_home": "Cota 1",
            "odds_draw": "Cota X",
            "odds_away": "Cota 2",
        })

        st.dataframe(
            df.drop(columns=["Competitie"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
            height=350,
        )

        # --- Grafic simplu: numar de goluri pe sezon ---
        if "Sezon" in df.columns and df["Sezon"].notna().any():
            st.subheader("Goluri totale pe sezon")
            goals_per_season = (
                df.groupby("Sezon")[["Gol Gazde", "Gol Oaspeti"]]
                .sum(numeric_only=True)
                .assign(Total=lambda x: x["Gol Gazde"] + x["Gol Oaspeti"])
                .sort_index()
            )
            st.bar_chart(goals_per_season["Total"])

# ============================================================
# COLOANA 3 — PREDICTIE
# ============================================================
with col_predictie:
    st.header("🎯 Predictie")
    st.caption(selected_label)

    st.info(
        "Modelul de predictie urmeaza sa fie construit intr-o etapa viitoare. "
        "Deocamdata, introduci aici cotele curente de la casa de pariuri, ca "
        "sa fie gata de comparatie cand modelul va fi disponibil."
    )

    known_teams = fetch_teams_for_competition(selected_id)

    with st.form("manual_odds_form", clear_on_submit=True):
        st.markdown("**Cote curente (introduse manual)**")

        if known_teams:
            home_team = st.selectbox("Echipa gazda", options=known_teams, key="home_team_select")
            home_team_custom = st.text_input("...sau alt nume (gazda)", key="home_team_custom")
            if home_team_custom.strip():
                home_team = home_team_custom.strip()
        else:
            home_team = st.text_input("Echipa gazda")

        if known_teams:
            away_team = st.selectbox("Echipa oaspete", options=known_teams, key="away_team_select")
            away_team_custom = st.text_input("...sau alt nume (oaspete)", key="away_team_custom")
            if away_team_custom.strip():
                away_team = away_team_custom.strip()
        else:
            away_team = st.text_input("Echipa oaspete")

        match_date = st.date_input("Data meciului")

        snapshot = st.radio(
            "Moment fata de startul meciului",
            options=["T24h", "T12h", "T0h"],
            horizontal=True,
            help="T24h = cu 24h inainte, T12h = cu 12h inainte, T0h = cu maxim 1h inainte de start",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            odds_home = st.number_input("Cota 1", min_value=1.01, step=0.01, format="%.2f")
        with c2:
            odds_draw = st.number_input("Cota X", min_value=1.01, step=0.01, format="%.2f")
        with c3:
            odds_away = st.number_input("Cota 2", min_value=1.01, step=0.01, format="%.2f")

        source = st.text_input("Sursa (optional)", placeholder="ex. Superbet, 17 iulie")

        submitted = st.form_submit_button("Salveaza cotele")

        if submitted:
            if not home_team or not away_team:
                st.error("Completeaza numele ambelor echipe inainte de a salva.")
            else:
                insert_manual_odds(
                    competition_id=selected_id,
                    home_team=home_team,
                    away_team=away_team,
                    match_date=str(match_date),
                    snapshot=snapshot,
                    odds_home=odds_home,
                    odds_draw=odds_draw,
                    odds_away=odds_away,
                    source=source.strip() if source.strip() else "manual",
                )
                st.success(f"Salvat ({snapshot}): {home_team} vs {away_team}")
                st.rerun()

    # --- Istoric cote introduse manual, pivotat: un rand per meci, ---
    # --- cu cele 3 momente (T24h / T12h / T0h) unul langa altul ---
    manual_entries = fetch_manual_odds(competition_id=selected_id)

    if manual_entries:
        st.markdown("**Miscarea cotelor (T24h → T12h → T0h):**")

        df_manual = pd.DataFrame(manual_entries)

        # Combinam cele 3 cote (1/X/2) intr-un singur text per moment, ex. "1.90 / 3.40 / 4.20"
        df_manual["cote"] = df_manual.apply(
            lambda r: (
                f"{r['odds_home']:.2f} / {r['odds_draw']:.2f} / {r['odds_away']:.2f}"
                if pd.notna(r["odds_home"]) else "—"
            ),
            axis=1,
        )

        pivot = df_manual.pivot_table(
            index=["home_team", "away_team", "match_date"],
            columns="snapshot",
            values="cote",
            aggfunc="first",
        ).reset_index()

        # Ne asiguram ca apar toate cele 3 coloane, chiar daca nu exista inca date pentru un moment
        for col in ["T24h", "T12h", "T0h"]:
            if col not in pivot.columns:
                pivot[col] = "—"
        pivot = pivot[["home_team", "away_team", "match_date", "T24h", "T12h", "T0h"]]

        pivot = pivot.rename(columns={
            "home_team": "Gazde",
            "away_team": "Oaspeti",
            "match_date": "Data",
        })

        st.dataframe(pivot, use_container_width=True, hide_index=True, height=250)
        st.caption("Format cote: Cota 1 / Cota X / Cota 2")

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
