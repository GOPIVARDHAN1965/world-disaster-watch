from explain import number_guard, template

FACTS = {"type": "Earthquake", "magnitude": 6.3, "depth_km": 10, "felt_reports": 1520, "countries": ["Vanuatu"]}

# AI text may only use numbers that are in the facts (rounding allowed)
assert number_guard("A magnitude 6.3 quake about 10 km deep; 1,520 people felt it.", FACTS)
assert number_guard("A strong quake shook Vanuatu.", FACTS)
assert not number_guard("At least 40 people were killed.", FACTS)
assert not number_guard("Winds of 140 mph", {"severity": 231.48, "severity_unit": "km/h"})  # unit conversion = invented number
assert number_guard("winds near 231 km/h", {"severity": 231.48, "severity_unit": "km/h"})

# templates turn raw numbers into plain categories
cyc = template({"type": "TC", "name": "Tropical Cyclone SIMON-26", "alert": "Red", "countries": ["Mexico"], "severity": 231.48})
assert "Category 4" in cyc["severity"] and "144 mph" in cyc["severity"], cyc
assert cyc["alert"].startswith("Red alert")

eq = template({"type": "EQ", "alert": "Orange", "magnitude": 6.3, "depth_km": 10, "place": "Vanuatu", "tsunami": True,
               "felt_reports": None, "countries": ["Vanuatu"]})
assert eq["severity"].startswith("Strong") and "shallow" in eq["severity"]
assert "not a warning by itself" in eq["expect"]

wf = template({"type": "WF", "alert": "Green", "countries": ["Indonesia"], "severity": 10733, "severity_unit": "ha"})
assert "26,521 acres" in wf["severity"], wf
print("ok")
