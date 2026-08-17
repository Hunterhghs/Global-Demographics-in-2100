#!/usr/bin/env python3
"""
Global Demographics in 2100 — dashboard build script.

Downloads (or reuses cached) Our World in Data / UN World Population Prospects 2024
data, preprocesses it into a compact embedded payload, and injects it into
template.html to produce a fully self-contained index.html.

Data sources:
  - UN World Population Prospects 2024 (medium variant), via Our World in Data
    https://ourworldindata.org/grapher/population-with-un-projections
    https://ourworldindata.org/grapher/population-regions-with-projections
    https://ourworldindata.org/grapher/median-age
  - Natural Earth 110m admin-0 country boundaries (GeoJSON)
"""
import json, math, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

SOURCES = {
    "population-countries.csv": "https://ourworldindata.org/grapher/population-with-un-projections.csv",
    "population-regions.csv":   "https://ourworldindata.org/grapher/population-regions-with-projections.csv",
    "median-age.csv":           "https://ourworldindata.org/grapher/median-age.csv",
    "fertility.csv":            "https://ourworldindata.org/grapher/children-per-woman-un.csv",
    "world-countries.geojson":  "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson",
}

REGIONS = {
    "UN_AFR": {"name": "Africa",                         "short": "Africa"},
    "UN_ASI": {"name": "Asia",                           "short": "Asia"},
    "UN_EUR": {"name": "Europe",                         "short": "Europe"},
    "UN_LAC": {"name": "Latin America & Caribbean",      "short": "LatAm & Caribbean"},
    "UN_NAM": {"name": "Northern America",               "short": "N. America"},
    "UN_OCE": {"name": "Oceania",                        "short": "Oceania"},
}

# 5-year steps 1950..2100 (inclusive) = 31 points
YEARS5 = list(range(1950, 2101, 5))


def fetch():
    DATA.mkdir(exist_ok=True)
    for fname, url in SOURCES.items():
        dest = DATA / fname
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        print(f"  ↓ {fname}")
        urllib.request.urlretrieve(url, dest)
    print("  ✓ data present")


