# -*- coding: utf-8 -*-
"""
database.py

Modulul central pentru baza de date SQLite a aplicatiei de analiza fotbalistica.
Structura este generica: acopera echipe nationale (inclusiv Campionatul Mondial,
EURO etc.), campionate interne de club si cupe europene, fara sa fie nevoie de
schimbari ulterioare de structura.

Foloseste doar biblioteca standard Python (sqlite3), nu necesita instalare
suplimentara pentru aceasta parte.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "football.db"


def get_connection():
    """Returneaza o conexiune la baza de date SQLite (o creeaza daca nu exista)."""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Creeaza toate tabelele necesare, daca nu exista deja."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('national_team', 'club_league', 'european_cup')),
            country TEXT,
            UNIQUE(name, type)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('national', 'club')),
            country TEXT,
            UNIQUE(name, type)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL,
            season TEXT,
            date TEXT NOT NULL,
            stage TEXT,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            odds_home REAL,
            odds_draw REAL,
            odds_away REAL,
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS elo_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            rating REAL NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
    """)

    # Curatam eventuale duplicate deja existente (ex. din rulari anterioare
    # ale importului, inainte sa existe protectia de unicitate), pastrand
    # doar prima aparitie a fiecarui meci. Necesar sa ruleze INAINTE de a
    # crea indexul de unicitate de mai jos, altfel crearea indexului ar esua
    # daca mai exista deja duplicate in baza de date.
    cur.execute("""
        DELETE FROM matches
        WHERE id NOT IN (
            SELECT MIN(id) FROM matches
            GROUP BY competition_id, home_team_id, away_team_id, date
        );
    """)
    removed = cur.rowcount
    if removed > 0:
        print(f"  [~] Curatare: {removed} meciuri duplicate gasite din rulari anterioare au fost sterse.")

    # Indexul de unicitate: un meci e definit ca (aceeasi competitie + aceleasi
    # doua echipe + aceeasi data). O data creat, orice incercare ulterioara de
    # a insera acelasi meci e ignorata automat de scripturile de import
    # (INSERT OR IGNORE), deci import_batch.py poate fi rulat oricand din nou,
    # in siguranta, fara sa dubleze datele.
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_match
        ON matches(competition_id, home_team_id, away_team_id, date);
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS manual_odds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            match_date TEXT,
            snapshot TEXT NOT NULL DEFAULT 'T0h' CHECK(snapshot IN ('T24h', 'T12h', 'T0h')),
            odds_home REAL,
            odds_draw REAL,
            odds_away REAL,
            source TEXT DEFAULT 'manual',
            entered_at TEXT NOT NULL,
            FOREIGN KEY (competition_id) REFERENCES competitions(id)
        );
    """)

    # Migrare: daca baza de date a fost creata inainte de introducerea
    # coloanei "snapshot" (cotele la T24h / T12h / T0h inainte de meci),
    # o adaugam acum, fara sa pierdem datele existente.
    cur.execute("PRAGMA table_info(manual_odds);")
    existing_cols = {row["name"] for row in cur.fetchall()}
    if "snapshot" not in existing_cols:
        cur.execute("""
            ALTER TABLE manual_odds ADD COLUMN snapshot TEXT NOT NULL DEFAULT 'T0h';
        """)
        print("  [~] Migrare: coloana 'snapshot' (T24h/T12h/T0h) a fost adaugata la cotele manuale existente.")

    # Un singur set de cote per meci + moment (T24h/T12h/T0h). Daca introduci
    # din nou cote pentru acelasi meci si acelasi moment, valoarea veche este
    # inlocuita (INSERT OR REPLACE), nu duplicata.
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_manual_odds
        ON manual_odds(competition_id, home_team, away_team, match_date, snapshot);
    """)

    conn.commit()
    conn.close()
    print("Tabelele au fost create (sau existau deja).")


