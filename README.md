# Global Demographics in 2100

An interactive, fixed-position webapp dashboard mapping the demographic transformation of the 21st century. Built with the **Veles (Fable-5 × DeepSeek)** pipeline for **H Heuristics**.

**Live source of data:** [Our World in Data — region population to 2100](https://ourworldindata.org/region-population-2100)

---

## What it shows

- **World choropleth map** — projected population (or Δ growth 2024→2100) for every country, animated on a 1950–2100 timeline with playback controls.
- **Region trajectories** — population by UN region (Africa, Asia, Europe, Latin America & Caribbean, Northern America, Oceania) plus the World total and an IHME (Lancet) comparison scenario.
- **Country ranking** — the top-12 most populous nations in 2100, colored by region.
- **Median-age panel** — the greying of every region, 1950–2100.
- **Key figures** — world population in 2024 (8.16 B), the projected peak (10.29 B in 2084), and the 2100 total (10.18 B), alongside fertility and age-structure milestones.

## Data sources

| Dataset | Source |
|---|---|
| Population (historical + projected, 1950–2100) | **UN World Population Prospects 2024** (medium variant), via Our World in Data |
| Median age (1950–2100) | UN WPP 2024, via Our World in Data |
| Country boundaries | Natural Earth 110m admin-0 |
| IHME comparison | IHME / *The Lancet* (2020) global scenario |

All projections are the UN **medium variant**. The IHME line is an illustrative global trajectory (peak ~9.73 B in 2064, declining to ~8.79 B by 2100).

## Project structure

```
├── index.html          # self-contained dashboard (committed, deploy-ready)
├── template.html       # UI/JS/CSS source with a data placeholder
├── build.py            # fetches OWID data + GeoJSON, regenerates index.html
├── .github/workflows/  # GitHub Pages deploy (on push to main)
└── fable.toml          # Veles / Fable-5 config
```

## Rebuild

```bash
# requires Python 3 (pandas optional; falls back to stdlib csv)
python3 build.py
```

`build.py` downloads the source CSVs into `data/` (git-ignored), preprocesses them into a compact embedded payload, and injects it into `template.html` to produce `index.html`.

## Deploy

Push to `main` — the included GitHub Actions workflow deploys to GitHub Pages automatically. In the repository's **Settings → Pages**, set **Source** to **GitHub Actions**.

---

© H Heuristics · Built with Veles (Fable-5 × DeepSeek)
