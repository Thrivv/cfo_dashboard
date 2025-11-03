"""
Applies rebate suggestions to the AP Invoice data and saves the result.
"""
import os
import sys
import pandas as pd
import subprocess
import json
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.query_rebate import query_rebate_collection
def get_rebate_suggestions(df: pd.DataFrame, discounts: List[Dict[str, any]]) -> pd.DataFrame:
    """
    Applies rebate suggestions to the AP Invoice data.
    Args:
        df (pd.DataFrame): The AP Invoice data.
        discounts (List[Dict[str, any]]): A list of dictionaries with supplier names and their discounts.
    Returns:
        pd.DataFrame: The DataFrame with rebate suggestions.
    """
    
    for discount_info in discounts:
        supplier_name = discount_info.get("supplier_name")
        discount_percentage = discount_info.get("discount_percentage")

        if supplier_name and discount_percentage:
            if isinstance(discount_percentage, str):
                try:
                    discount_percentage = float(discount_percentage.strip('%'))
                except ValueError:
                    continue
            
            mask = df["Supplier Name"] == supplier_name
            df.loc[mask, "Discount"] = discount_percentage
            df.loc[mask, "Final Amount to Pay"] = df["Amount (AED)"] * (1 - discount_percentage / 100)

    return df

def apply_and_save_rebates():
    """
    Fetches rebate information by running an external script, applies it to the AP Invoice data, 
    and saves the updated DataFrame.
    """
    try:
        discounts = query_rebate_collection("Get all company discounts")
    except Exception as e:
        print(f"Error getting discounts: {e}")
        return

    if not discounts:
        print("Could not retrieve any discounts. Exiting.")
        return

    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'AP_Invoice_rebate.csv')
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    df_with_rebates = get_rebate_suggestions(df, discounts)

    try:
        df_with_rebates.to_csv(file_path, index=False)
        print(f"Successfully updated {file_path} with rebate information.")
    except Exception as e:
        print(f"Error saving the updated file: {e}")

if __name__ == "__main__":
    apply_and_save_rebates()