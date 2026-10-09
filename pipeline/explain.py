"""Plain-language explanations for each event, built only from the feed's own numbers."""

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
