# Utility Rate Analyzer

Tools for parsing and analyzing residential electricity rates using URDB
and ZIP-code utility mappings.

## Features
- Filters active residential tariffs
- Removes low-income, EV, TOU, and multi-unit rates
- Computes effective cents per kWh for a 1 kW average household load
- Designed for Massachusetts utilities

## External Data Files Required (Not Tracked in Git)

This repository intentionally does NOT store large external datasets.
You must download the following files manually before running the code.

---

### 1. ZIP Code to Utility Mapping Files

Required files:
- iou_zipcodes_2024.csv
- non_iou_zipcodes_2024.csv

These files map ZIP codes to electric utilities.

Download them from your source (EIA, OpenEI, state datasets, or your
pre-existing archive) and place both files in the project root directory.

The analysis code expects both files to be present locally.

---

### 2. Utility Rates Database (URDB CSV)

Required file:
- usurdb.csv

This is the full OpenEI Utility Rate Database export (typically over 150 MB).

You can download it from OpenEI using the Utility Rates API:

https://apps.openei.org/services/doc/rest/util_rates/

Or via the direct "Download Full Approved US Rates" option on OpenEI.

Once downloaded:
1. If the file is compressed (for example, .csv.gz), extract it.
2. Rename the extracted file to:
   usurdb.csv
3. Place it in the project root directory.

This file is intentionally excluded from Git because it exceeds GitHub's
file size limits.

---

### Important Notes

- These CSV files are REQUIRED for the parsing and analysis scripts to run.
- They are listed in .gitignore and will not be committed to Git.
- Each user must download these datasets independently.

