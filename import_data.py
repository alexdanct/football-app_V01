# -*- coding: utf-8 -*-
"""
import_data.py

Importa fisiere CSV descarcate de pe football-data.co.uk in baza de date SQLite.

Cum se foloseste (din terminal, in folderul proiectului):

    python import_data.py cale/catre/fisier.csv "Premier League" club_league England 2023-2024

Sau, daca fisierul concateneaza mai multi ani/sezoane intr-un singur CSV
(fara coloana de sezon explicita), se omite ultimul argument si sezonul
se deduce automat din data fiecarui meci:

    python import_data.py cale/catre/fisier.csv "Premier League" club_league England

Argumente, in ordine:
    1. calea catre fisierul CSV descarcat
    2. numele competitiei (se creeaza automat daca nu exista deja)
    3. tipul competitiei: club_league / national_team / european_cup
    4. tara (sau "None" daca nu se aplica, ex. pentru Campionatul Mondial)
    5. sezonul, ex: 2023-2024 (OPTIONAL — daca lipseste, se deduce automat
       din data meciului, presupunand ciclul iulie-iunie al campionatelor
       europene)

Fisierele de pe football-data.co.uk au, de regula, coloanele:
    Date, HomeTeam, AwayTeam, FTHG (gol gazde), FTAG (gol oaspeti),
    B365H, B365D, B365A (cote Bet365: victorie gazda / egal / victorie oaspeti)

Daca un fisier are coloane cu alte nume, se ajusteaza maparea COLUMN_MAP de mai jos.
"""

import sys
import csv
from datetime import datetime

from database import get_connection, get_or_create_team, get_or_create_competition, create_tables

# Maparea coloanelor asteptate din CSV-urile football-data.co.uk
COLUMN_MAP = {
    "date": "Date",
    "home_team": "HomeTeam",
    "away_team": "AwayTeam",
    "home_goals": "FTHG",
    "away_goals": "FTAG",
    "odds_home": "B365H",
    "odds_draw": "B365D",
    "odds_away": "B365A",
}


def parse_date(raw_date: str) -> str:
    """
    football-data.co.uk foloseste de obicei formatul DD/MM/YYYY sau DD/MM/YY.
    Convertim la ISO (YYYY-MM-DD) pentru consistenta in baza de date.
    """
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # daca formatul nu se potriveste, il lasam ca atare si semnalam
    print(f"  [!] Atentie: nu am putut interpreta data '{raw_date}', o pastrez ca atare.")
    return raw_date


def derive_season(iso_date: str) -> str:
    """
    Deduce sezonul (ex. "2016-2017") dintr-o data ISO, pentru fisiere care
    concateneaza mai multi ani intr-un singur CSV, fara coloana de sezon
    explicita. Foloseste conventia campionatelor europene: sezonul incepe
    in iulie/august si se termina in mai/iunie anul urmator.
    """
    try:
        year, month = int(iso_date[:4]), int(iso_date[5:7])
    except (ValueError, TypeError, IndexError):
        return None

    if month >= 7:
        return f"{year}-{year + 1}"
    else:
        return f"{year - 1}-{year}"


def read_csv_dictrows(filepath: str):
    """
    Citeste un fisier CSV incercand mai multe codificari, in ordine:
    UTF-8, apoi Windows-1252 (cp1252) si Latin-1 — cele mai frecvente
    codificari intalnite la fisiere descarcate din surse europene, care
    pot contine caractere speciale (ex. diacritice) ce nu sunt UTF-8 valid.

    Returneaza (fieldnames, lista_de_dictionare), citite complet in memorie
    — fisierele noastre au cateva mii de randuri, deci e sigur.
    """
    encodings_to_try = ("utf-8-sig", "cp1252", "latin-1")

    for enc in encodings_to_try:
        try:
            with open(filepath, newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            return reader.fieldnames, rows
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "unknown", b"", 0, 1,
        f"Nu am putut citi '{filepath}' cu niciuna dintre codificarile incercate: "
        f"{encodings_to_try}"
    )


def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def import_csv(filepath: str, competition_name: str, competition_type: str,
                country: str, season: str = None):
    """
    Daca season este None sau gol, sezonul este dedus automat pentru fiecare
    meci in parte, din data meciului (util pentru fisiere care concateneaza
    mai multi ani intr-un singur CSV, fara coloana de sezon).
    """

    create_tables()  # siguranta: se asigura ca tabelele exista

    competition_id = get_or_create_competition(competition_name, competition_type, country)

    team_type = "national" if competition_type == "national_team" else "club"
    auto_season = not season  # daca nu s-a dat sezon explicit, il deducem per rand

    fieldnames, rows = read_csv_dictrows(filepath)

    conn = get_connection()
    cur = conn.cursor()

    inserted, skipped, duplicates = 0, 0, 0
    seasons_seen = set()

    try:
        for row in rows:
            try:
                home_name = row[COLUMN_MAP["home_team"]].strip()
                away_name = row[COLUMN_MAP["away_team"]].strip()
                raw_date = row[COLUMN_MAP["date"]].strip()
            except KeyError as e:
                print(f"[EROARE] Coloana lipsa in CSV: {e}. Verifica COLUMN_MAP.")
                raise

            if not home_name or not away_name or not raw_date:
                skipped += 1
                continue

            match_date = parse_date(raw_date)
            row_season = derive_season(match_date) if auto_season else season
            if row_season:
                seasons_seen.add(row_season)

            home_team_id = get_or_create_team(cur, home_name, team_type, country)
            away_team_id = get_or_create_team(cur, away_name, team_type, country)

            home_goals = safe_int(row.get(COLUMN_MAP["home_goals"]))
            away_goals = safe_int(row.get(COLUMN_MAP["away_goals"]))
            odds_home = safe_float(row.get(COLUMN_MAP["odds_home"]))
            odds_draw = safe_float(row.get(COLUMN_MAP["odds_draw"]))
            odds_away = safe_float(row.get(COLUMN_MAP["odds_away"]))

            cur.execute("""
                INSERT OR IGNORE INTO matches
                    (competition_id, season, date, stage, home_team_id, away_team_id,
                     home_goals, away_goals, odds_home, odds_draw, odds_away)
                VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            """, (competition_id, row_season, match_date, home_team_id, away_team_id,
                  home_goals, away_goals, odds_home, odds_draw, odds_away))

            if cur.rowcount == 0:
                duplicates += 1
            else:
                inserted += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\nImport finalizat pentru '{competition_name}':")
    print(f"  - meciuri inserate: {inserted}")
    print(f"  - meciuri deja existente (sarite, fara duplicare): {duplicates}")
    print(f"  - randuri sarite (date lipsa): {skipped}")
    if auto_season:
        print(f"  - sezoane deduse automat: {len(seasons_seen)} ({', '.join(sorted(seasons_seen))})")
    else:
        print(f"  - sezon: {season}")


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        print(__doc__)
        sys.exit(1)

    filepath, competition_name, competition_type, country = sys.argv[1:5]
    season = sys.argv[5] if len(sys.argv) == 6 else None
    country = None if country == "None" else country

    import_csv(filepath, competition_name, competition_type, country, season)
