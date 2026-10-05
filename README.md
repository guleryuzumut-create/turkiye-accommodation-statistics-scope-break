# Replication data and code for: Who Disappears from Official Tourism Statistics? A Licensing Reform, Scope Breaks and the Geography of Missing Accommodation Data in Türkiye

Replication package for the article *Who Disappears from Official Tourism Statistics? A Licensing Reform, Scope Breaks and the Geography of Missing Accommodation Data in Türkiye* (Umut Güleryüz, Bitlis Eren University). The package contains the derived district- and province-level datasets, the code that produces every table and figure, and instructions for obtaining the original source files.

## Contents

```
code/                 Python scripts (run in numerical order)
data/derived/         Derived datasets used in the article (CSV, JSON)
data/raw/             Place the original source files here (see below); il_bolge.csv is included
figures/              Figures 1–3 of the article
requirements.txt      Python packages
```

## Derived data

* `data/derived/district_panel.csv`: 852 districts × annual overnight stays 2015–2026, 2022 licensing components, implied bed capacity, TGA certificate counts, SEGE-2022 scores, disappearance indicators and conversion estimates.
* `data/derived/province_table.csv`: 81 provinces with published, subtraction-based and conversion-adjusted changes.
* `data/derived/results.json`: All statistics reported in the article (correlations, model coefficients, validation results).

### Variable dictionary (district_panel.csv)

| Variable | Description |
|---|---|
| `province` | Province (il), upper case as in the official series |
| `district` | District (ilçe) as named in the official series |
| `region` | Geographical region (bölge) |
| `stays_2022_published` | Overnight stays 2022, published series (all licensing groups) |
| `stays_2022_novdec` | Overnight stays Nov–Dec 2022, published series |
| `stays_2022_municipal` | Overnight stays 2022, municipality-licensed bulletin |
| `stays_2022_ministry` | Overnight stays 2022, Ministry-licensed bulletin |
| `stays_2022_simple_novdec` | Simple-certificate overnight stays Nov–Dec 2022 (published total minus the two bulletins) |
| `arrivals_2022_municipal` | Arrivals 2022, municipality-licensed bulletin |
| `occupancy_2022_municipal_pct` | Bed occupancy (%) 2022, municipality-licensed bulletin |
| `occupancy_2022_ministry_pct` | Bed occupancy (%) 2022, Ministry-licensed bulletin |
| `sege2022_score` | SEGE-2022 district socio-economic development score |
| `sege2022_rank` | SEGE-2022 national rank (1 = most developed) |
| `tga_simple_certificates` | Simple certificates in the TGA register (accessed 5 Oct 2026) |
| `tga_simple_certificates_2021_2022` | Simple certificates numbered 2021 or 2022 |
| `tga_ministry_certificates` | Tourism operation (incl. partial) certificates in the TGA register |
| `stays_YYYY` | Annual overnight stays, published series (2026 = January–July) |
| `stays_2025_jan_jul` | Overnight stays January–July 2025 |
| `stays_2026_jan_jul` | Overnight stays January–July 2026 |
| `beds_series_2022` | Average beds implied by the 2022 series (stays / occupancy) |
| `beds_series_2023` | Average beds implied by the 2023 series |
| `beds_series_2025` | Average beds implied by the 2025 series |
| `beds_ministry_2022` | Beds implied by the 2022 Ministry-licensed bulletin |
| `stays_2022_foreign` | Overnight stays by foreign residents 2022 |
| `arrivals_2022_published` | Arrivals 2022, published series |
| `disappeared_2023` | Stays in 2022, none in 2023 |
| `disappeared_2023_2025` | Stays in 2022, none in 2023, 2024 and 2025 |
| `reappeared_by_2025` | Disappeared in 2023, stays recorded in 2025 |
| `municipal_only_2022` | All 2022 stays from municipality-licensed establishments |
| `municipal_pool_2022` | Municipal plus Nov–Dec simple-certificate stays 2022 |
| `novdec_share_district` | Share of Nov–Dec in district 2022 stays |
| `novdec_share_province` | Share of Nov–Dec in province 2022 stays |
| `converted_volume_seasonal` | Estimated full-year 2022 volume of converted establishments, seasonal assumption (eq. 2) |
| `converted_volume_flat` | Same, flat assumption (Nov–Dec × 6) |
| `conversion_rate_seasonal` | Converted volume / municipal pool (eq. 4) |
| `exit_share_seasonal` | 1 − conversion rate |
| `excess_beds_2023` | beds_series_2023 − beds_ministry_2022 |

## Original sources (not redistributed)

The Ministry of Culture and Tourism publications carry the notice that all rights belong to the Ministry under Law No. 5846 and that they may not be reproduced or distributed without permission. They are therefore **not** included. Download them and place them as follows:

| File (place in `data/raw/ktb/` unless noted) | Source |
|---|---|
| `2015-2026 ... İL İLÇE BAZINDA KONAKLAMA İSTATİSTİKLERİ.xlsx` (file name must start with `2015-2026`) | Ministry of Culture and Tourism, province and district accommodation statistics, https://yigm.ktb.gov.tr |
| `2022 YILI BELEDİYE BELGELİ KONAKLAMA İSTATİSTİKLERİ BÜLTENİ.xlsx` | Ministry, 2022 municipality-licensed bulletin |
| `2022 YILI İŞLETME BELGELİ KONAKLAMA İSTATİSTİKLER BÜLTENİİ.xlsx` | Ministry, 2022 Ministry-licensed bulletin (archive "2022 Yılı İşletme ve Basit Belgeli Konaklama İstatistikleri Bülteni") |
| `ARALIK 2022 BASİT BELGELİ KONAKLAMA İSTATİSTİKLERİ BÜLTENİ.xlsx` | Same archive |
| `data/raw/b2023.xlsx`, `b2024.xlsx`, `b2025.xlsx` | Ministry annual bulletins 2023–2025, https://yigm.ktb.gov.tr/TR-201126/yillik-bultenler.html |
| `data/raw/tga_tesis_listesi_2026-10-05.json` | Run `code/00_fetch_tga_register.py` (TGA public register; the register changes over time, the article uses the version accessed 5 October 2026) |
| `data/raw/sege2022_ilce_kademe.pdf` → `sege2022_ilce.json` | SEGE-2022 district ranking (Kalkınma Ajansları Genel Müdürlüğü, 2022); run `code/00_parse_sege.py` |
| `data/raw/tur_adm1.geojson`, `tur_adm2.geojson` | Run `code/00_fetch_boundaries.py` (geoBoundaries gbOpen, ODbL) |

## Reproduction

```
pip install -r requirements.txt
python code/00_fetch_tga_register.py
python code/00_parse_sege.py
python code/00_fetch_boundaries.py
python code/01_build_panel.py
python code/02_match_boundaries.py
python code/03_analysis.py
python code/04_figures.py
```

Outputs are written to `output/`. Running the scripts with a later version of the TGA register will change the certificate counts slightly.

## Licence

Code: MIT License (`LICENSE`). Derived data and figures: Creative Commons Attribution 4.0 International (`LICENSE-DATA.md`). Map boundaries derive from geoBoundaries/OpenStreetMap (ODbL).

## Citation

See `CITATION.cff`. Please cite both this dataset and the article.

## Generative AI disclosure

The code in this package was written with the assistance of Claude (Claude Opus 5.5; Anthropic, 2026) and was reviewed by the author.

Prepared 2026-10-05.
