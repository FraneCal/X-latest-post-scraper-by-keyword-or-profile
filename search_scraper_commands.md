# Search Scraper Commands

This document contains standardized and validated command examples for running `run_search_scraper.py`.
Queries are normalized for boolean correctness and API safety.

---

## PokerStars

### Keyword Search

Overview of the options
```bash
python run_search_scraper.py \
  --keyword '(PokerStars) OR (pokerstars) OR (Poker stars) OR (@PokerStars)' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_pokerstars_keyword.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --keyword '(PokerStars) OR (pokerstars) OR (Poker stars) OR (@PokerStars)' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_pokerstars_keyword.xlsx
```

### Profile Search

Overview of the options
```bash
python run_search_scraper.py \
  --from-account 'pokerstars' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_pokerstars_profile.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --from-account 'pokerstars' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_pokerstars_profile.xlsx
```

---

## Poker.org

### Keyword Search

Overview of the options
```bash
python run_search_scraper.py \
  --keyword '(poker.org) OR (pokerorg) OR (Poker Org) OR (PokerOrg) OR (Poker.Org) OR (@pokerorg)' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_pokerorg_keyword.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --keyword '(poker.org) OR (pokerorg) OR (Poker Org) OR (PokerOrg) OR (Poker.Org) OR (@pokerorg)' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_pokerorg_keyword.xlsx
```

### Profile Search

Overview of the options
```bash
python run_search_scraper.py \
  --from-account 'pokerorg' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_pokerorg_profile.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --from-account 'pokerorg' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_pokerorg_profile.xlsx
```

---

## World Series of Poker

### Keyword Search

Overview of the options
```bash
python run_search_scraper.py \
  --keyword '(WSOP) OR (World Series of Poker) OR (World Series AND poker) OR (@WSOP) OR (WSOP Circuit) OR (World Series of Poker Circuit) OR (World Series of Poker AND Circuit) OR (WSOP AND Circuit)' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_wsop_keyword.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --keyword '(WSOP) OR (World Series of Poker) OR (World Series AND poker) OR (@WSOP) OR (WSOP Circuit) OR (World Series of Poker Circuit) OR (World Series of Poker AND Circuit) OR (WSOP AND Circuit)' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_wsop_keyword.xlsx
```

### Profile Search

Overview of the options
```bash
python run_search_scraper.py \
  --from-account 'WSOP' \
  --limit 500 \
  --latest \
  --since-date 2025-12-17 \
  --until-date 2025-12-18 \
  --output 251218_wsop_profile.xlsx
```
Run this in your terminal
```bash
python run_search_scraper.py --from-account 'WSOP' --limit 500 --latest --since-date 2025-12-17 --until-date 2025-12-18 --output 251218_wsop_profile.xlsx
```

---

## Notes

- All boolean operators are explicit.
- All multi-word phrases are quoted.
- Queries are compatible with strict search backends and APIs.
- Output filenames are normalized per entity.
