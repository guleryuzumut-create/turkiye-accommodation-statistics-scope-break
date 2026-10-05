# -*- coding: utf-8 -*-
"""Ulusal makale veri seti: ilçe ve il düzeyinde birleşik panel."""
import openpyxl, glob, os, json, calendar, collections, re
import numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
V = str(RAW / "ktb")
E = str(RAW)
OUT = str(ROOT / "output")
os.makedirs(OUT, exist_ok=True)


def up(s):
    s = str(s).strip().replace('i', 'İ').replace('ı', 'I').upper()
    return re.sub(r'\s+', ' ', s)


def wb(path):
    return openpyxl.load_workbook(path, read_only=True, data_only=True)

# ---------------------------------------------------------------- 1) aylık seri
nat = wb(glob.glob(os.path.join(V, '2015-2026*.xlsx'))[0])
M = {}  # (il, ilce) -> year -> list of 12 dicts or None
for y in nat.sheetnames:
    Y = int(y)
    for r in nat[y].iter_rows(values_only=True):
        if not r[0] or not r[1] or r[0] == 'İL':
            continue
        n = min(12, (len(r) - 2) // 8)
        months = []
        for m in range(n):
            v = r[2 + m * 8: 2 + m * 8 + 8]
            if not isinstance(v[5], (int, float)):
                months.append(None)
                continue
            months.append(dict(gel=v[2] or 0, gyer=v[3] or 0, gyab=v[4] or 0, gec=v[5] or 0, dol=v[7] or 0))
        M.setdefault((up(r[0]), up(r[1])), {})[Y] = months


def annual(key, Y, fld='gec', months=None):
    ms = M.get(key, {}).get(Y)
    if not ms:
        return 0
    return sum((x or {}).get(fld, 0) for i, x in enumerate(ms) if (months is None or i in months))


def capacity(key, Y, months=None):
    """Doluluktan geri hesaplanan ortalama yatak (yatak-gün / gün)."""
    ms = M.get(key, {}).get(Y)
    if not ms:
        return 0.0
    bd = 0.0; days = 0
    for i, x in enumerate(ms):
        if months is not None and i not in months:
            continue
        d = calendar.monthrange(Y, i + 1)[1]; days += d
        if x and x['gec'] > 0 and x['dol'] > 0:
            bd += x['gec'] / (x['dol'] / 100.0)
    return bd / days if days else 0.0

districts = sorted(M)
ALIAS = {('AFYONKARAHİSAR', 'BAŞMAKCI'): ('AFYONKARAHİSAR', 'BAŞMAKÇI'),
         ('AFYONKARAHİSAR', 'SİNANPAŞA (SİNCANLI)'): ('AFYONKARAHİSAR', 'SİNANPAŞA'),
         ('ESKİŞEHİR', 'MİHALIÇCIK'): ('ESKİŞEHİR', 'MİHALIÇÇIK'),
         ('ORDU', 'KABADÜZ (KARADÜZ)'): ('ORDU', 'KABADÜZ'),
         ('SAMSUN', 'ONDOKUZ MAYIS'): ('SAMSUN', '19 MAYIS'),
         ('TEKİRDAĞ', 'MARMARA EREĞLİSİ'): ('TEKİRDAĞ', 'MARMARAEREĞLİSİ'),
         ('İSTANBUL', 'BÜYÜKADA'): ('İSTANBUL', 'ADALAR'),
         ('İZMİR', 'ALSANCAK'): ('İZMİR', 'KONAK')}

# ---------------------------------------------------------------- 2) 2022 bültenleri (ilçe)
def bulletin(path, sheet='İl İlçe'):
    rows = list(wb(path)[sheet].iter_rows(values_only=True))
    res = {}; cur = None
    for r in rows[3:]:
        if r[0] and str(r[0]).strip() and 'GENEL' not in str(r[0]).upper():
            cur = up(r[0])
        if not r[1] or not cur or r[7] is None:
            continue
        name = up(r[1])
        if name == 'TOPLAM':
            continue
        res[(cur, name)] = dict(gel=r[4], gec=r[7], gec_yab=r[5], dol=r[13])
    return res

BEL = bulletin(os.path.join(V, '2022 YILI BELEDİYE BELGELİ KONAKLAMA İSTATİSTİKLERİ BÜLTENİ.xlsx'))
ISL = bulletin(os.path.join(V, '2022 YILI İŞLETME BELGELİ KONAKLAMA İSTATİSTİKLER BÜLTENİİ.xlsx'))

# basit (Aralık, il)
rows = list(wb(os.path.join(V, 'ARALIK 2022 BASİT BELGELİ KONAKLAMA İSTATİSTİKLERİ BÜLTENİ.xlsx'))['İl'].iter_rows(values_only=True))
BAS_DEC_IL = {up(r[0]): r[6] for r in rows[3:] if r[0] and r[6] is not None and 'TOPLAM' not in str(r[0]).upper()}

# ---------------------------------------------------------------- 3) TGA tesis listesi
tga = json.load(open(os.path.join(E, 'tga_tesis_listesi_2026-10-05.json'), encoding='utf-8'))
TGA = collections.defaultdict(lambda: collections.Counter())
for x in tga:
    k = (up(x['Sehir']), up(x['Ilce']))
    t = x['BelgeTuru']
    TGA[k][t] += 1
    if t == 'BASİT KONAKLAMA' and str(x.get('BelgeNo', ''))[:4] in ('2021', '2022'):
        TGA[k]['BASIT_GECIS'] += 1

# ---------------------------------------------------------------- 4) SEGE-2022 ilçe
sege = {(up(r['il']), up(r['ilce'])): r for r in json.load(open(os.path.join(E, 'sege2022_ilce.json'), encoding='utf-8'))}

# ---------------------------------------------------------------- 5) kapasite kaydı (il -> bölge)
REG = {up(r['province']): r['region'] for _, r in __import__('pandas').read_csv(os.path.join(E, 'il_bolge.csv')).iterrows()}

# ---------------------------------------------------------------- 6) ilçe tablosu
D = []
unmatched = collections.Counter()
for k in districts:
    il, ilce = k
    t22 = annual(k, 2022)
    nd22 = annual(k, 2022, months=[10, 11])
    bel = (BEL.get(k) or {}).get('gec') or 0
    isl = (ISL.get(k) or {}).get('gec') or 0
    if t22 and (k not in BEL and k not in ISL):
        unmatched['bulten'] += 1
    rec = dict(il=il, ilce=ilce, bolge=REG.get(il, ''),
               t22=t22, nd22=nd22, bel=bel, isl=isl, bas=t22 - bel - isl,
               bel_gel=(BEL.get(k) or {}).get('gel') or 0, bel_dol=(BEL.get(k) or {}).get('dol') or 0,
               isl_dol=(ISL.get(k) or {}).get('dol') or 0,
               sege=(sege.get(ALIAS.get(k, k)) or {}).get('skor'), sege_sira=(sege.get(ALIAS.get(k, k)) or {}).get('sira'),
               tga_basit=TGA[ALIAS.get(k, k)]['BASİT KONAKLAMA'], tga_basit_gecis=TGA[ALIAS.get(k, k)]['BASIT_GECIS'],
               tga_isl=TGA[ALIAS.get(k, k)]['Turizm İşletmesi Belgesi'] + TGA[ALIAS.get(k, k)]['Kısmi Turizm İşletmesi Belgesi'])
    for Y in range(2015, 2027):
        rec[f'g{Y}'] = annual(k, Y)
    rec['g2025_jj'] = annual(k, 2025, months=range(7)); rec['g2026_jj'] = annual(k, 2026, months=range(7))
    rec['cap22'] = capacity(k, 2022); rec['cap23'] = capacity(k, 2023); rec['cap25'] = capacity(k, 2025)
    rec['cap22_isl'] = (isl / (rec['isl_dol'] / 100 * 365)) if isl and rec['isl_dol'] else 0.0
    rec['yab22'] = annual(k, 2022, 'gyab'); rec['gel22'] = annual(k, 2022, 'gel')
    D.append(rec)

# kayıt eşleşme kontrolü
print('ilçe sayısı', len(D), '| 2022 aktif', sum(1 for r in D if r['t22'] > 0))
print('bülten eşleşmeyen aktif ilçe', unmatched)
neg = [r for r in D if r['bas'] < -1]
print('negatif basit kalıntısı', len(neg), [(r['il'], r['ilce'], r['bas']) for r in neg[:10]])
print('SEGE eşleşen (2022 aktif)', sum(1 for r in D if r['t22'] > 0 and r['sege'] is not None))
miss = [(r['il'], r['ilce']) for r in D if r['t22'] > 0 and r['sege'] is None]
print('SEGE eşleşmeyen örnek', miss[:25])
bel_tot = sum(BEL[k]['gec'] for k in BEL); bel_in = sum(r['bel'] for r in D)
print('belediye bülten toplamı', bel_tot, 'panele eşlenen', bel_in)
isl_tot = sum(ISL[k]['gec'] for k in ISL); isl_in = sum(r['isl'] for r in D)
print('işletme bülten toplamı', isl_tot, 'panele eşlenen', isl_in)
miss_b = [(k, BEL[k]['gec']) for k in BEL if k not in M]
miss_i = [(k, ISL[k]['gec']) for k in ISL if k not in M]
print('seride olmayan belediye ilçeleri', len(miss_b), sorted(miss_b, key=lambda x: -x[1])[:10])
print('seride olmayan işletme ilçeleri', len(miss_i), sorted(miss_i, key=lambda x: -x[1])[:10])
json.dump(D, open(os.path.join(OUT, 'ilce_panel.json'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(BAS_DEC_IL, open(os.path.join(OUT, 'basit_aralik_il.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('kaydedildi')
