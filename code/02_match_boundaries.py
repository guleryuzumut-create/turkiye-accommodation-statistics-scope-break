# -*- coding: utf-8 -*-
"""geoBoundaries ADM2 poligonlarını il-ilçe anahtarlarına eşler (nokta-poligon testiyle)."""
import json, os, re
import numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
E = str(RAW); OUT = str(ROOT / "output")


def up(s):
    s = str(s).strip().replace('i', 'İ').replace('ı', 'I').upper()
    for a, b in (('Â', 'A'), ('Î', 'İ'), ('Û', 'U')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s)


def rings(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates'][0]]
    return [p[0] for p in geom['coordinates']]


def area(r):
    x = np.array([p[0] for p in r]); y = np.array([p[1] for p in r])
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def centroid(geom):
    r = max(rings(geom), key=area)
    a = np.array(r)
    # gerçek merkez noktası yerine poligon içinde kalması olası bir nokta: kütle merkezi
    x, y = a[:, 0], a[:, 1]
    cross = x * np.roll(y, -1) - np.roll(x, -1) * y
    A = cross.sum() / 2
    if abs(A) < 1e-12:
        return a.mean(0)
    cx = ((x + np.roll(x, -1)) * cross).sum() / (6 * A); cy = ((y + np.roll(y, -1)) * cross).sum() / (6 * A)
    return np.array([cx, cy])


def pip(pt, ring):
    x, y = pt; a = np.array(ring); xi, yi = a[:, 0], a[:, 1]; xj, yj = np.roll(xi, 1), np.roll(yi, 1)
    cond = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi)
    return cond.sum() % 2 == 1


g2 = json.load(open(os.path.join(E, 'tur_adm2.geojson'), encoding='utf-8'))
g1 = json.load(open(os.path.join(E, 'tur_adm1.geojson'), encoding='utf-8'))
P = [(up(f['properties']['shapeName']), rings(f['geometry'])) for f in g1['features']]
panel = json.load(open(os.path.join(OUT, 'ilce_panel.json'), encoding='utf-8'))
keys = {(r['il'], r['ilce']) for r in panel}
FIX = {'AFYONKARAHİSAR (MERKEZ İLÇE)': 'MERKEZ', 'GEDİZ MERKEZ': 'GEDİZ', 'GİRESUN DİSTRİCT': 'MERKEZ', 'ILIÇ': 'İLİÇ'}
REV = {('AFYONKARAHİSAR', 'BAŞMAKÇI'): 'BAŞMAKCI', ('AFYONKARAHİSAR', 'SİNANPAŞA'): 'SİNANPAŞA (SİNCANLI)',
       ('ORDU', 'KABADÜZ'): 'KABADÜZ (KARADÜZ)', ('SAMSUN', '19 MAYIS'): 'ONDOKUZ MAYIS',
       ('TEKİRDAĞ', 'MARMARAEREĞLİSİ'): 'MARMARA EREĞLİSİ', ('ISPARTA', 'ŞARKİKARAAĞAÇ'): 'ŞARKİKARAAĞAÇ'}
byname = {}
for (a, b) in keys:
    byname.setdefault(b, []).append(a)
res = []; unmatched = []
for f in g2['features']:
    c = centroid(f['geometry'])
    prov = None
    for name, rs in P:
        if any(pip(c, r) for r in rs):
            prov = name; break
    if prov is None:  # en yakın il (kıyıdaki küçük adalar vb.)
        d = [(np.min(np.hypot(np.array(r)[:, 0] - c[0], np.array(r)[:, 1] - c[1])), name) for name, rs in P for r in rs]
        prov = min(d)[1]
    nm = up(f['properties']['shapeName'])
    nm = FIX.get(nm, nm)
    cand = [nm]
    if 'MERKEZ' in nm or nm == prov:
        cand.append('MERKEZ')
    nm2 = nm.replace(' MERKEZ', '').strip()
    cand.append(nm2)
    key = None
    for cnd in cand:
        cnd = REV.get((prov, cnd), cnd)
        if (prov, cnd) in keys:
            key = (prov, cnd); break
    if key is None and nm != 'MERKEZ' and len(byname.get(nm, [])) == 1:
        key = (byname[nm][0], nm)
    res.append(dict(shapeID=f['properties']['shapeID'], name=f['properties']['shapeName'], il=prov, key=list(key) if key else None))
    if not key:
        unmatched.append((prov, nm))
print('poligon', len(res), 'eşlenen', sum(1 for r in res if r['key']), 'eşlenemeyen', len(unmatched))
print(unmatched[:60])
# panelde 2022 aktif olup poligonu olmayan
mk = {tuple(r['key']) for r in res if r['key']}
act = [(r['il'], r['ilce'], r['t22']) for r in panel if r['t22'] > 0 and (r['il'], r['ilce']) not in mk]
print('2022 aktif ama poligonsuz', len(act), sorted(act, key=lambda x: -x[2])[:20])
json.dump(res, open(os.path.join(OUT, 'harita_eslesme.json'), 'w', encoding='utf-8'), ensure_ascii=False)
