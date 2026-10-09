"""Plain-language explanations for each event.

template(event): deterministic sentences built only from the feed's numbers.
add_ai(events):  for serious events, a short "what this means" paragraph from GitHub Models,
                 written from the same facts. Any paragraph containing a number that isn't in
                 the facts is rejected (number_guard), so the AI can't invent figures.
"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

CACHE = Path(__file__).parent.parent / "data" / "ai_cache.json"
MODEL = "openai/gpt-4o-mini"
MAX_NEW_AI_PER_RUN = 12  # shortcut: stays inside the GitHub Models free-tier daily limit; raise with a paid key

ALERT_MEANING = {
    "Green": "Green alert: limited impact expected. Local authorities can usually handle it.",
    "Orange": "Orange alert: significant impact is likely. The affected country may need outside help.",
    "Red": "Red alert: severe impact is likely. International help will probably be needed.",
}
TYPE_NAME = {"EQ": "Earthquake", "TC": "Tropical cyclone", "FL": "Flood", "VO": "Volcano", "DR": "Drought", "WF": "Wildfire"}


def _num(n, digits=0):
    return f"{n:,.{digits}f}"


def _where(e):
    cs = [c for c in e.get("countries") or [] if c]
    if len(cs) > 3:
        return f"{', '.join(cs[:3])} and {len(cs) - 3} other countries"
    return ", ".join(cs) or "a remote area"


def quake(e):
    m, depth = e["magnitude"], e["depth_km"]
    scale = ("Light: people nearby feel it, but damage is rare." if m < 5 else
             "Moderate: it can crack weak buildings close to the center." if m < 6 else
             "Strong: it can seriously damage buildings in towns near the center." if m < 7 else
             "Major: it can cause widespread, serious damage over a large area." if m < 8 else
             "Great: one of the strongest kinds of earthquake, able to destroy communities near the center.")
    depth_note = (f"It was shallow ({depth} km deep), so shaking at the surface is stronger." if depth < 70 else
                  f"It was deep ({depth} km down), which softens the shaking at the surface.")
    lines = {"what": f"A magnitude {m} earthquake struck {e.get('place') or _where(e)}.", "severity": scale + " " + depth_note}
    if e.get("felt_reports"):
        lines["impact"] = f"{_num(e['felt_reports'])} people reported feeling it to the USGS."
    lines["expect"] = "Aftershocks are normal for days to weeks afterward and can knock down already-damaged buildings."
    if e.get("tsunami"):
        lines["expect"] += (" The USGS flags this quake as being in an ocean area where a tsunami is possible. "
                            "That flag is not a warning by itself: follow the local tsunami warning center.")
    return lines


def cyclone(e):
    kmh = e.get("severity") or 0
    mph = kmh / 1.609
    cat = ("a tropical storm (below hurricane strength)" if kmh < 119 else
           "a Category 1 hurricane/typhoon" if kmh < 154 else "a Category 2 hurricane/typhoon" if kmh < 178 else
           "a Category 3 (major) hurricane/typhoon" if kmh < 209 else "a Category 4 (major) hurricane/typhoon" if kmh < 252 else
           "a Category 5 (the strongest) hurricane/typhoon")
    damage = ("Winds can bring down branches and power lines." if kmh < 119 else
              "Winds can damage roofs and cause long power outages." if kmh < 178 else
              "Winds can tear roofs off homes and leave areas without power for weeks.")
    return {
        "what": f"{e['name']} is affecting {_where(e)}.",
        "severity": f"Top winds reach about {_num(kmh)} km/h ({_num(mph)} mph), which makes it {cat}. {damage}",
        "expect": "Near the coast, storm surge (sea water pushed ashore) is usually the deadliest part. Heavy rain can flood "
                  "areas far from the center. The shaded zones on the map show where winds of 60, 90 and 120 km/h are forecast.",
    }


def flood(e):
    return {
        "what": f"Flooding is affecting {_where(e)}.",
        "expect": "Rivers can keep rising for days after the rain stops. Floodwater is often dirty and hides debris; "
                  "just 15 cm (6 inches) of moving water can knock a person down.",
    }


def volcano(e):
    return {
        "what": f"The {e.get('storm_name') or 'volcano'} volcano in {_where(e)} is erupting.",
        "expect": "Volcanic ash makes breathing harder, contaminates water, and can shut down airports. "
                  "Mudflows can race down river valleys even far from the volcano.",
    }


def drought(e):
    lines = {"what": f"A drought is affecting {_where(e)}."}
    if e.get("severity_unit") == "km2" and e.get("severity"):
        km2 = e["severity"]
        lines["severity"] = f"It covers about {_num(km2)} km² ({_num(km2 / 2.59)} square miles) of farmland and pasture."
    lines["expect"] = "Droughts build slowly. The main dangers are failed crops, dying livestock, water shortages and rising food prices."
    return lines


def wildfire(e):
    lines = {"what": f"Wildfires are burning in {_where(e)}."}
    if e.get("severity_unit") == "ha" and e.get("severity"):
        ha = e["severity"]
        lines["severity"] = f"About {_num(ha)} hectares ({_num(ha * 2.471)} acres) have burned, roughly {_num(ha * 1.4)} soccer fields."
    lines["expect"] = "Smoke can travel hundreds of kilometres and is harmful to breathe. Fires can spread fast when it is windy and dry."
    return lines


BUILDERS = {"EQ": quake, "TC": cyclone, "FL": flood, "VO": volcano, "DR": drought, "WF": wildfire}


def template(e):
    lines = BUILDERS[e["type"]](e)
    lines["alert"] = ALERT_MEANING[e["alert"]]
    return lines


# ---------- AI paragraph ----------

def facts(e):
    keys = ("type", "name", "alert", "countries", "place", "start", "magnitude", "depth_km", "tsunami",
            "felt_reports", "severity", "severity_unit", "severity_text")
    f = {k: e[k] for k in keys if e.get(k) not in (None, "", [])}
    f["type"] = TYPE_NAME[e["type"]]
    return f


NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def number_guard(text, fact_dict):
    """True if every number in `text` appears in the facts (allowing rounding)."""
    known = [float(n.replace(",", "")) for n in NUMBER.findall(json.dumps(fact_dict))]
    for n in NUMBER.findall(text):
        v = float(n.replace(",", ""))
        if not any(abs(v - k) <= max(1, 0.02 * k) for k in known):
            return False
    return True


PROMPT = """You explain disasters to the general public at a 6th-grade reading level.
Using ONLY the facts below, write 2-3 short sentences on what this event means for people living there.
Rules: do not add any number that is not in the facts; do not convert units; do not guess deaths, damage costs or forecasts;
do not give medical or evacuation instructions beyond "follow local authorities". No headings, no lists.

