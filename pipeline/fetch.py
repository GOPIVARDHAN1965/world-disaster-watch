"""Fetch active disasters worldwide and write the app's data files.

Sources (all public, no keys):
- GDACS (UN/EU Global Disaster Alert and Coordination System): cyclones, floods,
  volcanoes, droughts, wildfires, plus alert levels for earthquakes
- USGS: earthquakes M4.5+ in the past 7 days (tsunami flag, felt reports, PAGER alert)

Writes docs/data/events.json (one list for the map + cards) and
docs/data/cyclones.geojson (forecast tracks and wind zones).
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import explain  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "docs" / "data"
GDACS = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP?eventtype={}"
USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
GDACS_TYPES = ["TC", "FL", "VO", "DR", "WF", "EQ"]
ALERT_RANK = {"Green": 1, "Orange": 2, "Red": 3}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "world-disaster-watch (github.com/GOPIVARDHAN1965)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except OSError as e:
            if attempt == 2:
                raise
            print(f"retry {url}: {e}")
            time.sleep(5)


def gdacs_events():
    """Centroid feature per event, plus cyclone track/wind-zone features."""
    events, cyclone_shapes = {}, []
    for t in GDACS_TYPES:
        for f in get(GDACS.format(t))["features"]:
            p = f["properties"]
            if p.get("iscurrent") != "true":
                continue
            if f["geometry"]["type"] == "Point" and p.get("Class") in (None, "Point_Centroid"):
                events[(t, p["eventid"])] = f
            elif t == "TC" and (p.get("Class", "").startswith("Poly_") or p.get("Class", "").startswith("Line_")):
                cyclone_shapes.append({"type": "Feature", "geometry": f["geometry"], "properties": {
                    "eventid": p["eventid"], "kind": p["Class"], "label": p.get("polygonlabel")}})
    return events, cyclone_shapes


def from_gdacs(f):
    p = f["properties"]
    lon, lat = f["geometry"]["coordinates"][:2]
    sev = p.get("severitydata") or {}
    countries = [c["countryname"] for c in p.get("affectedcountries") or []] or [p.get("country")]
    name = p["name"].replace("  ", " ")
    if p["eventtype"] == "VO" and p.get("eventname"):
        name = f"{p['eventname']} volcano"
    elif len(countries) > 3:  # e.g. a drought spanning 30 European countries
        name = f"{explain.TYPE_NAME[p['eventtype']]} in {countries[0]}, {countries[1]} and {len(countries) - 2} other countries"
    return {
        "id": f"gdacs-{p['eventtype']}-{p['eventid']}",
        "type": p["eventtype"],
        "name": name,
        "storm_name": p.get("eventname") or None,
        "alert": p["alertlevel"],
        "lat": round(lat, 3), "lon": round(lon, 3),
        "countries": countries,
        "start": p["fromdate"] + "Z", "end": p["todate"] + "Z", "updated": p["datemodified"] + "Z",
        "severity": sev.get("severity"), "severity_unit": sev.get("severityunit"), "severity_text": (sev.get("severitytext") or "").strip(),
        "source": p.get("source"), "source_id": p.get("sourceid"),
        "gdacs_eventid": p["eventid"],
        "report_url": p["url"]["report"],
    }


def from_usgs(f, gdacs_alerts):
    p = f["properties"]
    lon, lat, depth = f["geometry"]["coordinates"]
    return {
        "id": f"usgs-{f['id']}",
        "type": "EQ",
        "name": p["title"],
        "storm_name": None,
        # GDACS rates human impact; fall back to Green for quakes GDACS didn't score
        "alert": gdacs_alerts.get(f["id"], "Green"),
        "lat": round(lat, 3), "lon": round(lon, 3),
        "countries": [p["place"].split(", ")[-1]] if p.get("place") else [],
        "place": p.get("place"),
        "start": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated": datetime.fromtimestamp(p["updated"] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "magnitude": p["mag"], "depth_km": round(depth),
        "tsunami": bool(p.get("tsunami")), "felt_reports": p.get("felt"), "pager_alert": p.get("alert"),
        "source": "USGS", "report_url": p["url"],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gdacs, cyclone_shapes = gdacs_events()
    eq_alerts = {f["properties"].get("sourceid"): f["properties"]["alertlevel"]
                 for (t, _), f in gdacs.items() if t == "EQ" and f["properties"].get("sourceid")}
    events = [from_gdacs(f) for (t, _), f in gdacs.items() if t != "EQ"]  # quakes come from USGS (richer detail)
    events += [from_usgs(f, eq_alerts) for f in get(USGS)["features"]]
    if len(events) < 20:  # every feed down at once is an outage, not a quiet planet
        sys.exit(f"only {len(events)} events fetched, refusing to overwrite the site data")

    for e in events:
        e["explain"] = explain.template(e)
    explain.add_ai(events)

    events.sort(key=lambda e: e["start"], reverse=True)          # newest first...
    events.sort(key=lambda e: ALERT_RANK[e["alert"]], reverse=True)  # ...within each alert level (stable sort)
    (OUT / "events.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "events": events}, separators=(",", ":")))
    (OUT / "cyclones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": cyclone_shapes}, separators=(",", ":")))
    counts = {}
    for e in events:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    print(f"{len(events)} events {counts}, {len(cyclone_shapes)} cyclone shapes")


if __name__ == "__main__":
    main()
