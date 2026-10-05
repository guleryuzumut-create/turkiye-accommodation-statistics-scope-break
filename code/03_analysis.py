# -*- coding: utf-8 -*-
"""Ulusal makale analizleri. Çıktı: cikti/sonuclar.json ve ekrana özet."""
import json, os, re, glob, collections, math
import numpy as np
import openpyxl
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import pandas as pd

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = str(ROOT / "output")
E = str(RAW)
V = str(RAW / "ktb")
D = pd.DataFrame(json.load(open(os.path.join(OUT, 'ilce_panel.json'), encoding='utf-8')))
R = {}

def up(s):
    return str(s).strip().replace('i', 'İ').replace('ı', 'I').upper()

# ------------------------------------------------------------------ A. ulusal uzlaştırma
nat = {y: D[f'g{y}'].sum() for y in range(2015, 2027)}
R['national_annual'] = {str(k): int(v) for k, v in nat.items()}
R['recon_2022'] = dict(total=int(D.t22.sum()), isl=int(D.isl.sum()), bel=int(D.bel.sum()), bas=int(D.bas.sum()))
print('A. 2022:', R['recon_2022'], 'isl+bel+bas =', int(D.isl.sum() + D.bel.sum() + D.bas.sum()))

# 2023-2025 yıllık bültenler: basit belgeli hacim
def basit_from_bulletin(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    tot = None; bas = 0
    for r in wb['Tür Sınıf'].iter_rows(values_only=True):
        if r[0] and 'Basit Belgeli' in str(r[0]) and isinstance(r[7], (int, float)):
            bas += r[7]
        if r[0] == 'GENEL TOPLAM' and isinstance(r[7], (int, float)):
            tot = r[7]
    prov = {}
    for sh in ['Ankara', 'Antalya', 'Aydın', 'İstanbul', 'İzmir', 'Muğla']:
        b = 0; t = None
        for r in wb[sh].iter_rows(values_only=True):
            if r[0] and 'Basit Belgeli' in str(r[0]) and isinstance(r[7], (int, float)):
                b += r[7]
            if r[0] == 'GENEL TOPLAM' and isinstance(r[7], (int, float)):
                t = r[7]
        prov[up(sh)] = dict(basit=b, total=t)
    return dict(total=tot, basit=bas, prov=prov)

B = {y: basit_from_bulletin(os.path.join(E, f'b{y}.xlsx')) for y in (2023, 2024, 2025)}
R['bulletins'] = B
for y in B:
    print(f'   {y} bülten toplamı {B[y]["total"]:,} | seri {nat[y]:,} | basit {B[y]["basit"]:,} ({B[y]["basit"]/B[y]["total"]*100:.1f}%)')

# ------------------------------------------------------------------ B. istatistikten silinen ilçeler
act = D[D.t22 > 0].copy()
act['gone_2023'] = act.g2023 == 0
act['gone_all'] = (act.g2023 == 0) & (act.g2024 == 0) & (act.g2025 == 0)
act['back_2025'] = (act.g2023 == 0) & (act.g2025 > 0)
R['districts'] = dict(active2022=int(len(act)), active={str(y): int((D[f'g{y}'] > 0).sum()) for y in range(2015, 2027)},
                      gone2023=int(act.gone_2023.sum()), gone_all=int(act.gone_all.sum()),
                      gone_all_nights22=int(act[act.gone_all].t22.sum()),
                      gone2023_nights22=int(act[act.gone_2023].t22.sum()),
                      back2025=int(act.back_2025.sum()))
print('B.', R['districts'])
# bütünüyle belediye belgeli ilçeler
act['mun_only'] = (act.isl == 0) & (act.bas == 0) & (act.bel > 0)
R['districts']['mun_only'] = int(act.mun_only.sum())
R['districts']['mun_only_gone'] = int((act.mun_only & act.gone_2023).sum())
# SEGE karşılaştırma
g = act[act.gone_all & act.sege.notna()].sege; s = act[~act.gone_all & act.sege.notna()].sege
mw = stats.mannwhitneyu(g, s)
R['districts']['sege_gone_median'] = float(g.median()); R['districts']['sege_stay_median'] = float(s.median())
R['districts']['sege_mw_p'] = float(mw.pvalue)
print('   SEGE ortanca: silinen', round(g.median(), 3), 'kalan', round(s.median(), 3), 'MW p', mw.pvalue)
reg_g = act[act.gone_all].groupby('bolge').size(); reg_a = act.groupby('bolge').size()
R['districts']['gone_by_region'] = {k: [int(reg_g.get(k, 0)), int(v)] for k, v in reg_a.items()}

# ------------------------------------------------------------------ C. geçiş tahmini (ilçe)
pool = act.bel + act.bas
act['pool'] = pool
act['ndshare'] = act.nd22 / act.t22
# il düzeyi Kasım-Aralık payı (küçük ilçelerde istikrar için)
prov_nd = act.groupby('il').apply(lambda x: x.nd22.sum() / x.t22.sum())
act['ndshare_il'] = act.il.map(prov_nd)
act['conv_seas'] = np.where(act.bas > 0, act.bas / act.ndshare_il, 0.0)
act['conv_seas'] = np.minimum(act.conv_seas, act.pool)
act['conv_flat'] = np.minimum(act.bas * 6, act.pool)
act['cr'] = np.where(act.pool > 0, act.conv_seas / act.pool, np.nan)
act['exit_share'] = 1 - act.cr
# ------------------------------------------------------------------ C1. doğrulama: TGA tesis sayıları
m = act[act.pool > 0]
has_bas = m.bas > 0; has_tga = m.tga_basit_gecis > 0
ct = pd.crosstab(has_bas, has_tga)
R['val_tga_crosstab'] = {f'{a}|{b}': int(ct.loc[a, b]) for a in ct.index for b in ct.columns}
rho = stats.spearmanr(m.bas, m.tga_basit_gecis)
pos = m[(m.bas > 0) & (m.tga_basit_gecis > 0)]
r_log = stats.pearsonr(np.log(pos.bas), np.log(pos.tga_basit_gecis))
R['val_tga'] = dict(spearman=float(rho.statistic), p=float(rho.pvalue), n=int(len(m)),
                    log_r=float(r_log.statistic), log_n=int(len(pos)))
print('C1. ilçe basit Kas-Ara hacmi ~ TGA basit (2021-22) tesis sayısı: Spearman', round(rho.statistic, 3), 'n', len(m), '| log r', round(r_log.statistic, 3), 'n', len(pos))
print('    çapraz tablo (basit hacim>0 x TGA basit>0):', R['val_tga_crosstab'])
# ------------------------------------------------------------------ C2. doğrulama: kapasite fazlası
act['cap_excess'] = act.cap23 - act.cap22_isl
cc = act[(act.cap22_isl > 0) & (act.g2023 > 0)]
r_cap = stats.spearmanr(cc.cap_excess, cc.bas)
r_cap2 = stats.spearmanr(cc.cap_excess, cc.tga_basit_gecis)
nobas = cc[cc.bas == 0].cap_excess; wbas = cc[cc.bas > 0].cap_excess
R['val_cap'] = dict(n=int(len(cc)), rho_bas=float(r_cap.statistic), rho_tga=float(r_cap2.statistic),
                    med_excess_nobas=float(nobas.median()), med_excess_bas=float(wbas.median()),
                    n_nobas=int(len(nobas)), n_bas=int(len(wbas)))
print('C2. kapasite fazlası (2023 seri - 2022 işletme) ~ basit hacim: rho', round(r_cap.statistic, 3), '| ~ TGA:', round(r_cap2.statistic, 3), '| ortanca fazla: basitsiz', round(nobas.median(), 1), 'basitli', round(wbas.median(), 1))
# ------------------------------------------------------------------ C3. doğrulama: 6 il 2023 basit hacmi
prov = act.groupby('il').agg(t22=('t22', 'sum'), bel=('bel', 'sum'), isl=('isl', 'sum'), bas=('bas', 'sum'),
                             conv_seas=('conv_seas', 'sum'), conv_flat=('conv_flat', 'sum'), nd22=('nd22', 'sum'),
                             g2023=('g2023', 'sum'), g2024=('g2024', 'sum'), g2025=('g2025', 'sum'),
                             g2025_jj=('g2025_jj', 'sum'), g2026_jj=('g2026_jj', 'sum'))
v6 = []
for p, d in B[2023]['prov'].items():
    v6.append(dict(il=p, est_conv=float(prov.loc[p, 'conv_seas']), flat=float(prov.loc[p, 'conv_flat']), basit2023=d['basit'],
                   basit2024=B[2024]['prov'][p]['basit'], basit2025=B[2025]['prov'][p]['basit']))
R['val_6prov'] = v6
for x in v6:
    print(f"C3. {x['il']:<10} tahmini geçiş {x['est_conv']:>12,.0f} | düz {x['flat']:>12,.0f} | 2023 basit {x['basit2023']:>12,} | oran {x['basit2023']/x['est_conv']:.2f}")
R['nat_conv'] = dict(seas=float(act.conv_seas.sum()), flat=float(act.conv_flat.sum()), basit2023=B[2023]['basit'])
print('    ulusal: mevsimsel', round(act.conv_seas.sum()), 'düz', round(act.conv_flat.sum()), '2023 basit', B[2023]['basit'])

# ------------------------------------------------------------------ D. il düzeyi düzeltme
prov['pool'] = prov.bel + prov.bas
prov['share_bel'] = prov.bel / prov.t22 * 100
prov['cr'] = prov.conv_seas / prov.pool * 100
prov['cr_flat'] = prov.conv_flat / prov.pool * 100
prov['pub'] = (prov.g2023 / prov.t22 - 1) * 100
prov['sub'] = (prov.g2023 / (prov.t22 - prov.bel) - 1) * 100
prov['adj_seas'] = (prov.g2023 / (prov.isl + prov.conv_seas) - 1) * 100
prov['adj_flat'] = (prov.g2023 / (prov.isl + prov.conv_flat) - 1) * 100
prov['g23_25'] = (prov.g2025 / prov.g2023 - 1) * 100
prov['pub22_25'] = (prov.g2025 / prov.t22 - 1) * 100
prov['adj22_25'] = (prov.g2025 / (prov.isl + prov.conv_flat) - 1) * 100
prov['jj'] = (prov.g2026_jj / prov.g2025_jj - 1) * 100
def corr(x, y):
    r = stats.pearsonr(prov[x], prov[y]); ci = r.confidence_interval()
    s = stats.spearmanr(prov[x], prov[y])
    return dict(r=float(r.statistic), p=float(r.pvalue), lo=float(ci.low), hi=float(ci.high), rho=float(s.statistic), rho_p=float(s.pvalue))
R['prov_corr'] = {k: corr('share_bel', k) for k in ['pub', 'sub', 'adj_seas', 'adj_flat']}
R['prov_corr']['cr_pub'] = corr('cr', 'pub')
for k, v in R['prov_corr'].items():
    print(f'D. {k:<9} r={v["r"]:.2f} [{v["lo"]:.2f},{v["hi"]:.2f}] p={v["p"]:.3g} rho={v["rho"]:.2f}')
R['prov_summary'] = {k: dict(median=float(prov[k].median()), q1=float(prov[k].quantile(.25)), q3=float(prov[k].quantile(.75)))
                     for k in ['share_bel', 'cr', 'cr_flat', 'pub', 'sub', 'adj_seas', 'adj_flat', 'g23_25', 'pub22_25', 'adj22_25', 'jj']}
R['prov_ncap'] = int((prov.cr >= 99.999).sum())
# bölgeler
REG = act.groupby('il').bolge.first(); prov['bolge'] = REG
regt = prov.groupby('bolge').agg(n=('cr', 'size'), cr_med=('cr', 'median'), cr_flat_med=('cr_flat', 'median'),
                                 share_bel=('share_bel', 'median'), pub=('pub', 'median'), adj=('adj_flat', 'median'))
pool_reg = prov.groupby('bolge').apply(lambda x: x.conv_flat.sum() / x.pool.sum() * 100)
regt['cr_flat_pooled'] = pool_reg
R['regions'] = regt.round(2).reset_index().to_dict('records')
print(regt.round(1))
kw = stats.kruskal(*[g.cr_flat.values for _, g in prov.groupby('bolge')])
R['regions_kw'] = dict(H=float(kw.statistic), p=float(kw.pvalue))
print('   Kruskal-Wallis (düz geçiş oranı, bölge):', round(kw.statistic, 2), kw.pvalue)
# sıralama değişimi
rk_pub = prov.pub.rank(ascending=False); rk_adj = prov.adj_flat.rank(ascending=False)
R['rank'] = dict(spearman_pub_adj=float(stats.spearmanr(prov.pub, prov.adj_flat).statistic),
                 mean_abs_shift=float((rk_pub - rk_adj).abs().mean()), max_shift=int((rk_pub - rk_adj).abs().max()),
                 n_shift10=int(((rk_pub - rk_adj).abs() >= 10).sum()),
                 sign_flip=int(((prov.pub < 0) & (prov.adj_flat > 0)).sum()),
                 pub_neg=int((prov.pub < 0).sum()), adj_neg=int((prov.adj_flat < 0).sum()))
print('   sıralama:', R['rank'])

# ------------------------------------------------------------------ E. belirleyiciler (ilçe)
md = act[(act.pool >= 1000) & act.sege.notna() & (act.bel_gel > 0)].copy()
md['exit_flat'] = 1 - np.minimum(md.bas * 6, md.pool) / md.pool
md['exit_seas'] = md.exit_share
md['stay_bel'] = md.bel / md.bel_gel
md['ln_stay'] = np.log(md.stay_bel)
md['ln_pool'] = np.log(md.pool)
md['share_mun'] = md.pool / md.t22
md['occ_bel'] = md.bel_dol / 100
md['foreign'] = md.yab22 / md.t22
md['full_exit'] = (md.bas == 0).astype(int)
md['reg'] = md.bolge.str.replace(' BÖLGESİ', '')
R['model_n'] = int(len(md))
desc = md[['exit_flat', 'exit_seas', 'sege', 'stay_bel', 'occ_bel', 'pool', 'share_mun', 'foreign', 'full_exit']].describe().T
R['model_desc'] = desc.round(4).reset_index().to_dict('records')
print(desc.round(3))
f1 = 'exit_flat ~ sege + ln_stay + occ_bel + ln_pool + share_mun + foreign'
f2 = f1 + ' + C(reg)'
res = {}
for name, f in [('ols1', f1), ('ols2', f2)]:
    mres = smf.ols(f, data=md).fit(cov_type='cluster', cov_kwds={'groups': md['il']})
    res[name] = mres
    print('\n', name, 'n', int(mres.nobs), 'R2', round(mres.rsquared, 3))
    print(mres.summary2().tables[1].round(4))
lg = smf.glm('full_exit ~ sege + ln_stay + occ_bel + ln_pool + share_mun + foreign + C(reg)', data=md,
             family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': md['il']})
res['logit'] = lg
print('\n logit full exit n', int(lg.nobs)); print(lg.summary2().tables[1].round(4))
fl = smf.glm('exit_flat ~ sege + ln_stay + occ_bel + ln_pool + share_mun + foreign + C(reg)', data=md,
             family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': md['il']})
res['fraclogit'] = fl
print('\n fractional logit n', int(fl.nobs)); print(fl.summary2().tables[1].round(4))
R['models'] = {}
for k, mres in res.items():
    t = mres.summary2().tables[1]
    R['models'][k] = dict(n=int(mres.nobs), r2=float(getattr(mres, 'rsquared', float('nan'))),
                          coef={i: dict(b=float(t.loc[i].iloc[0]), se=float(t.loc[i].iloc[1]), p=float(t.loc[i].iloc[3])) for i in t.index})
# standartlaştırılmış etkiler (ols2)
sd = md[['sege', 'ln_stay', 'occ_bel', 'ln_pool', 'share_mun', 'foreign']].std()
R['std_effects_ols2'] = {k: float(res['ols2'].params[k] * sd[k]) for k in sd.index}
print('std etkiler (1 SS artışın çıkış payına etkisi):', {k: round(v, 3) for k, v in R['std_effects_ols2'].items()})
# ------------------------------------------------------------------ E2. sağlamlık: mevsimsellik kontrolü ve alternatif bağımlı değişken
md['ln_nd'] = np.log(md.ndshare.clip(lower=0.005))
rob = {}
for name, f in [('flat_season', 'exit_flat ~ sege + ln_stay + occ_bel + ln_pool + share_mun + foreign + ln_nd + C(reg)'),
                ('seas_season', 'exit_seas ~ sege + ln_stay + occ_bel + ln_pool + share_mun + foreign + ln_nd + C(reg)')]:
    mres = smf.ols(f, data=md).fit(cov_type='cluster', cov_kwds={'groups': md['il']})
    t = mres.summary2().tables[1]
    rob[name] = dict(n=int(mres.nobs), r2=float(mres.rsquared), coef={i: dict(b=float(t.loc[i].iloc[0]), se=float(t.loc[i].iloc[1]), p=float(t.loc[i].iloc[3])) for i in t.index})
    print(name, 'R2', round(mres.rsquared, 3)); print(t.loc[[i for i in t.index if not i.startswith('C(')]].round(4))
R['models_robust'] = rob
# ------------------------------------------------------------------ E3. ilçenin tamamen silinmesi (2022 aktif ilçeler)
gd = act[act.sege.notna()].copy()
gd['gone'] = gd.gone_all.astype(int)
gd['share_mun'] = (gd.bel + gd.bas) / gd.t22
gd['ln_t22'] = np.log(gd.t22)
gd['reg'] = gd.bolge.str.replace(' BÖLGESİ', '')
gl = smf.glm('gone ~ sege + share_mun + ln_t22 + C(reg)', data=gd, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': gd['il']})
t = gl.summary2().tables[1]
print('E3 silinme logit n', int(gl.nobs)); print(t.loc[[i for i in t.index if not i.startswith('C(')]].round(4))
R['model_gone'] = dict(n=int(gl.nobs), events=int(gd.gone.sum()), coef={i: dict(b=float(t.loc[i].iloc[0]), se=float(t.loc[i].iloc[1]), p=float(t.loc[i].iloc[3])) for i in t.index})
# ortalama marjinal etki: SEGE
me = gl.get_margeff(at='overall').summary_frame()
R['model_gone']['ame_sege'] = float(me.loc['sege'].iloc[0]); R['model_gone']['ame_share'] = float(me.loc['share_mun'].iloc[0])
print('   AME sege', round(me.loc['sege'].iloc[0], 4), 'AME share', round(me.loc['share_mun'].iloc[0], 4))
# SEGE dörtte birlik dilimlerine göre silinme oranı
gd['sq'] = pd.qcut(gd.sege, 4, labels=['Q1 (en az gelişmiş)', 'Q2', 'Q3', 'Q4 (en gelişmiş)'])
R['gone_by_sege_q'] = gd.groupby('sq', observed=True).agg(n=('gone', 'size'), gone=('gone', 'sum'), rate=('gone', 'mean')).reset_index().astype({'sq': str}).to_dict('records')
print(R['gone_by_sege_q'])
# tamamen belediye belgeli olup silinen ilçelerin payı
md.to_json(os.path.join(OUT, 'model_verisi.json'), orient='records', force_ascii=False)
prov.reset_index().to_json(os.path.join(OUT, 'il_tablosu.json'), orient='records', force_ascii=False)
act.to_json(os.path.join(OUT, 'ilce_analiz.json'), orient='records', force_ascii=False)

# ------------------------------------------------------------------ F. Bitlis
b = prov.loc['BİTLİS']
R['bitlis'] = {k: float(b[k]) for k in ['t22', 'bel', 'isl', 'bas', 'g2023', 'g2025', 'share_bel', 'cr', 'cr_flat', 'pub', 'adj_seas', 'adj_flat', 'g23_25']}
R['bitlis']['cr_rank_low'] = int((prov.cr_flat < b.cr_flat).sum() + 1)
print('F. Bitlis', {k: round(v, 1) for k, v in R['bitlis'].items()})
json.dump(R, open(os.path.join(OUT, 'sonuclar.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print('kaydedildi')

# ------------------------------------------------------------------ G. ilçe düzeyi kapsam sınaması (il düzeyindeki sınamanın genişletilmesi)
dd = act[(act.t22 >= 1000)].copy()
dd['share_mun'] = (dd.bel + dd.bas) / dd.t22 * 100
dd['pub'] = (dd.g2023 / dd.t22 - 1) * 100
dd['sub'] = np.where(dd.t22 - dd.bel > 0, (dd.g2023 / (dd.t22 - dd.bel).clip(lower=1) - 1) * 100, np.nan)
dd['adj_flat'] = np.where(dd.isl + dd.conv_flat > 0, (dd.g2023 / (dd.isl + dd.conv_flat).clip(lower=1) - 1) * 100, np.nan)
dd['adj_seas'] = np.where(dd.isl + dd.conv_seas > 0, (dd.g2023 / (dd.isl + dd.conv_seas).clip(lower=1) - 1) * 100, np.nan)
G = {}
for k in ['pub', 'sub', 'adj_flat', 'adj_seas']:
    x = dd[['share_mun', k]].replace([np.inf, -np.inf], np.nan).dropna()
    x = x[x[k] < 1000]  # aşırı uçlar (tabanı çok küçük ilçeler)
    s = stats.spearmanr(x.share_mun, x[k])
    G[k] = dict(n=int(len(x)), rho=float(s.statistic), p=float(s.pvalue), median=float(x[k].median()))
    print(f'G. ilçe {k:<9} n={len(x)} rho={s.statistic:.3f} p={s.pvalue:.3g} medyan={x[k].median():.1f}')
R['district_scope_test'] = G
# ulusal düzeltilmiş değişim
isl23 = B[2023]['total'] - B[2023]['basit']
R['national_change'] = dict(pub=(B[2023]['total'] / R['recon_2022']['total'] - 1) * 100,
                            sub=(B[2023]['total'] / (R['recon_2022']['total'] - R['recon_2022']['bel']) - 1) * 100,
                            isl_only=(isl23 / R['recon_2022']['isl'] - 1) * 100,
                            adj_seas=(B[2023]['total'] / (R['recon_2022']['isl'] + act.conv_seas.sum()) - 1) * 100,
                            adj_flat=(B[2023]['total'] / (R['recon_2022']['isl'] + act.conv_flat.sum()) - 1) * 100,
                            isl23=isl23, lost_seas=float(act.pool.sum() - act.conv_seas.sum()), lost_flat=float(act.pool.sum() - act.conv_flat.sum()),
                            pool=float(act.pool.sum()))
print('ulusal değişim', {k: round(v, 2) for k, v in R['national_change'].items()})
json.dump(R, open(os.path.join(OUT, 'sonuclar.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