def seed_initial_competitions():
    """
    Populeaza tabela competitions cu cateva competitii de start, inclusiv
    Campionatul Mondial, ca sa avem ceva de ales din interfata inca de la
    prima rulare.
    """
    conn = get_connection()
    cur = conn.cursor()

    initial_competitions = [
        ("Campionatul Mondial", "national_team", None),
        ("Campionatul European (EURO)", "national_team", None),
        ("Superliga", "club_league", "Romania"),
        ("Premier League", "club_league", "England"),
        ("La Liga", "club_league", "Spain"),
        ("Serie A", "club_league", "Italy"),
        ("Bundesliga", "club_league", "Germany"),
        ("Ligue 1", "club_league", "France"),
        ("UEFA Champions League", "european_cup", None),
        ("UEFA Europa League", "european_cup", None),
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO competitions (name, type, country)
        VALUES (?, ?, ?)
    """, initial_competitions)

    conn.commit()
    conn.close()
    print(f"Competitii initiale inserate (sau existau deja): {len(initial_competitions)} verificate.")


def get_or_create_team(cur, name: str, team_type: str, country: str = None) -> int:
    """
    Returneaza id-ul unei echipe; o creeaza daca nu exista inca.
    team_type trebuie sa fie 'national' sau 'club'.

    Primeste un cursor deja deschis (cur), ca sa nu deschidem conexiuni noi
    in paralel cu apelantul (asta cauza erori de tip "database is locked").
    Apelantul e responsabil de conn.commit() / conn.close().
    """
    cur.execute("SELECT id FROM teams WHERE name = ? AND type = ?", (name, team_type))
    row = cur.fetchone()
    if row:
        return row["id"]

    cur.execute(
        "INSERT INTO teams (name, type, country) VALUES (?, ?, ?)",
        (name, team_type, country)
    )
    return cur.lastrowid


def get_competition_id(name: str, comp_type: str) -> int:
    """Returneaza id-ul unei competitii dupa nume si tip. None daca nu exista."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM competitions WHERE name = ? AND type = ?", (name, comp_type))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def get_or_create_competition(name: str, comp_type: str, country: str = None) -> int:
    """
    Returneaza id-ul unei competitii; o creeaza automat daca nu exista inca.
    Folosita de scripturile de import, ca sa nu fie nevoie sa editezi manual
    database.py de fiecare data cand adaugi un campionat nou.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM competitions WHERE name = ? AND type = ?", (name, comp_type))
    row = cur.fetchone()
    if row:
        conn.close()
        return row["id"]

    cur.execute(
        "INSERT INTO competitions (name, type, country) VALUES (?, ?, ?)",
        (name, comp_type, country)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    print(f"  [+] Competitie noua creata: '{name}' ({comp_type})")
    return new_id


def fetch_all_competitions():
    """Returneaza toate competitiile, ca lista de dict-uri."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM competitions ORDER BY type, name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetch_matches(competition_id: int = None):
    """
    Returneaza meciurile, cu numele echipelor deja rezolvate (JOIN),
    optional filtrate dupa competitie.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
            m.id, c.name AS competition, m.season, m.date, m.stage,
            th.name AS home_team, ta.name AS away_team,
            m.home_goals, m.away_goals,
            m.odds_home, m.odds_draw, m.odds_away
        FROM matches m
        JOIN competitions c ON m.competition_id = c.id
        JOIN teams th ON m.home_team_id = th.id
        JOIN teams ta ON m.away_team_id = ta.id
    """
    params = ()
    if competition_id is not None:
        query += " WHERE m.competition_id = ?"
        params = (competition_id,)
    query += " ORDER BY m.date DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetch_teams_for_competition(competition_id: int):
    """
    Returneaza lista de nume de echipe care au jucat vreodata in aceasta
    competitie (dupa istoricul din tabela matches). Utila pentru dropdown-uri
    in formulare, ca sa nu se scrie numele echipelor de mana de fiecare data.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT t.name FROM teams t
        JOIN matches m ON t.id = m.home_team_id
        WHERE m.competition_id = ?
        UNION
        SELECT DISTINCT t.name FROM teams t
        JOIN matches m ON t.id = m.away_team_id
        WHERE m.competition_id = ?
        ORDER BY name
    """, (competition_id, competition_id))
    names = [r["name"] for r in cur.fetchall()]
    conn.close()
    return names


def insert_manual_odds(competition_id: int, home_team: str, away_team: str,
                        match_date: str, snapshot: str, odds_home: float,
                        odds_draw: float, odds_away: float, source: str = "manual"):
    """
    Insereaza (sau suprascrie, daca exista deja) cotele pentru un meci la un
    anumit moment fata de start: 'T24h', 'T12h' sau 'T0h'.
    """
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO manual_odds
            (competition_id, home_team, away_team, match_date, snapshot,
             odds_home, odds_draw, odds_away, source, entered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (competition_id, home_team, away_team, match_date, snapshot,
          odds_home, odds_draw, odds_away, source,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def fetch_manual_odds(competition_id: int = None):
    """Returneaza cotele introduse manual, optional filtrate dupa competitie."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT mo.id, c.name AS competition, mo.home_team, mo.away_team,
               mo.match_date, mo.snapshot, mo.odds_home, mo.odds_draw, mo.odds_away,
               mo.source, mo.entered_at
        FROM manual_odds mo
        JOIN competitions c ON mo.competition_id = c.id
    """
    params = ()
    if competition_id is not None:
        query += " WHERE mo.competition_id = ?"
        params = (competition_id,)
    query += " ORDER BY mo.home_team, mo.away_team, mo.match_date, mo.entered_at DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def delete_manual_odds(entry_id: int):
    """Sterge o inregistrare de cote manuale dupa id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM manual_odds WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    seed_initial_competitions()
    print(f"Baza de date este gata la: {DB_PATH}")
