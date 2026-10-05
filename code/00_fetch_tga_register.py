# -*- coding: utf-8 -*-
"""Downloads the TGA register of Ministry-certified establishments (public online database)."""
import json, ssl, urllib.parse, urllib.request
from pathlib import Path
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
rows, page = [], 1
while True:
    qs = urllib.parse.urlencode({"belge_turu": "Tümü", "il": "Tümü", "ilce": "Tümü", "page": page, "tesis_adi": "",
                                 "tesis_turu": "Tümü", "tesis_sinifi": "Tümü", "page_size": 1000})
    req = urllib.request.Request("https://cms-backend.tga.gov.tr/api/ktb-accommodation/?" + qs,
                                 headers={"User-Agent": "Mozilla/5.0", "Origin": "https://tga.gov.tr",
                                          "Referer": "https://tga.gov.tr/kultur-ve-turizm-bakanligi-belgeli-konaklama-tesisleri"})
    d = json.load(urllib.request.urlopen(req, context=ctx, timeout=60))["data"]
    rows += d["rows"]
    if page >= d["total_page"]:
        break
    page += 1
out = RAW / "tga_tesis_listesi_2026-10-05.json"   # file name expected by 01_build_panel.py
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(len(rows), "records ->", out)