Facts:
{facts}"""


def ask_model(fact_dict, token):
    body = json.dumps({"model": MODEL, "temperature": 0.2, "max_tokens": 160,
                       "messages": [{"role": "user", "content": PROMPT.format(facts=json.dumps(fact_dict, indent=1))}]}).encode()
    req = urllib.request.Request("https://models.github.ai/inference/chat/completions", data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError):
        raise ValueError(f"unexpected model response (HTTP {r.status}, {r.headers.get('content-type')}): {raw[:200]!r}")


def wants_ai(e):
    return e["alert"] in ("Orange", "Red") or e["type"] == "TC" or (e["type"] == "EQ" and e["magnitude"] >= 6)


def add_ai(events):
    token = os.environ.get("GITHUB_TOKEN")
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    new = 0
    for e in events:
        if not wants_ai(e):
            continue
        f = facts(e)
        key = e["id"] + ":" + json.dumps(f, sort_keys=True)  # regenerate when the facts change
        if key not in cache and token and new < MAX_NEW_AI_PER_RUN:
            try:
                text = ask_model(f, token)
                new += 1
                cache[key] = text if number_guard(text, f) else None  # None = rejected, don't retry
                if cache[key] is None:
                    print(f"rejected AI text for {e['id']}: {text!r}")
                time.sleep(4)  # free tier allows ~15 requests/minute
            except (OSError, ValueError, KeyError) as err:  # AI is optional: never fail the data run
                print(f"AI skipped for {e['id']}: {err}")
        if cache.get(key):
            e["ai"] = cache[key]
    live = {e["id"] for e in events}
    cache = {k: v for k, v in cache.items() if k.split(":", 1)[0] in live}  # drop ended events
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    print(f"AI paragraphs: {new} new, {sum(1 for e in events if e.get('ai'))} shown")
