# -*- coding: utf-8 -*-
"""Parses district SEGE-2022 scores (Annex 1) from the PDF into JSON. Requires PyMuPDF."""
import json, re
from pathlib import Path
import pymupdf
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
d = pymupdf.open(RAW / "sege2022_ilce_kademe.pdf")
lines = [l.strip() for p in d for l in p.get_text().split("\n") if l.strip()]
i = lines.index("Ek-1: İlçelerin Sosyo-Ekonomik Gelişmişlik Sıralaması")
j = lines.index("Ek-2: İlçelerin İl Bazında Sosyo-Ekonomik Gelişmişlik Sıralamaları")
L, out, k = lines[i:j], [], 0
while k < len(L) - 3:
    if re.fullmatch(r"\d+", L[k]) and re.fullmatch(r"-?\d+,\d+", L[k + 3]) and not re.fullmatch(r"\d+", L[k + 1]):
        out.append({"il": L[k + 1], "ilce": L[k + 2], "sira": int(L[k]), "skor": float(L[k + 3].replace(",", "."))}); k += 4
    else:
        k += 1
json.dump(out, open(RAW / "sege2022_ilce.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "districts")
