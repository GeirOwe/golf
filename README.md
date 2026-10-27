# Lisboa Høst

Flask-app for golfturneringen Lisboa Høst. Den holder orden på spillere, runder, scorer, baner og finale.

Kjører på [Render](https://golf-app-w497.onrender.com).

## Funksjoner

- Spillere med handicap. Høyeste handicap er 54.0.
- Runder med bane, dato, tee time og henting. Datoer vises på norsk, for eksempel `Mandag 10.03`.
- Scoreregistrering per runde.
- Tabell OOM. Summerer scorer over 0, regner snitt av de samme scorene, og sorterer på total.
- Finale. OOM-plass 1–4 gir bonus 4, 3, 2 og 1. Bonusen følger live OOM til første finalescore lagres, og låses deretter. Total er finalescore pluss bonus.
- Baner med anlegg og tee (Herre eller Dame, par, course rating, slope).
- Mottatte slag etter WHS (se `models.course_handicap`).
- Spilleoppsett, lokale regler og nedtelling til første tee time.
- Værmelding fra yr.no på forsiden.
- Kort golftips på `/ai-story` via xAI.
- Admin på `/admin` (ikke i menyen): slett scorer, runder og spillere.
- `/health` svarer `{"status":"ok"}` uten å bruke databasen.

## Kom i gang

```bash
git clone https://github.com/GeirOwe/golf.git
cd golf
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Lag en `.env` i rotmappa. Filen er gitignorert.

```env
DATABASE_URL=postgresql://user:password@host/neondb?sslmode=require
FLASK_ENV=development
XAI_API_KEY=your_xai_api_key_here
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

## Produksjon

`render.yaml` beskriver webtjenesten. `DATABASE_URL` settes i Render-dashboardet og er merket `sync: false`, så en blueprint-synk ikke bytter fra Neon til en Render-database. Render installerer `requirements.txt` og starter:

```bash
gunicorn -c gunicorn.conf.py app:app
```

Sett `DATABASE_URL`, `FLASK_SECRET_KEY` og `ORGANIZER_SECRET` i Render. `FLASK_SECRET_KEY` er en lang tilfeldig streng som signerer innloggingen på `/start`. `ORGANIZER_SECRET` er koden du skriver der. En `postgres://`-adresse skrives om til `postgresql://` ved oppstart. Mot Neon brukes pooler-tilkoblingen (`-pooler`) med `NullPool`; ellers en liten connection pool med `pool_pre_ping`.

`scripts/cutover.py` er allerede kjørt mot Neon. Ikke kjør den på nytt. Den stopper selv hvis de nye tabellene allerede finnes.

## Database

Modellene ligger i `database.py`: `players`, `rounds`, `round_scores`, `finale_scores`, `golf_courses`, `course_tees`.

## Prosjektstruktur

```plaintext
golf/
├── app.py              # Flask-app og ruter
├── database.py         # SQLAlchemy-modeller
├── models.py           # HandicapError og WHS mottatte slag
├── gunicorn.conf.py
├── render.yaml
├── requirements.txt
├── static/
├── templates/
└── .env                # ikke committet
```

## Utvalgte ruter

Meny og øvrige sider er definert i `app.py`. Spesielt:

| Sti | Merknad |
| --- | --- |
| `/admin` | Ikke i menyen |
| `/ai-story` | Krever `XAI_API_KEY` |
| `/health` | Ingen database |

## Credits

Bygget av Gary Owen.
