# -*- coding: utf-8 -*-
"""
import_international.py

Importa meciuri de echipe nationale dintr-un fisier de tip "International
football results" (dataset Kaggle: date, home_team, away_team, home_score,
away_score, tournament, city, country, neutral).

Acest fisier contine TOATE meciurile internationale din 1872 pana azi —
amicale, calificari, turnee finale, toate amestecate. Scriptul filtreaza
dupa coloana "tournament", ca sa importi doar competitia care te intereseaza
(ex. doar Cupa Mondiala, nu si amicalele).

Cum se foloseste (din terminal, in folderul proiectului):

    python import_international.py results.csv "FIFA World Cup" "Campionatul Mondial"

Argumente, in ordine:
    1. calea catre fisierul CSV (formatul Kaggle descris mai sus)
    2. numele exact al turneului in fisier, coloana "tournament"
       (ex. "FIFA World Cup", "FIFA World Cup qualification",
       "UEFA Euro qualification", "Friendly")
    3. numele sub care vrei sa apara competitia in aplicatie
       (ex. "Campionatul Mondial") — se creeaza automat daca nu exista

Sezonul se deduce automat din anul meciului (ex. "2022" pentru un meci
din Cupa Mondiala 2022), pentru ca turneele de echipe nationale nu au
un ciclu iulie-iunie ca ligile de club.

Pentru a vedea ce nume de turnee exista in fisierul tau, ruleaza:

    python import_international.py --list-tournaments results.csv
"""

import sys
import csv

from database import get_connection, get_or_create_team, get_or_create_competition, create_tables
from import_data import read_csv_dictrows


def list_tournaments(filepath: str):
    """Afiseaza toate valorile unice din coloana 'tournament', utile ca referinta."""
    _, rows = read_csv_dictrows(filepath)
    tournaments = sorted({row["tournament"] for row in rows if row.get("tournament")})

    print(f"Turnee gasite in '{filepath}' ({len(tournaments)} total):\n")
    for t in tournaments:
        print(f"  - {t}")


def import_international(filepath: str, tournament_filter: str, competition_name: str):

    create_tables()

    competition_id = get_or_create_competition(competition_name, "national_team", None)

    _, rows = read_csv_dictrows(filepath)

    conn = get_connection()
    cur = conn.cursor()

    inserted, skipped, other_tournament, duplicates = 0, 0, 0, 0
    seasons_seen = set()

    try:
        for row in rows:
            if row.get("tournament", "").strip().lower() != tournament_filter.strip().lower():
                other_tournament += 1
                continue

            home_name = row.get("home_team", "").strip()
            away_name = row.get("away_team", "").strip()
            raw_date = row.get("date", "").strip()

            if not home_name or not away_name or not raw_date:
                skipped += 1
                continue

            # unele randuri sunt sloturi programate pentru meciuri viitoare
            # (ex. finale ale unui turneu inca neinceput), fara echipe stabilite
            # inca, marcate literal cu textul "NA" — le ignoram, nu sunt date reale
            if home_name.upper() == "NA" or away_name.upper() == "NA":
                skipped += 1
                continue

            # formatul Kaggle e deja ISO: YYYY-MM-DD
            match_date = raw_date
            season = raw_date[:4]  # anul meciului, ex. "2022"

            home_team_id = get_or_create_team(cur, home_name, "national", None)
            away_team_id = get_or_create_team(cur, away_name, "national", None)

            home_goals = row.get("home_score") or None
            away_goals = row.get("away_score") or None
            try:
                home_goals = int(home_goals) if home_goals is not None else None
                away_goals = int(away_goals) if away_goals is not None else None
            except ValueError:
                home_goals, away_goals = None, None

            cur.execute("""
                INSERT OR IGNORE INTO matches
                    (competition_id, season, date, stage, home_team_id, away_team_id,
                     home_goals, away_goals, odds_home, odds_draw, odds_away)
                VALUES (?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, NULL)
            """, (competition_id, season, match_date, home_team_id, away_team_id,
                  home_goals, away_goals))

            if cur.rowcount == 0:
                duplicates += 1
            else:
                inserted += 1
                seasons_seen.add(season)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\nImport finalizat pentru '{competition_name}' (filtrat dupa turneul '{tournament_filter}'):")
    print(f"  - meciuri inserate: {inserted}")
    print(f"  - meciuri deja existente (sarite, fara duplicare): {duplicates}")
    print(f"  - randuri sarite (date/echipe lipsa): {skipped}")
    print(f"  - randuri ignorate (alt turneu): {other_tournament}")
    print(f"  - ani acoperiti: {len(seasons_seen)} ({min(seasons_seen)}–{max(seasons_seen)})" if seasons_seen else "")

    if inserted == 0 and duplicates == 0:
        print(f"\n[!] Atentie: 0 meciuri inserate. Verifica numele exact al turneului cu:")
        print(f"    python import_international.py --list-tournaments {filepath}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--list-tournaments":
        list_tournaments(sys.argv[2])
        sys.exit(0)

    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    _, filepath, tournament_filter, competition_name = sys.argv
    import_international(filepath, tournament_filter, competition_name)
