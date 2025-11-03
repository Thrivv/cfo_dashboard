import pandas as pd
from typing import Dict, List

def get_rebate_suggestions(df: pd.DataFrame, discounts: List[Dict[str, any]]) -> pd.DataFrame:
    """
    Applies rebate suggestions to the AP Invoice data.
    Args:
        df (pd.DataFrame): The AP Invoice data.
        discounts (List[Dict[str, any]]): A list of dictionaries with company names and their discounts.
    Returns:
        pd.DataFrame: The DataFrame with rebate suggestions.
    """
    
    for discount_info in discounts:
        supplier_name = discount_info.get("company_name")
        discount_percentage = discount_info.get("discount_percentage")

        if supplier_name and discount_percentage:
            # Remove percentage sign and convert to float
            if isinstance(discount_percentage, str):
                discount_percentage = float(discount_percentage.strip('%'))
            
            # Find matching rows and apply the discount
            mask = df["Supplier Name"] == supplier_name
            df.loc[mask, "Discount"] = discount_percentage
            
            # Calculate the final amount to pay after discount
            df.loc[mask, "Final Amount to Pay"] = df["Amount (AED)"] * (1 - discount_percentage / 100)

    return df
