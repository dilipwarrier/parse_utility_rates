#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_utility_rates.py

General-purpose utility rate parser for arbitrary US ZIP codes using:
- ZIP -> Utility mapping CSVs (with EIAID)
- OpenEI Utility Rate Database (URDB) CSV
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from datetime import date

def require_file(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path

def load_zip_maps(iou_csv, non_iou_csv):
    iou = pd.read_csv(iou_csv)
    non_iou = pd.read_csv(non_iou_csv)

    zipmap = pd.concat([iou, non_iou], ignore_index=True)

    if "eiaid" not in zipmap.columns:
        raise ValueError("ZIP mapping files must contain 'eiaid' column")

    zipmap["zip"] = zipmap["zip"].astype("int64")
    zipmap["eiaid"] = zipmap["eiaid"].astype("int64")

    return zipmap

def load_urdb(urdb_csv):
    df = pd.read_csv(urdb_csv, low_memory=False)

    if "eiaid" not in df.columns:
        raise ValueError("URDB file must contain 'eiaid' column")

    df["eiaid"] = df["eiaid"].astype("int64")

    return df

def filter_by_zip(zip_code, zipmap, urdb):
    zip_code = int(zip_code)

    utilities = zipmap[zipmap["zip"] == zip_code]

    if utilities.empty:
        raise ValueError(f"No utilities found for ZIP code {zip_code}")

    zip_eiaids = utilities["eiaid"].unique()
    df_zip = urdb[urdb["eiaid"].isin(zip_eiaids)]

    df_zip = df_zip.merge(
        utilities[["eiaid", "utility_name", "state", "ownership", "service_type"]],
        on="eiaid",
        how="left"
    )

    return df_zip

def filter_residential_active_today(df):
    df2 = df.copy()

    # Residential only
    df2 = df2[df2["sector"].str.contains("res", case=False, na=False)]

    # Default tariffs only
    df2 = df2[df2["is_default"] == True]

    # Parse dates safely
    df2["startdate"] = pd.to_datetime(df2["startdate"], errors="coerce")
    df2["enddate"] = pd.to_datetime(df2["enddate"], errors="coerce")

    today = pd.Timestamp(date.today())

    # Active today filter
    df2 = df2[
        ((df2["startdate"].isna()) | (df2["startdate"] <= today)) &
        ((df2["enddate"].isna()) | (df2["enddate"] >= today))
    ]

    return df2

def extract_flat_energy_rate(row):
    for col in row.index:
        if col.startswith("energyratestructure") and col.endswith("rate"):
            val = row[col]
            if pd.notna(val) and val > 0:
                return float(val)
    return None

def add_cents_per_kwh(df):
    rates = df.apply(extract_flat_energy_rate, axis=1)
    df["cents_per_kwh"] = (rates * 100).round(2)
    return df

def main():
    parser = argparse.ArgumentParser(description="Parse residential utility rates for any US ZIP code.")

    parser.add_argument("--zip", required=True, help="Target ZIP code (5-digit)")
    parser.add_argument("--urdb", default="usurdb.csv", help="Path to URDB CSV (default: usurdb.csv)")
    parser.add_argument("--iou", default="iou_zipcodes_2024.csv", help="IOU ZIP mapping CSV")
    parser.add_argument("--non-iou", dest="non_iou", default="non_iou_zipcodes_2024.csv", help="Non-IOU ZIP mapping CSV")
    parser.add_argument("--out", default=None, help="Optional output CSV filename")

    args = parser.parse_args()

    try:
        urdb_path = require_file(args.urdb)
        iou_path = require_file(args.iou)
        non_iou_path = require_file(args.non_iou)

        zipmap = load_zip_maps(iou_path, non_iou_path)
        urdb = load_urdb(urdb_path)

        df_zip = filter_by_zip(args.zip, zipmap, urdb)
        df_res = filter_residential_active_today(df_zip)
        df_res = add_cents_per_kwh(df_res)

        cols_out = [
            "utility_name",
            "ownership",
            "service_type",
            "cents_per_kwh",
            "fixedchargefirstmeter"
        ]

        cols_out = [c for c in cols_out if c in df_res.columns]

        df_out = df_res[cols_out].dropna(subset=["cents_per_kwh"])

        if args.out:
            df_out.to_csv(args.out, index=False)
            print(f"Wrote {len(df_out)} rows to {args.out}")
        else:
            # Pretty-print to terminal
            pd.set_option("display.max_rows", None)
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", 160)
            pd.set_option("display.colheader_justify", "left")

            print("\nResidential Utility Rates (cents per kWh):\n")
            print(df_out.to_string(index=False))

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
