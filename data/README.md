# Data provenance

Raw files are committed in `data/raw/` (about 78 MB, all under open licences that allow redistribution with attribution) so a fresh clone runs offline; data.gov.in rejects scripted downloads, so re-fetching is not reliable. Integrity check: `shasum -a 256 -c data/raw_manifest.sha256` (run from `data/`). All raw files were downloaded on 18 Sep 2026.

## Pilot district: Nashik, Maharashtra
Why Nashik was picked:
- It has the largest rural PHC network in Maharashtra in the facility directory: 147 PHCs, 574 sub-centres, 31 CHCs and 15 sub-districts.
- It includes tribal blocks (Surgana, Peth, Trimbakeshwar) with poor access, which is where lateral transfers matter most.
- Monsoon seasonality drives malaria and diarrhoea demand, which is the demand signal the forecaster needs.
- All 760 facilities have valid coordinates.

Federation clients are 4 states from different regions with different amounts of data: Maharashtra, Haryana, Assam and Meghalaya (Meghalaya is the data-poor state).

## Datasets
| # | Dataset | File(s) | Source | License | Used for |
|---|---|---|---|---|---|
| 1 | HMIS item-wise monthly district reports, Apr 2013 – Mar 2020, for MH, HR, AS, ML (336 files; the "for-<Month>" files are single months, not year-to-date totals) | `raw/hmis/hmis-item-<FY>-mn-<st>-for-<Mon>.csv`; URLs in `raw/hmis/source_urls.txt` | data.gov.in, MoHFW | NDSAP / Government Open Data License – India | Service-delivery demand drivers (OPD, inpatient, deliveries, childhood diseases, malaria from NVBDCP); **real drug stock flows (M19 section, FY2017-18 onward)** |
| 2 | All India Health Centres Directory (as on 7 Oct 2016) | `raw/facilities/geocode_health_centre.csv` | data.gov.in, MoHFW | NDSAP / GODL-India | Facility list, type and coordinates for the network graph and solver |
| 3 | National List of Essential Medicines 2022 | `raw/nlem/nlem2022.pdf` | CDSCO / MoHFW | Government publication. Only drug names, dosage forms and levels of care are extracted (facts). | Drug master list for normalising drug names |
| 4 | NASA POWER daily weather (rainfall, temperature, max temperature, relative humidity), Apr 2013 – Mar 2020, for Nashik (20.00N 73.79E, pilot) and Dhule (21.01N 74.45E, held-out district) | `raw/weather/{nashik,dhule}_power_daily_2013_2020.json` | NASA LaRC POWER API | Open. NASA data carries no use restrictions; attribution requested. | Weather features for both districts scored in the real benchmark. Replaces IMD, whose gridded data requires registration. |

### Key finding: real drug stock data (HMIS section M19, FY2017-18 onward)
For each district and month, HMIS reports five figures for about 15 items: 1. Balance From Previous Month, 2. Stocks Received, 3. Unusable Stock, 4. Stock Distributed, 5. Total Stock. The items include ORS, Zinc 20 mg, Albendazole 400 mg, IFA (adult, paediatric syrup, adolescent and junior), Vitamin A syrup, paediatric antibiotics and Tab. Fluconazole.

This gives a **real** consumption series ("Stock Distributed") and a real stock position at district × drug × month granularity, covering 36 months × about 95 districts across the 4 states. It is the basis of the headline real-data forecasting benchmark. Parsing note: files are latin-1 encoded, and S.No. values carry stray quote characters.

### Deviations from doc v2 (document these in the deck)
- **IDSP/IHIP weekly bulletins are replaced by HMIS disease indicators**: M10 childhood diseases and M11 NVBDCP malaria. These are real, machine-readable and share the same district keys. IDSP bulletins are PDFs and not reliably parseable.
- **IMD is replaced by NASA POWER.** IMD gridded data requires registration and its licensing is unclear; NASA POWER is open.
- The real data is **monthly and district-level**. Facility × week granularity exists only in the sealed synthetic ledger, which is anchored to these real district totals.
- Data ends March 2020. **March 2020 is excluded from test windows** because of COVID-19 disruption.

## Synthetic and team-created data
- `data/synthetic/`: sealed ledger generator output (stock, beds, attendance per facility per week). **Not committed to git** (it is a ~42 MB deterministic byproduct of `eval/seal_generator.py`, regenerable from the seed and the real HMIS anchors already in `data/raw/`). Its integrity is verified by `eval/protocol.lock`'s `generator_seal.content_hash`, which IS committed: `python -m eval.seal_generator` regenerates the files and `eval.seal_generator.compute_content_hash()` must match the locked hash, or the run refuses to proceed silently.
- `data/labelled_registers/`: at least 200 register images plus two-annotator labels. Committed (small, original team work needed for grading transparency).
