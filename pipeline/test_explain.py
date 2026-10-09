from explain import template

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
