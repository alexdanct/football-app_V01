# Aplicatie Analiza Fotbalistica — v1.0 (schelet)

## Structura proiectului

```
football-app/
├── database.py       ← structura bazei de date SQLite + functii de citire/scriere
├── import_data.py     ← import fisiere CSV (football-data.co.uk) in baza de date
├── app.py              ← interfata Streamlit (ce vede utilizatorul)
├── requirements.txt    ← lista de biblioteci Python necesare
└── README.md           ← acest fisier
```

## 1. Rulare locala (pe calculatorul tau, Windows 11)

### Prima data — instalarea bibliotecilor

Deschide Command Prompt (tasta Windows → scrie `cmd` → Enter), navigheaza in
folderul proiectului si instaleaza bibliotecile:

```
cd cale\catre\football-app
pip install -r requirements.txt
```

### Crearea bazei de date

```
python database.py
```

Ar trebui sa vezi mesajul "Tabelele au fost create" si "Competitii initiale
inserate" — se creeaza automat fisierul `football.db` in acelasi folder,
deja populat cu Campionatul Mondial, EURO, si principalele campionate de club.

### Import date din CSV (football-data.co.uk, un fisier per sezon)

```
python import_data.py cale\catre\fisier.csv "Premier League" club_league England 2023-2024
```

Pentru Campionatul Mondial (dataset Kaggle, format posibil diferit — te ghidez
separat cand ajungem acolo cu fisierul real):

```
python import_data.py cale\catre\worldcup.csv "Campionatul Mondial" national_team None 2022
```

### Import date din Excel (.xlsx, format multi-sezon)

Pentru fisiere Excel de tipul "Romania_totale.xlsx" — o singura foaie cu
mai multe sezoane deodata, coloane: Country, League, Season, Date, Home,
Away, HG, AG, plus mai multe seturi de cote. Sezonul se ia automat din
coloana "Season" a fisierului, deci nu il specifici manual.

```
python import_xlsx.py cale\catre\fisier.xlsx "Superliga" club_league Romania
```

Foloseste implicit cotele medii de piata (coloanele AvgCH/AvgCD/AvgCA) ca
sursa pentru odds_home/odds_draw/odds_away. Daca fisierul are alte nume de
coloane, se ajusteaza constantele de la inceputul lui `import_xlsx.py`.

### Import in lot — mai multe fisiere dintr-o singura comanda

Cand ai mai multe campionate de importat deodata (CSV-uri si/sau fisiere
Excel amestecate), nu mai rulezi comanda de import pe rand pentru fiecare —
completezi o singura lista si le imporți pe toate deodata.

Scriptul recunoaste automat 3 tipuri de fisiere:
1. **CSV format club** (football-data.co.uk): coloane `Date, HomeTeam,
   AwayTeam, FTHG...`. Daca fisierul concateneaza mai multi ani intr-un
   singur CSV, fara coloana de sezon, sezonul se deduce automat din data
   fiecarui meci (conventia iulie-iunie a campionatelor europene).
2. **CSV format international** (dataset Kaggle "International football
   results"): coloane `date, home_team, away_team, tournament...`. Contine
   TOATE meciurile internationale (amicale, calificari, turnee), deci
   trebuie spus explicit ce turneu extragi (ex. doar "FIFA World Cup").
3. **Excel (.xlsx) multi-sezon**, de tipul "Romania_totale.xlsx".

**Pasul 1** — copiaza `import_list_exemplu.csv`, redenumeste-l (ex.
`import_list.csv`) si completeaza-l cu fisierele tale:

```
fisier,competitie,tip,tara,sezon,turneu
date/anglia_totale.csv,Premier League,club_league,England,,
date/Romania_totale.xlsx,Superliga,club_league,Romania,,
date/results.csv,Campionatul Mondial,national_team,None,,FIFA World Cup
```

Reguli:
- `fisier`: calea catre fisier — se detecteaza automat tipul (CSV club /
  CSV international / Excel), dupa continut, nu doar dupa extensie
- `competitie`: numele campionatului — daca nu exista inca in baza de date,
  se creeaza automat
- `tip`: club_league / national_team / european_cup
- `tara`: tara, sau "None" daca nu se aplica
- `sezon`: OPTIONAL pentru CSV format club — lasa gol daca fisierul are mai
  multi ani concatenati fara coloana de sezon (se deduce automat)
- `turneu`: OBLIGATORIU doar pentru CSV format international — numele exact
  al turneului din coloana "tournament" a fisierului (ex. "FIFA World Cup",
  "FIFA World Cup qualification"). Lasa gol pentru celelalte tipuri de fisier.

Ca sa vezi ce nume de turnee exista intr-un fisier international inainte
sa completezi lista:

```
python import_international.py --list-tournaments date/results.csv
```

**Pasul 2** — rulezi:

```
python import_batch.py import_list.csv
```

La final vezi un rezumat cu ce s-a importat cu succes si ce a esuat (ex.
fisier negasit, sau lipsa filtrul de turneu), ca sa poti corecta rapid
lista si rula din nou.

### Pornirea aplicatiei

```
streamlit run app.py
```

Se deschide automat in browser, de obicei la `http://localhost:8501`.
Doar tu vezi aplicatia in acest moment (ruleaza local, pe calculatorul tau).

## 2. Publicare online (acces pentru tine + utilizator BETA)

Pasii, pe scurt (te ghidez detaliat cand ajungem aici):

1. Urci folderul `football-app` intr-un repository nou pe GitHub (contul creat
   deja).
2. Te conectezi pe **share.streamlit.io** cu acelasi cont GitHub.
3. Alegi "New app", selectezi repository-ul si fisierul `app.py`.
4. Streamlit iti da un link public (ex. `https://numele-tau.streamlit.app`),
   pe care il trimiti utilizatorului BETA.

**Nota despre baza de date pe Streamlit Cloud:** fisierul `football.db` se
poate reseta la repornirea aplicatiei in cloud (stocare temporara, nu
permanenta). Pentru faza de BETA, cu volum mic de date, nu e o problema —
reimportam datele daca se intampla. Daca ajungem sa avem nevoie de
persistenta completa, migram baza de date la un serviciu cloud gratuit
(Turso sau Supabase), fara sa schimbam structura de tabele.

## 3. Ce urmeaza

- Import date reale (primul fisier CSV de test)
- Verificare vizuala in aplicatie ca datele arata corect
- Calcul Elo si forma recenta
- Primul model de predictie (v1.0 — fara cote, doar istoric + forma)
