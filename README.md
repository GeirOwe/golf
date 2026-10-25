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
- Mottatte slag etter WHS: handicapindeks × (slope / 113) + (course rating − par).
- Spilleoppsett, lokale regler og nedtelling til første tee time.
- Værmelding fra yr.no på forsiden.
- Kort golftips på `/ai-story` via xAI. Krever `XAI_API_KEY`.
- Admin på `/admin`. Siden ligger ikke i menyen. Derfra kan scorer, runder og spillere slettes.
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

Produksjonsdatabasen ligger på Neon. For en lokal, tom database kan du bruke SQLite i stedet:

```env
DATABASE_URL=sqlite:///golf.db
```

Start appen:

```bash
flask --app app run
```

Tabellene opprettes ved første vanlige sideforespørsel. `/health` gjør det ikke.

## Produksjon

`render.yaml` beskriver webtjenesten. Render installerer `requirements.txt` og starter:

```bash
gunicorn -c gunicorn.conf.py app:app
```

Sett `DATABASE_URL` og eventuelt `XAI_API_KEY` i miljøet. En `postgres://`-adresse skrives om til `postgresql://` ved oppstart. Mot Neon brukes pooler-tilkoblingen med `NullPool`, og mot en vanlig Postgres-tilkobling brukes en liten connection pool med `pool_pre_ping`.

## Database

| Tabell | Innhold |
| --- | --- |
| `players` | Navn og handicap |
| `rounds` | Bane, dato, tee time, henting |
| `round_scores` | Score per spiller per runde |
| `finale_scores` | Én finalescore og låst OOM-bonus per spiller |
| `golf_courses` | Banenavn og anlegg |
| `course_tees` | Tee, kjønn, par, course rating, slope |

## Prosjektstruktur

```plaintext
golf/
├── app.py              # Flask-app og ruter
├── database.py         # SQLAlchemy-modeller
├── models.py           # Handicap-validering og mottatte slag
├── gunicorn.conf.py    # Gunicorn for Render
├── render.yaml         # Render-tjeneste
├── requirements.txt
├── .env                # Miljøvariabler, ikke committet
└── templates/
    ├── base.html
    ├── home.html
    ├── list_players.html
    ├── register_player.html
    ├── update_player.html
    ├── list_rounds.html
    ├── add_round.html
    ├── update_round.html
    ├── manage_scores.html
    ├── list_scores.html
    ├── finale.html
    ├── finale_resultat.html
    ├── confirm_reset_finale.html
    ├── list_golf_courses.html
    ├── add_golf_course.html
    ├── view_golf_course.html
    ├── mottatte_slag.html
    ├── flight_setup.html
    ├── local_rules.html
    ├── admin.html
    ├── unicorn_story.html
    └── 404.html
```

## Hovedruter

| Sti | Side |
| --- | --- |
| `/` | Hjem |
| `/players` | HCP-oversikt |
| `/register` | Ny spiller |
| `/rounds` | Tee times |
| `/round/new` | Ny runde |
| `/round/<id>/scores` | Registrer score |
| `/scores` | Tabell OOM |
| `/finale` | Finale |
| `/finale/resultat` | Finaleresultat |
| `/baner` | Baner |
| `/baner/ny` | Ny bane |
| `/baner/mottatte-slag` | Mottatte slag |
| `/flights` | Spilleoppsett |
| `/local-rules` | Lokale regler |
| `/admin` | Admin |
| `/ai-story` | AI-tips |
| `/health` | Helsesjekk |

## Credits

Bygget av Gary Owen.
