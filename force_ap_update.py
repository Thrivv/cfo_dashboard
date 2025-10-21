import pandas as pd
from datetime import datetime

def update_ap_invoice_status(file_path):
    """Reads the AP_Invoice.csv file, updates the 'Status' column, and saves it."""
    df = pd.read_csv(file_path)
    today = datetime.now().date()

    def get_status(row):
        due_date = pd.to_datetime(row["Due Date"]).date()
        payment_status = str(row["Payment Status"]).lower().strip()

        if payment_status == "paid":
            return "paid"

        delta = (due_date - today).days

        if delta < 0:
            return f"overdue ({abs(delta)} days ago)"
        elif 0 <= delta <= 7:
            return f"upcoming ({delta} days remaining)"
        else:
            return f"future ({delta} days remaining)"

    df["Status"] = df.apply(get_status, axis=1)
    df.to_csv(file_path, index=False)

if __name__ == "__main__":
    update_ap_invoice_status("data/AP_Invoice.csv")
    print("AP_Invoice.csv has been updated successfully.")
