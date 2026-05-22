# Metro Honda → Facebook Marketplace (live cached app)

Scrapes [Metro Honda Jersey City](https://www.mymetrohonda.com/search/used-honda-jersey-city-nj/?cy=07305&mk=23&tp=used) inventory and gives you a **browser UI** to copy listings, download photo ZIPs, and post to Facebook Marketplace.

## Quick start (local)

```powershell
pip install -r requirements.txt
copy config.example.yaml config.yaml
# Edit config.yaml — set seller.phone to YOUR number

npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

`npm run dev` starts both pieces:

- FastAPI cache API at `http://127.0.0.1:8787`
- Vite website at `http://localhost:5173`

The website loads cached inventory immediately, then the API refreshes inventory in the background if the cache is missing or stale. You do **not** need to run `npm run refresh` every time.

### Workflow in the browser

1. Click a vehicle
2. **Copy all** — title, price, description for Marketplace
3. **Download photos (ZIP)** — upload to Facebook (up to 20)
4. **Open Marketplace** — create vehicle listing, paste, publish
5. Check **Mark as posted** — tracked in your browser (localStorage)

## Commands

| Command | What it does |
|---------|----------------|
| `npm run dev` | Local website + live inventory cache API |
| `npm run build` | Production build → `dist/` |
| `npm run preview` | Preview production build |
| `npm run data` | Export `data/inventory.json` → `public/` |
| `npm run scrape` | Scrape dealer site only |
| `npm run refresh` | Manual scrape + export fallback |

## Deploy to Render

1. Push this repo to GitHub
2. [Render](https://render.com) → **New Web Service** → connect repo
3. Use the included `render.yaml`, or set:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt && npm install && npm run build`
   - **Start command:** `python -m metro_fb.server --host 0.0.0.0 --port $PORT`

On Render, the React site is still static assets, but the Python service keeps the live cache updated automatically.

## Deploy to GitHub Pages

```powershell
npm run refresh
npm run build
# Deploy dist/ with GitHub Actions or gh-pages branch
```

Set Vite `base` in `vite.config.ts` to your repo name if not deploying at domain root, e.g. `base: '/metrohondafacebookmarketplace/'`.

## Configuration

Edit `config.yaml` (not committed — copy from `config.example.yaml`):

- `seller.phone` — buyers contact **you** for $150 private leads
- `scrape.max_vehicles` — cap per scrape
- `scrape.condition` — `used`, `new`, or `all`

Then restart `npm run dev` (or let Render redeploy).

## Facebook Marketplace API?

There is **no** public API to post to a personal Marketplace account. This app prepares content; you post manually (2–3 min per car).

## Project layout

```
src/                 React UI (Vite)
public/data/         inventory.json + photos (generated)
metro_fb/            Python scraper
config.yaml          Your settings (local only)
dist/                Built static site (after npm run build)
```

## Python CLI (optional)

```powershell
python -m metro_fb scrape
python -m metro_fb export-web
python -m metro_fb run --limit 10
```
