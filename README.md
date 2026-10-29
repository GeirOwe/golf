# Lisboa Høst

Flask-app for golfturneringen Lisboa Høst. En arrangør oppretter grupper. Hver gruppe har spillere, turer, runder og finale. Baner er felles for alle.

Kjører på [Render](https://golf-app-w497.onrender.com).

## Funksjoner

- Grupper. Kortadresse `/g/<slug>` følger gruppenavnet, for eksempel `/g/lisboa-host`. Den gamle hemmelige token-adressen virker fortsatt. Etter omdøping peker den gamle kortadressen videre til den nye.
- Spillere med handicap. Gyldig handicap er 0.0 til 54.0.
- Turer med destinasjon, lokale regler og yr-sted. En spiller som forlater turen tar med seg scorene sine fra den turen.
- Runder med bane, dato, tee time og henting. Datoer vises på norsk, for eksempel `Mandag 10.03`.
- Scoreregistrering per runde. Én score per spiller per runde.
- Tabell OOM. Summerer scorer over 0, regner snitt av de samme scorene, og sorterer på total.
- Finale. OOM-plass 1–4 gir bonus 4, 3, 2 og 1. Bonusen følger live OOM til finalescorer lagres, og låses deretter. Den låses også opp igjen når finalescorene tømmes, eller når runden ikke lenger er finale. Total er finalescore pluss bonus.
- Baner med anlegg og tee (Herre eller Dame, par, course rating, slope). Alle kan opprette og endre baner på `/baner`.
- Mottatte slag etter WHS (se `models.course_handicap`). Uten en gruppe vises ingen spillere.
- `/health` svarer `{"status":"ok"}` uten å bruke databasen.

## Kom i gang

```bash
git clone https://github.com/GeirOwe/golf.git
cd golf
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements.txt` er det Render installerer. `requirements-dev.txt` legger til pytest og flake8.

Lag en `.env` i rotmappa. Filen er gitignorert.

```env
DATABASE_URL=postgresql://user:password@host/neondb?sslmode=require
FLASK_ENV=development
FLASK_SECRET_KEY=a-long-random-string
ORGANIZER_SECRET=koden-du-skriver-pa-start
```

Produksjonsdatabasen ligger på Neon. For en lokal, tom database kan du bruke SQLite:

```env
DATABASE_URL=sqlite:///golf.db
```

Start appen:

```bash
flask --app app run
```

Tabellene opprettes ved første vanlige sideforespørsel. `/health` gjør det ikke.

Åpne `/start` og skriv `ORGANIZER_SECRET` for å opprette en gruppe. Del kortadressen i nettleseren. Forsiden tar imot en innlimt gruppelenke og sender deg videre.

## Produksjon

`render.yaml` beskriver webtjenesten. `DATABASE_URL` settes i Render-dashboardet og er merket `sync: false`, så en blueprint-synk ikke bytter fra Neon til en Render-database. Render installerer `requirements.txt` og starter:

```bash
gunicorn -c gunicorn.conf.py app:app
```

Sett `DATABASE_URL`, `FLASK_SECRET_KEY` og `ORGANIZER_SECRET` i Render. `FLASK_SECRET_KEY` er en lang tilfeldig streng som signerer innloggingen på `/start`. `ORGANIZER_SECRET` er koden du skriver der. En `postgres://`-adresse skrives om til `postgresql://` ved oppstart. Mot Neon brukes pooler-tilkoblingen (`-pooler`) med `NullPool`; ellers en liten connection pool med `pool_pre_ping`.

Sesjonskaken er `Secure` når databasen er Postgres. Lokal kjøring mot SQLite, også med `FLASK_ENV=production`, lar kaken virke over `http://127.0.0.1`.

`scripts/cutover.py` er allerede kjørt mot Neon. Ikke kjør den på nytt. Den stopper selv hvis de nye tabellene allerede finnes. Nye kolonner og indekser, som `finale_bonus` og unik score per spiller og runde, legges på ved oppstart av appen.

## Database

Modellene ligger i `database.py`: `groups`, `group_aliases`, `players`, `trips`, `trip_players`, `rounds`, `round_scores`, `golf_courses`, `course_tees`.

## Prosjektstruktur

```plaintext
golf/
├── app.py              # Flask-app og ruter
├── database.py         # SQLAlchemy-modeller
├── models.py           # HandicapError og WHS mottatte slag
├── scoring.py          # OOM og finale
├── gunicorn.conf.py
├── render.yaml
├── requirements.txt
├── requirements-dev.txt
├── static/
├── templates/
└── .env                # ikke committet
```

## Utvalgte ruter

| Sti | Merknad |
| --- | --- |
| `/` | Lim inn gruppelenken |
| `/start` | Arrangør. Krever `ORGANIZER_SECRET` |
| `/g/<slug>` | Gruppen. Gammel slug videresendes, gammel token virker |
| `/baner` | Felles baner |
| `/health` | Ingen database |

## Credits

Bygget av Gary Owen.