def read_csv(fname):
    import csv
    rows = []
    with open(DATA / fname, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def to_num(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def pop1000(v):
    """Population in thousands, rounded to int."""
    if v is None:
        return None
    return int(round(v / 1000.0))


def build_region_series(rows):
    """Yearly population (thousands) for world + 6 UN regions, 1950-2100."""
    table = {}
    for r in rows:
        code = (r.get("Code") or "").strip()
        if code not in REGIONS and r.get("Entity") != "World":
            continue
        y = int(float(r["Year"]))
        if y < 1950 or y > 2100:
            continue
        p = to_num(r.get("Population"))
        if p is None:
            continue
        key = code if code in REGIONS else "WLD"
        table.setdefault(key, {})[y] = pop1000(p)
    out = {}
    for key, d in table.items():
        years = sorted(d)
        full = [d.get(y) for y in years]
        full_years = years
        # 5-year downsample
        d5 = {y: d.get(y) for y in YEARS5 if y in d}
        out[key] = {
            "fullYears": full_years,
            "full": full,
            "years5": [y for y in YEARS5 if y in d5],
            "v5": [d5[y] for y in YEARS5 if y in d5],
        }
    return out


def build_median_series(rows):
    """Median age (1 decimal) for world + regions, 1950-2100."""
    out = {}
    for r in rows:
        code = (r.get("Code") or "").strip()
        key = code if code in REGIONS else ("WLD" if r.get("Entity") == "World" else None)
        if key is None:
            continue
        y = int(float(r["Year"]))
        if y < 1950 or y > 2100:
            continue
        hist = to_num(r.get("Median age"))
        proj = to_num(r.get("Median age (Projected)"))
        v = proj if proj is not None else hist
        if v is None:
            continue
        out.setdefault(key, {})[y] = round(v, 1)
    result = {}
    for key, d in out.items():
        # yearly but downsampled to 5yr for compactness
        result[key] = {"years5": [y for y in YEARS5 if y in d],
                       "v5": [d[y] for y in YEARS5 if y in d],
                       "now": d.get(2024),
                       "end": d.get(2100)}
    return result


def build_tfr(rows):
    """World fertility rate: historical 1950-2023 + UN projected anchors."""
    yrs, vals = [], []
    for r in rows:
        if r.get("Entity") != "World":
            continue
        y = int(float(r["Year"]))
        v = to_num(r.get("Fertility rate"))
        if v is None:
            continue
        yrs.append(y); vals.append(round(v, 2))
    # sort by year
    pairs = sorted(zip(yrs, vals))
    return {"years": [p[0] for p in pairs], "v": [p[1] for p in pairs]}


def build_countries(rows, geojson_lookup):
    """Country-level population (thousands) on 5yr steps, 1950-2100."""
    import re
    iso3_re = re.compile(r"^[A-Z]{3}$")
    series = {}
    names = {}
    for r in rows:
        code = (r.get("Code") or "").strip()
        if not iso3_re.match(code):
            continue
        y = int(float(r["Year"]))
        if y < 1950 or y > 2100:
            continue
        hist = to_num(r.get("Population"))
        proj = to_num(r.get("Population (Projected)"))
        v = proj if proj is not None else hist
        if v is None:
            continue
        series.setdefault(code, {})[y] = v
        names.setdefault(code, r.get("Entity", code))

    out = {}
    for code, d in series.items():
        v5 = [pop1000(d.get(y)) for y in YEARS5 if y in d]
        if not v5:
            continue
        p2024 = d.get(2024)
        p2100 = d.get(2100)
        grow = None
        if p2024 and p2100 and p2024 > 0:
            grow = round((p2100 - p2024) / p2024 * 100.0, 1)
        g = geojson_lookup.get(code)
        out[code] = {
            "name": names.get(code, code),
            "region": g["region"] if g else None,
            "v5": v5,
            "p2024": pop1000(p2024) if p2024 else None,
            "p2100": pop1000(p2100) if p2100 else None,
            "grow": grow,
        }
    return out


def load_geojson():
    g = json.load(open(DATA / "world-countries.geojson"))
    lookup = {}
    feats = []
    for f in g["features"]:
        p = f.get("properties", {})
        iso = (p.get("ISO_A3_EH") or p.get("ISO_A3") or "").strip()
        if not iso or iso == "-99":
            # Norway / France have -99 in ISO_A3 but valid ISO_A3_EH; skip if still missing
            continue
        name = p.get("NAME") or p.get("ADMIN") or iso
        region = region_from_ne(p.get("REGION_UN"), p.get("SUBREGION"))
        # slim geometry: round coords to 2 decimals
        geom = f.get("geometry")
        slim = slim_geometry(geom)
        feats.append({"type": "Feature",
                      "properties": {"iso": iso, "name": name, "region": region},
                      "geometry": slim})
        lookup[iso] = {"name": name, "region": region}
    return feats, lookup


def region_from_ne(region_un, subregion):
    if region_un == "Africa":
        return "UN_AFR"
    if region_un == "Asia":
        return "UN_ASI"
    if region_un == "Europe":
        return "UN_EUR"
    if region_un == "Oceania":
        return "UN_OCE"
    if region_un == "Americas":
        return "UN_NAM" if (subregion or "") == "Northern America" else "UN_LAC"
    return None


def slim_geometry(geom):
    if geom is None:
        return None
    t = geom.get("type")
    if t == "Polygon":
        return {"type": t, "coordinates": [[[round(c[0], 2), round(c[1], 2)] for c in ring] for ring in geom["coordinates"]]}
    if t == "MultiPolygon":
        return {"type": t, "coordinates": [[[[round(c[0], 2), round(c[1], 2)] for c in ring] for ring in poly] for poly in geom["coordinates"]]}
    return geom


def main():
    fetch()
    print("Reading CSVs…")
    region_rows = read_csv("population-regions.csv")
    country_rows = read_csv("population-countries.csv")
    median_rows = read_csv("median-age.csv")
    tfr_rows = read_csv("fertility.csv")

    print("Processing GeoJSON…")
    geojson_feats, geojson_lookup = load_geojson()

    print("Building series…")
    regions = build_region_series(region_rows)
    median = build_median_series(median_rows)
    tfr = build_tfr(tfr_rows)
    countries = build_countries(country_rows, geojson_lookup)

    # World headline numbers (from full yearly world series)
    world_full = regions.get("WLD", {})
    wfull = dict(zip(world_full.get("fullYears", []), world_full.get("full", [])))
    if wfull:
        peak_year = max(wfull, key=lambda y: wfull[y])
        world_meta = {
            "p2024": wfull.get(2024),
            "p2050": wfull.get(2050),
            "p2100": wfull.get(2100),
            "peak": wfull[peak_year],
            "peakYear": peak_year,
            "p1950": wfull.get(1950),
        }
    else:
        world_meta = {}

    # Region rollup (for ledger / chart labels)
    region_list = []
    for code, meta in REGIONS.items():
        d = regions.get(code, {})
        full = dict(zip(d.get("fullYears", []), d.get("full", [])))
        region_list.append({
            "code": code,
            "name": meta["name"],
            "p2024": full.get(2024),
            "p2050": full.get(2050),
            "p2100": full.get(2100),
        })

    # IHME (Lancet, 2020) scenario — illustrative global trajectory for comparison
    ihme = [
        [2024, 8.16], [2030, 8.52], [2040, 9.02], [2050, 9.42], [2060, 9.68],
        [2064, 9.73], [2070, 9.61], [2080, 9.26], [2090, 8.97], [2100, 8.79],
    ]

    payload = {
        "meta": {
            "years5": YEARS5,
            "world": world_meta,
            "regions": region_list,
            "ihme": ihme,
            "title": "Global Demographics in 2100",
            "source": "UN World Population Prospects 2024 · Our World in Data",
        },
        "regions": {k: v for k, v in regions.items() if k != "WLD"},
        "world": world_full.get("v5", []),
        "median": median,
        "tfr": tfr,
        "countries": countries,
        "geo": geojson_feats,
    }

    (DATA / "payload.json").write_text(json.dumps(payload, separators=(",", ":")))
    print(f"  countries: {len(countries)}")
    print(f"  geojson features: {len(geojson_feats)}")
    print(f"  world 2024={world_meta.get('p2024')}k  peak={world_meta.get('peak')}k@{world_meta.get('peakYear')}  2100={world_meta.get('p2100')}k")

    # Inject into template
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    marker = "/*__PAYLOAD__*/"
    if marker not in tpl:
        print("ERROR: template.html missing marker", marker)
        sys.exit(1)
    injected = json.dumps(payload, separators=(",", ":"))
    out_html = tpl.replace(marker, injected, 1)
    (ROOT / "index.html").write_text(out_html, encoding="utf-8")
    print(f"  ✓ wrote index.html ({len(out_html):,} bytes)")


if __name__ == "__main__":
    main()
