# -*- coding: utf-8 -*-
"""Ulusal makale şekilleri (İngilizce etiketler, Garamond)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Patch
from matplotlib.collections import PatchCollection

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = str(ROOT / "output"); E = str(RAW)
plt.rcParams.update({'font.family': 'Garamond', 'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
INK = '#222222'; MUTED = '#9a9a9a'; LIGHT = '#e6e6e6'; ACC = '#b2412f'; ACC2 = '#e3a79b'
R = json.load(open(os.path.join(OUT, 'sonuclar.json'), encoding='utf-8'))
act = json.load(open(os.path.join(OUT, 'ilce_analiz.json'), encoding='utf-8'))
A = {(r['il'], r['ilce']): r for r in act}

# ---------------------------------------------------------------- Şekil 1: harita
g2 = json.load(open(os.path.join(E, 'tur_adm2.geojson'), encoding='utf-8'))
g1 = json.load(open(os.path.join(E, 'tur_adm1.geojson'), encoding='utf-8'))
match = {m['shapeID']: m for m in json.load(open(os.path.join(OUT, 'harita_eslesme.json'), encoding='utf-8'))}

def polys(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates'][0]]
    return [p[0] for p in geom['coordinates']]

cats = {'gone': ACC, 'back': ACC2, 'stay': '#7d7d7d', 'none': '#f2f2f2'}
counts = {k: 0 for k in cats}
fig, ax = plt.subplots(figsize=(6.3, 3.7), dpi=300)
patches = []; colors = []
for f in g2['features']:
    m = match.get(f['properties']['shapeID'])
    r = A.get(tuple(m['key'])) if m and m['key'] else None
    if r is None or r['t22'] <= 0:
        c = 'none'
    elif r['gone_all']:
        c = 'gone'
    elif r['gone_2023']:
        c = 'back'
    else:
        c = 'stay'
    counts[c] += 1
    for ring in polys(f['geometry']):
        patches.append(MPoly(np.array(ring), closed=True)); colors.append(cats[c])
pc = PatchCollection(patches, facecolor=colors, edgecolor='white', linewidth=0.15)
ax.add_collection(pc)
prov_patches = [MPoly(np.array(ring), closed=True) for f in g1['features'] for ring in polys(f['geometry'])]
ax.add_collection(PatchCollection(prov_patches, facecolor='none', edgecolor='#555555', linewidth=0.35))
ax.set_xlim(25.6, 44.9); ax.set_ylim(35.75, 42.2)
fig.subplots_adjust(bottom=0.2); ax.set_aspect(1.25); ax.axis('off')
ax.legend(handles=[Patch(color=ACC, label=f'Disappeared 2023–2025 ({R["districts"]["gone_all"]} districts)'),
                   Patch(color=ACC2, label=f'Disappeared in 2023, reappeared by 2025 ({R["districts"]["back2025"]})'),
                   Patch(color='#7d7d7d', label='Remained in the official series'),
                   Patch(facecolor='#f2f2f2', edgecolor='#bbbbbb', label='No overnight stays recorded in 2022')],
          loc='upper center', fontsize=7.5, frameon=False, ncol=2, bbox_to_anchor=(0.5, 0.02))
fig.savefig(os.path.join(OUT, 'fig1_map.png'), bbox_inches='tight'); plt.close()
print('harita kategorileri (poligon):', counts)

# ---------------------------------------------------------------- Şekil 2: aktif ilçe sayısı ve SEGE dilimleri
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.3, 2.7), dpi=300, gridspec_kw={'width_ratios': [1.35, 1]})
yrs = list(range(2015, 2027)); val = [R['districts']['active'][str(y)] for y in yrs]
cols = [MUTED if y <= 2022 else INK for y in yrs]
a1.bar(yrs, val, color=cols, width=0.65)
for y, v in zip(yrs, val):
    a1.text(y, v + 6, str(v), ha='center', fontsize=7)
a1.set_ylim(550, 820); a1.set_xticks(yrs); a1.set_xticklabels([str(y)[2:] for y in yrs], fontsize=8)
a1.axvline(2022.5, color=INK, lw=0.8, ls='--')
a1.set_ylabel('Districts with recorded stays', fontsize=9)
a1.set_title('(a) Districts in the official series', fontsize=9.5)
a1.text(2026.4, 812, '2026: Jan–Jul', fontsize=7, ha='right', color=MUTED)
q = R['gone_by_sege_q']
labs = ['Q1\nleast\ndeveloped', 'Q2', 'Q3', 'Q4\nmost\ndeveloped']
rates = [x['rate'] * 100 for x in q]
a2.bar(range(4), rates, color=[ACC, ACC2, MUTED, MUTED], width=0.6)
for i, x in enumerate(q):
    a2.text(i, rates[i] + 0.7, f"{rates[i]:.1f}%\n({x['gone']}/{x['n']})", ha='center', fontsize=7)
a2.set_xticks(range(4)); a2.set_xticklabels(labs, fontsize=7.5); a2.set_ylim(0, 31)
a2.set_ylabel('Share disappeared 2023–2025 (%)', fontsize=9)
a2.set_title('(b) By SEGE-2022 development quartile', fontsize=9.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig2_districts.png')); plt.close()

# ---------------------------------------------------------------- Şekil 3: il düzeyinde yayımlanan ve düzeltilmiş değişim
prov = json.load(open(os.path.join(OUT, 'il_tablosu.json'), encoding='utf-8'))
x = np.array([p['pub'] for p in prov]); y = np.array([p['adj_seas'] for p in prov]); yf = np.array([p['adj_flat'] for p in prov])
fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=300)
lo, hi = -70, 60
ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.8, ls='--'); ax.axhline(0, color=LIGHT, lw=0.8); ax.axvline(0, color=LIGHT, lw=0.8)
for xi, yi, yfi in zip(x, y, yf):
    ax.plot([xi, xi], [min(yi, yfi), max(yi, yfi)], color='#cccccc', lw=0.7, zorder=1)
ax.scatter(x, y, s=12, color=INK, zorder=3, label='Conversion-adjusted (seasonal)')
ax.scatter(x, yf, s=12, facecolor='white', edgecolor=INK, lw=0.6, zorder=2, label='Conversion-adjusted (flat)')
for p in prov:
    NAMES = {'BİTLİS': 'Bitlis', 'ANTALYA': 'Antalya', 'İSTANBUL': 'Istanbul', 'HAKKARİ': 'Hakkari', 'ARTVİN': 'Artvin', 'NİĞDE': 'Niğde'}
    if p['il'] in NAMES:
        OFF = {'Hakkari': (-6, -12), 'Artvin': (5, -10), 'Istanbul': (4, -11), 'Bitlis': (4, 5)}
        ax.annotate(NAMES[p['il']], (p['pub'], p['adj_seas']), xytext=OFF.get(NAMES[p['il']], (4, 3)), textcoords='offset points', fontsize=7.5)
ax.set_xlim(lo, 45); ax.set_ylim(-60, 100)
ax.set_xlabel('Published change, 2022–2023 (%)'); ax.set_ylabel('Scope-consistent change, 2022–2023 (%)')
ax.legend(fontsize=7.5, frameon=False, loc='upper left')
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig3_provinces.png')); plt.close()
print('ok')
