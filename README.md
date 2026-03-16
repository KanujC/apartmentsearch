# Apartment Agent 🏠

A daily apartment-hunting agent that searches **ImmoScout24, Immowelt, eBay Kleinanzeigen and WG-Gesucht**, uses **Claude AI** to summarise each listing, and sends you a beautiful HTML email digest every morning via **SendGrid** — all running for free on **GitHub Actions**.

---

## How it works

```
07:00 every day
      │
      ▼
 GitHub Actions
      │
      ├─ Scrape all 4 sites
      ├─ Filter out already-seen listings
      ├─ Ask Claude for a 2-sentence summary of each flat
      ├─ Build HTML email digest
      ├─ Send via SendGrid
      └─ Commit updated seen_ids.json  ← no duplicates tomorrow
```

---

## Setup (15 minutes)

### 1. Fork / push this repo to GitHub

```bash
git init apartment-agent
cd apartment-agent
# copy all files here
git add .
git commit -m "initial commit"
gh repo create apartment-agent --private --push
```

### 2. Create a GitHub Personal Access Token (PAT)

The workflow needs to commit `seen_ids.json` back to your repo.

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Create a token with **Contents: read & write** for this repo
3. Copy the token

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name         | Value |
|---------------------|-------|
| `GH_PAT`            | Your fine-grained PAT from step 2 |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |
| `SENDGRID_API_KEY`  | From [app.sendgrid.com](https://app.sendgrid.com) → API Keys |
| `EMAIL_FROM`        | A **verified sender** email in your SendGrid account |
| `EMAIL_TO`          | Your personal email address |

### 4. Set search criteria (optional)

Go to **Settings → Secrets and variables → Actions → Variables** and add any of:

| Variable     | Default  | Description |
|-------------|---------|-------------|
| `CITY`       | `Berlin` | City to search (e.g. `München`, `Hamburg`) |
| `MIN_ROOMS`  | `2`      | Minimum rooms |
| `MAX_ROOMS`  | `4`      | Maximum rooms |
| `MIN_SIZE`   | `40`     | Minimum size in m² |
| `MAX_SIZE`   | `120`    | Maximum size in m² |
| `MIN_PRICE`  | `0`      | Minimum rent €/month |
| `MAX_PRICE`  | `1500`   | Maximum rent €/month |

### 5. Set up SendGrid sender verification

1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier = 100 emails/day)
2. Go to **Settings → Sender Authentication → Single Sender Verification**
3. Verify the email address you put in `EMAIL_FROM`

### 6. Trigger a test run

Go to your repo → **Actions → Daily Apartment Search → Run workflow**

You can also do a local dry-run (no email sent, saves preview to `email_preview.html`):

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export DRY_RUN=1
export CITY=Berlin
export MAX_PRICE=1500
python main.py
open email_preview.html
```

---

## File structure

```
apartment-agent/
├── .github/
│   └── workflows/
│       └── daily.yml        ← GitHub Actions schedule
├── agent/
│   ├── scraper.py           ← scraping logic for all 4 sites
│   ├── store.py             ← deduplication (seen_ids.json)
│   ├── email_builder.py     ← Claude summaries + HTML email
│   └── mailer.py            ← SendGrid sender
├── main.py                  ← orchestrates everything
├── seen_ids.json            ← auto-updated, do not delete
├── requirements.txt
└── README.md
```

---

## Customising

**Change the schedule** — edit the cron in `.github/workflows/daily.yml`:
```yaml
- cron: "0 6 * * *"   # 07:00 Berlin time (06:00 UTC)
```

**Search multiple cities** — duplicate the workflow job or add a matrix strategy.

**Add more sites** — add a new `scrape_xyz()` function in `agent/scraper.py` and call it from `scrape_all()`.

---

## Notes

- Sites may update their HTML structure. If scraping breaks, check the selectors in `scraper.py`.
- Claude summarises up to 20 new listings per run to keep API costs minimal (< €0.01/day).
- The `seen_ids.json` file grows over time — you can safely delete old entries (keep last 500 or so).
