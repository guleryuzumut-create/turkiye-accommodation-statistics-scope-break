# -*- coding: utf-8 -*-
"""Downloads geoBoundaries (gbOpen) TUR ADM1 and ADM2 simplified boundaries (ODbL)."""
import json, urllib.request
from pathlib import Path
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
for lvl, name in (("ADM1", "tur_adm1.geojson"), ("ADM2", "tur_adm2.geojson")):
    meta = json.load(urllib.request.urlopen(f"https://www.geoboundaries.org/api/current/gbOpen/TUR/{lvl}/"))
    urllib.request.urlretrieve(meta["simplifiedGeometryGeoJSON"], RAW / name)
    print(lvl, "->", RAW / name)
