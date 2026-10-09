# World Disaster Watch

A live map of active disasters worldwide (tropical cyclones, earthquakes, floods, wildfires,
volcanoes and droughts) with each event explained in plain language and a 7-day weather
forecast for the affected spot.

**Live:** https://gopivardhan1965.github.io/world-disaster-watch/

![Tropical cyclone with forecast wind zones and its plain-language card](docs/screenshot.png)

## How it works

```
GDACS (UN / European Commission) ─┐                        ┌─ docs/data/events.json
USGS earthquakes (M4.5+, 7 days) ──┼─► pipeline/fetch.py ──┤
GitHub Models (free tier) ─────────┘   + explain.py        └─ docs/data/cyclones.geojson
                                                                     │
                       docs/index.html (Leaflet map) ◄───────────────┘
                                 ▲
                                 └── Open-Meteo forecast, fetched in the browser on click
```

- **Hourly refresh.** A GitHub Actions workflow fetches every current GDACS event and the last
  7 days of USGS earthquakes, then redeploys the static site. USGS quakes are joined to GDACS
  impact alerts by event ID. If every feed comes back nearly empty, the run fails instead of
  publishing an empty map.
- **Plain-language explanations, two layers.**
  1. *Templates* turn the official numbers into sentences: magnitude into "Strong: it can
     seriously damage buildings…", wind speed into a hurricane category and what those winds
     do, burned hectares into acres and soccer fields, and alert levels into what they mean.
  2. *AI paragraph* (Orange/Red alerts, all cyclones, quakes M6+). GitHub Models writes 2–3
     sentences from the same facts only. A **number guard** rejects any paragraph containing a
     number that isn't in the official data (rounding allowed), so it can't invent death tolls
     or convert units wrongly. Accepted paragraphs are cached per event and regenerated only
     when the facts change, to stay inside the free tier.
- **Forecasts come from official sources:** GDACS/NOAA cyclone wind zones (60/90/120 km/h)
  and tracks, and the Open-Meteo weather forecast at the event location, with plain notes for
  heavy rain, gale-force wind and dangerous heat. The app does not make its own disaster
  predictions.

## Run locally

Standard library only, Python 3.10+:

```bash
python pipeline/test_explain.py
GITHUB_TOKEN=... python pipeline/fetch.py   # token optional: without it, templates only
python -m http.server -d docs               # http://localhost:8000
```

Not an official warning service. Always follow local authorities.
Data: GDACS, USGS, Open-Meteo; map © OpenStreetMap contributors.
