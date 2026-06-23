# Cita Previa Bot

Monitors the Spanish ICPPlus appointment system and sends a Telegram alert when slots open up. Read-only — never books anything.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
uv sync
uv run playwright install chromium

cp .env.example .env
# Fill in TELEGRAM_*, NIE, NOMBRE, and review the checker settings
```

## Commands

### Single availability check

```bash
uv run python -m app.main --check
```

Runs the wizard once headlessly, prints the status, and exits. Good for testing before setting up the monitor.

### Continuous monitor (polling loop)

```bash
uv run python -m app.main --monitor
```

Polls every `CHECK_INTERVAL_SECONDS` (default 300 s). Sends a Telegram alert if slots are found.

### Telegram test

```bash
uv run python -m app.main --telegram-test
```

### Discovery mode (headed browser, manual walk-through)

```bash
uv run python -m app.main --discover
```

Opens a headed Chromium window. Navigate through each wizard step manually, then press **ENTER** in the terminal to capture that page's state. Type `done` + ENTER when finished.

Captures saved under `data/discovery/<run_id>/step_NN/`:

| File | Contents |
|------|----------|
| `screenshot.png` | Full-page screenshot |
| `page.html` | Raw HTML |
| `visible_text.txt` | Visible text only |
| `meta.json` | URL, title, buttons, forms, select options |

## Wizard flow (discovered: Alicante / Ucrania TIE)

| Step | URL | Action |
|------|-----|--------|
| 0 | `/icpplus/index.html` | Select province → Aceptar |
| 1 | `/icpco/citar?p=3` | Select office + procedure → Aceptar |
| 2 | `/icpco/acInfo` | Info page → Entrar |
| 3 | `/icpco/acEntrada` | Fill NIE + name → Aceptar |
| 4 | `/icpco/acValidarEntrada` | Click "Solicitar Cita" |
| 5 | `/icpco/acCitar` | **Read result** — alert if no "no hay citas" text |

## Key .env settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVINCE_URL_PATH` | `/icpco/citar?p=3&locale=es` | Province select value |
| `SEDE_VALUE` | `99` | Office ID (99 = any) |
| `TRAMITE_GROUP_INDEX` | `1` | Which `tramiteGrupo[N]` to use |
| `TRAMITE_VALUE` | `4112` | Procedure value (4112 = Ucrania TIE) |
| `NIE` | — | Your NIE |
| `NOMBRE` | — | Your full name |
| `CHECK_INTERVAL_SECONDS` | `300` | Poll interval |

## Docker (headless monitor)

```bash
# Edit docker-compose.yml command to: ["uv", "run", "python", "-m", "app.main", "--monitor"]
docker compose up --build
```

> Discovery mode requires a real display — run it locally, not in Docker.

## Project structure

```
app/
  config.py        — env-based settings
  database.py      — SQLite schema + connection helper
  checker.py       — automated wizard walker + availability detection
  discovery.py     — headed browser capture loop
  telegram_bot.py  — Telegram send helper
  main.py          — CLI entry point
data/
  discovery/       — captured wizard steps (git-ignored)
  cita_previa.db   — SQLite state (git-ignored)
```

## Safety rules

- **No auto-booking.** Reads the result page only.
- **No CAPTCHA bypass.**
- **No proxy rotation.**
- **No aggressive polling** — minimum 5-minute interval recommended.
