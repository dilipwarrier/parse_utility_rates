import pandas as pd
import numpy as np
import re

# ============================================================
# 1. Load datasets
# ============================================================

# Full URDB CSV (replace path if needed)
df = pd.read_csv(r"usurdb.csv", low_memory=False)

# Combined IOU + non-IOU ZIP-Utility mappings
zip_iou = pd.read_csv(r"iou_zipcodes_2024.csv")
zip_non_iou = pd.read_csv(r"non_iou_zipcodes_2024.csv")

# Combine ZIP maps
zipmap = pd.concat([zip_iou, zip_non_iou], ignore_index=True)

# ============================================================
# 2. Get utilities for a ZIP
# ============================================================

target_zip = "01749"
target_zip_int = int(target_zip)   # ZIPs stored without leading zeros

zip_utilities = zipmap[zipmap['zip'] == target_zip_int]
utilities = zip_utilities['utility_name'].unique().tolist()

# Print for debugging
print("\nUtilities in ZIP", target_zip, ":")
print(utilities)

# ============================================================
# 3. Map ZIP-map utility names to URDB utility names
# ============================================================

utility_map = {
    "Massachusetts Electric Co": "Massachusetts Electric Co",
    "NSTAR Electric Company": "NSTAR Electric Company",
    "Town of Hudson - (MA)": "Town of Hudson, Massachusetts (Utility Company)",
    "Town of Littleton - (MA)": "Town of Littleton, Massachusetts (Utility Company)"
}

mapped_utilities = [utility_map[u] for u in utilities]

# ============================================================
# 4. Filter URDB for these utilities (full set)
# ============================================================

df_zip = df[df['utility'].isin(mapped_utilities)]

# Keep only residential sector
df_zip_res = df_zip[df_zip['sector'] == "Residential"].copy()

# ============================================================
# 5. Filter to rates effective TODAY
# ============================================================

df_zip_res['startdate'] = pd.to_datetime(df_zip_res['startdate'], errors='coerce')
df_zip_res['enddate'] = pd.to_datetime(df_zip_res['enddate'], errors='coerce')

# End date missing - assume still valid
df_zip_res['enddate'] = df_zip_res['enddate'].fillna(pd.Timestamp("2100-01-01"))

today = pd.Timestamp.today().normalize()

df_active = df_zip_res[
    (df_zip_res['startdate'] <= today) &
    (df_zip_res['enddate'] >= today)
].copy()

print("\nActive residential rate plans:", df_active.shape[0])

# ============================================================
# 6. Filter to single-family, non-low-income, non-special plans
# ============================================================

df_single = df_active.copy()

exclude_multi = [
    "Two", "2-", "2 ", "Two Residential",
    "Three", "3-", "3 ", "Three Residential",
    "Multi", "Multiple",
    "Condominium"
]

exclude_special = [
    "Water Heater",
    "Heat Pump",
    "Off Peak", "Off-peak",
    "Storage", "Thermal",
    "Electric Vehicle", "EV",
    "Interruptible",
    "Time of Use", "TOU",
    "Seasonal"
]

exclude_low_income = [
    "Low Income",
    "Income Eligible",
    "Discount",
    "Lifeline",
    "Assistance",
    "Subsidized",
    "R-2", "R2",
    "A-2", "A2",
]

# Apply all exclusion filters
for pat in exclude_multi + exclude_special + exclude_low_income:
    df_single = df_single[~df_single['name'].str.contains(pat, case=False, na=False)]
    df_single = df_single[~df_single['description'].str.contains(pat, case=False, na=False)]

print("\nSingle-family, non-low-income active rate plans:", df_single.shape[0])

def effective_cents_per_kwh_for_usage(row, monthly_kwh=720.0):
    """
    Compute effective cents/kWh for a given monthly_kwh usage,
    using only energyratestructure/period0/tier* fields.
    """
    usage_remaining = monthly_kwh
    cost = 0.0
    prev_max = 0.0

    for tier in range(0, 16):  # 0..15 tiers
        rate_col = f"energyratestructure/period0/tier{tier}rate"
        max_col  = f"energyratestructure/period0/tier{tier}max"

        if rate_col not in row.index:
            break

        rate = row[rate_col]
        if pd.isna(rate) or not isinstance(rate, (int, float)) or rate <= 0:
            continue

        tier_max = row[max_col] if max_col in row.index else np.nan

        if pd.isna(tier_max) or tier_max <= 0:
            # no upper bound => all remaining usage in this tier
            tier_energy = usage_remaining
        else:
            available   = max(tier_max - prev_max, 0)
            tier_energy = min(usage_remaining, available)

        if tier_energy <= 0:
            prev_max = tier_max if not pd.isna(tier_max) else prev_max
            continue

        cost += tier_energy * rate
        usage_remaining -= tier_energy

        prev_max = tier_max if not pd.isna(tier_max) and tier_max > 0 else prev_max

        if usage_remaining <= 1e-6:
            break

    if monthly_kwh <= 0:
        return None

    effective_rate_dollars = cost / monthly_kwh
    return effective_rate_dollars * 100.0  # cents/kWh

# ============================================================
# 7. Function to extract a representative cents/kWh
# ============================================================

def extract_cents_per_kwh(row):
    """
    Extracts all energy (not demand) tier rates from URDB columns like:
    energyratestructure/periodX/tierYrate
    and returns the lowest tier rate in cents/kWh.
    """
    rates = []

    for col in row.index:
        # Only energy (kWh) charges
        if col.startswith("energyratestructure/") and col.endswith("rate"):
            val = row[col]
            if pd.notna(val) and isinstance(val, (float, int)) and val > 0:
                rates.append(val)

    if not rates:
        return None

    return min(rates) * 100   # Convert $/kWh -> cents/kWh

# Compute cents/kWh column
df_single["cents_per_kwh"] = df_single.apply(extract_cents_per_kwh, axis=1)

df_single["cents_per_kwh_1kWavg"] = df_single.apply(
    effective_cents_per_kwh_for_usage, axis=1
)

df_single[["utility", "name", "cents_per_kwh_1kWavg"]].sort_values(
    "cents_per_kwh_1kWavg"
)

# ============================================================
# 8. Show the final output
# ============================================================

final_output = df_single[['utility', 'name', 'cents_per_kwh', 'cents_per_kwh_1kWavg']]
print("\nFinal filtered rate plans:\n")
print(final_output.sort_values(by='utility'))
