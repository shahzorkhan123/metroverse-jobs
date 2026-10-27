# Tasks TODO

## Immediate (Low Effort)
1. "city" → "region" text cleanup in UI strings
2. Gzip compression setup for production (large metro files: 17-23MB)

## Short-Term
3. ~~GitHub Actions CI/CD workflow~~ (done)
4. ~~Deploy to GitHub Pages~~ (done)
5. Fix export_meta to merge with existing catalog (not overwrite)

## Medium-Term
6. ~~India state-level data~~ (done, PLFS microdata)
7. Multi-year support (2020-2024) — pipeline already supports --year flag
8. ~~RCA per region~~ (done 2026-10-25: real RCA vs national in industrySpace/chart/useRCAData.ts; fixes Good At)
9. ~~Occupation Space network graph~~ (done 2026-10-25: Occupation Space + Job Space tab, US only)
10. Growth Opportunities (PSWOT-style chart) — next: density ω from space phi (see playground §6), COG
11. Similar Regions comparison feature
12. Validate Job Space proximity against O*NET Career Changers matrix / CPS flows
13a. Article/design note: older (Hidalgo 2007 / classic Atlas / Metroverse) vs newer (Atlas 10, 2025) space model, and why we use the older one (see plan file "Later (documentation)")
13b. Occupation Space divisions from SOC 2018 hierarchy + group-aware layout + division-level setting (awaiting user go-ahead)
13. India Occupation Space (needs NCO→SOC crosswalk or richer state × NCO data)

## Long-Term
14. Additional countries (UK ONS, EU Eurostat via ISCO)
15. ~~O*NET task complexity integration~~ (done 2026-10-25: PCI replaces GDP proxy; JCI in complexity file)
16. Time-series animations (employment trends over years)
