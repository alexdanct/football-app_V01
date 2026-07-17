# -*- coding: utf-8 -*-
"""
import_batch.py

Importa mai multe fisiere (CSV sau Excel) dintr-o singura comanda, pe baza
unei liste ("manifest") pe care o completezi tu intr-un fisier CSV simplu.

Scriptul detecteaza automat 3 tipuri de fisiere:
    1. CSV format club (football-data.co.uk): Date, HomeTeam, AwayTeam, FTHG...
       -> daca lipseste sezonul, se deduce automat din data fiecarui meci
    2. CSV format international (Kaggle "International football results"):
       date, home_team, away_team, tournament...
       -> necesita coloana "turneu" completata in manifest, ca sa stie ce
          competitie sa extraga (ex. "FIFA World Cup")
    3. Excel (.xlsx) multi-sezon, de tipul "Romania_totale.xlsx"

PASUL 1 — completezi lista de fisiere de importat

Creezi un fisier `import_list.csv` (poti porni de la exemplul
`import_list_exemplu.csv` din acest folder), cu urmatoarele coloane:

    fisier,competitie,tip,tara,sezon,turneu

    - fisier      : calea catre fisierul CSV sau XLSX (relativa sau completa)
    - competitie  : numele sub care apare competitia in aplicatie, ex.
                    "Premier League" sau "Campionatul Mondial"
                    (daca nu exista inca in baza de date, se creeaza automat)
    - tip         : club_league / national_team / european_cup
    - tara        : tara campionatului, sau "None" daca nu se aplica
    - sezon       : OPTIONAL pentru CSV format club — daca lipseste, se
                    deduce automat din data meciului. Ignorat pentru XLSX
                    (se ia din coloana "Season" a fisierului) si pentru
                    fisiere internationale (se ia din anul meciului).
    - turneu      : OBLIGATORIU doar pentru CSV format international — numele
                    exact al turneului din coloana "tournament" a fisierului
                    (ex. "FIFA World Cup"). Lasa gol pentru celelalte tipuri.

Exemplu de continut:

    fisier,competitie,tip,tara,sezon,turneu
    date/anglia_totale.csv,Premier League,club_league,England,,
    date/Romania_totale.xlsx,Superliga,club_league,Romania,,
    date/results.csv,Campionatul Mondial,national_team,None,,FIFA World Cup

PASUL 2 — rulezi comanda

    python import_batch.py import_list.csv

La final, afiseaza un rezumat cu cate meciuri s-au importat din fiecare fisier.

Pentru a vedea ce nume de turnee exista intr-un fisier international, ruleaza
separat: python import_international.py --list-tournaments cale/fisier.csv
"""

import sys
import csv as csv_module
from pathlib import Path

from database import create_tables
from import_data import import_csv
from import_xlsx import import_xlsx
from import_international import import_international


def detect_csv_format(filepath: str) -> str:
    """
    Citeste doar antetul unui CSV si decide formatul:
    'international' daca are coloana 'tournament', 'club' daca are 'HomeTeam',
    None daca nu recunoaste formatul.

    Incearca mai multe codificari (UTF-8, apoi Windows-1252/Latin-1), pentru ca
    fisierul intreg poate fi citit dintr-un singur buffer intern, iar o eroare
    de decodare mai jos in fisier (ex. un caracter special intr-un nume de
    echipa) ar bloca altfel si citirea antetului.
    """
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(filepath, newline="", encoding=enc) as f:
                header = next(csv_module.reader(f), [])
            return _classify_header(header)
        except UnicodeDecodeError:
            continue
    return None


def _classify_header(header):
    header_set = set(h.strip() for h in header)
    if "tournament" in header_set:
        return "international"
    if "HomeTeam" in header_set:
        return "club"
    return None


def run_batch(manifest_path: str):
    create_tables()

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"[EROARE] Nu gasesc fisierul manifest: {manifest_path}")
        sys.exit(1)

    with open(manifest_file, newline="", encoding="utf-8-sig") as f:
        reader = csv_module.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    required_cols = {"fisier", "competitie", "tip", "tara"}
    if not rows or not required_cols.issubset(set(fieldnames)):
        print(f"[EROARE] Fisierul manifest trebuie sa aiba cel putin coloanele: "
              f"fisier,competitie,tip,tara (plus sezon,turneu optionale)")
        print(f"Coloane gasite: {fieldnames}")
        sys.exit(1)

    print(f"Gasite {len(rows)} inregistrari de importat.\n")

    results = []

    for i, row in enumerate(rows, start=1):
        filepath = row["fisier"].strip()
        competition_name = row["competitie"].strip()
        competition_type = row["tip"].strip()
        country = row["tara"].strip()
        country = None if country.lower() in ("none", "") else country
        season = (row.get("sezon") or "").strip() or None
        tournament_filter = (row.get("turneu") or "").strip() or None

        print(f"[{i}/{len(rows)}] Import '{filepath}' -> '{competition_name}' ({competition_type})...")

        path_obj = Path(filepath)
        if not path_obj.exists():
            print(f"  [!] Fisier negasit, sar peste: {filepath}\n")
            results.append((filepath, competition_name, "EROARE: fisier negasit"))
            continue

        try:
            suffix = path_obj.suffix.lower()

            if suffix in (".xlsx", ".xls"):
                import_xlsx(filepath, competition_name, competition_type, country)
                results.append((filepath, competition_name, "OK"))
                print()
                continue

            if suffix != ".csv":
                print(f"  [!] Extensie necunoscuta ({suffix}), sar peste.\n")
                results.append((filepath, competition_name, f"EROARE: extensie {suffix} necunoscuta"))
                continue

            csv_format = detect_csv_format(filepath)

            if csv_format == "international":
                if not tournament_filter:
                    print(f"  [!] Fisierul e format international (are coloana 'tournament'), "
                          f"dar lipseste coloana 'turneu' in manifest. Sar peste.\n")
                    results.append((filepath, competition_name, "EROARE: lipseste filtrul de turneu"))
                    continue
                import_international(filepath, tournament_filter, competition_name)
                results.append((filepath, competition_name, "OK"))

            elif csv_format == "club":
                import_csv(filepath, competition_name, competition_type, country, season)
                results.append((filepath, competition_name, "OK"))

            else:
                print(f"  [!] Nu recunosc formatul CSV-ului (nu are nici 'HomeTeam', "
                      f"nici 'tournament' in antet). Sar peste.\n")
                results.append((filepath, competition_name, "EROARE: format CSV necunoscut"))

        except SystemExit:
            results.append((filepath, competition_name, "EROARE la import"))
        except Exception as e:
            print(f"  [!] Eroare neasteptata: {e}\n")
            results.append((filepath, competition_name, f"EROARE: {e}"))

        print()

    print("=" * 60)
    print("REZUMAT IMPORT IN LOT")
    print("=" * 60)
    for filepath, competition_name, status in results:
        print(f"  {status:35s} | {competition_name:25s} | {filepath}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    run_batch(sys.argv[1])
