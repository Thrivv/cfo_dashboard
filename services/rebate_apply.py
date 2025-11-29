"""
Applies rebate (discount/penalty) suggestions to the AP Invoice data and saves the result.
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, List

# Adjust path for importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Optional: if you ever still want to re-query dynamically
# from services.rebate import query_rebate_collection


def normalize_supplier_name(name: str) -> str:
    """Cleans and normalizes supplier name for consistent matching."""
    if not isinstance(name, str):
        return ""
    return name.strip().lower().replace(".", "").replace(",", "")


def load_rebate_json() -> List[Dict[str, any]]:
    """
    Loads pre-extracted rebate data from data/rebate_output.json.
    """
    rebate_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "rebate_output.json"
    )

    if not os.path.exists(rebate_file):
        raise FileNotFoundError(
            f"❌ rebate_output.json not found at {rebate_file}. Please run `python rebate.py` first."
        )

    with open(rebate_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📄 Loaded {len(data)} rebate entries from {rebate_file}")
    return data


def get_rebate_suggestions(df: pd.DataFrame, rebates: List[Dict[str, any]]) -> pd.DataFrame:
    """
    Applies both discount and penalty suggestions to the AP Invoice data.
    """

    expected_cols = [
        "Discount", "Discount Note", "Final Amount with Discount",
        "Penalty", "Penalty Note", "Final Amount with Penalty"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Normalize supplier column name
    supplier_col = None
    for possible in ["Supplier Name", "Supplier_Name", "Supplier"]:
        if possible in df.columns:
            supplier_col = possible
            break
    if supplier_col is None:
        raise KeyError("No 'Supplier Name' column found in dataset!")

    # Clean supplier names
    df["_clean_supplier"] = df[supplier_col].apply(normalize_supplier_name)

    print(f"\n🔍 Applying rebates and penalties to {len(df)} invoices...")

    for info in rebates:
        supplier = normalize_supplier_name(info.get("supplier_name"))
        if not supplier:
            continue

        discount_str = info.get("discount")
        penalty_str = info.get("penalty")
        discount_note = info.get("discount_clause")
        penalty_note = info.get("penalty_clause")

        mask = df["_clean_supplier"] == supplier
        if not mask.any():
            print(f"⚠️  No match found for supplier: {info.get('supplier_name')}")
            continue

        # Convert % strings safely
        def to_num(val):
            if not val:
                return None
            try:
                return float(str(val).replace("%", "").strip())
            except ValueError:
                return None

        discount_val = to_num(discount_str)
        penalty_val = to_num(penalty_str)

        # Apply discount
        if discount_val is not None:
            df.loc[mask, "Discount"] = discount_val
            df.loc[mask, "Discount Note"] = discount_note
            df.loc[mask, "Final Amount with Discount"] = (
                df.loc[mask, "Amount (AED)"] * (1 - discount_val / 100)
            ).round(2)
            print(f"✅ Applied {discount_val}% discount for {info.get('supplier_name')}")

        # Apply penalty
        if penalty_val is not None:
            df.loc[mask, "Penalty"] = penalty_val
            df.loc[mask, "Penalty Note"] = penalty_note
            df.loc[mask, "Final Amount with Penalty"] = (
                df.loc[mask, "Amount (AED)"] * (1 + penalty_val / 100)
            ).round(2)
            print(f"✅ Applied {penalty_val}% penalty for {info.get('supplier_name')}")

    df.drop(columns=["_clean_supplier"], inplace=True)
    return df


def apply_and_save_rebates():
    """
    Loads rebate data from rebate_output.json, applies it to Rebate_ap.csv, and saves results.
    """

    try:
        rebates = load_rebate_json()
    except Exception as e:
        print(f"Error loading rebate data: {e}")
        return

    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "AP_Invoice.csv"
    )

    if not os.path.exists(file_path):
        print(f"❌ Error: {file_path} not found.")
        return

    print(f"📂 Loading AP dataset from: {file_path}")
    df = pd.read_csv(file_path)
    print(f"✅ Loaded {len(df)} records.")

    updated_df = get_rebate_suggestions(df, rebates)

    updated_df.to_csv(file_path, index=False)
    print(f"💾 Saved updated dataset to {file_path}\n")


if __name__ == "__main__":
    apply_and_save_rebates()
