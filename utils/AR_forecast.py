import pandas as pd
import datetime
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import call_vllm

def get_ar_warnings_and_unpaid_invoices():
    """
    Generates warnings for invoices from customers with the highest average forecasted delay,
    and returns the unpaid invoices dataframe.

    Returns:
        tuple: A tuple containing:
            - list: A list of dictionaries, each containing details for a warning.
            - DataFrame: The DataFrame of unpaid invoices.
    """
    ar_invoice_path = 'data/AR_Invoice.csv'
    ar_forecast_path = 'data/AR_forecast.csv'

    try:
        invoices_df = pd.read_csv(ar_invoice_path)
        forecast_df = pd.read_csv(ar_forecast_path)
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found.")
        return [], pd.DataFrame()

    unpaid_invoices = invoices_df[invoices_df['Payment Status'] == 'Not paid'].copy()

    if unpaid_invoices.empty:
        print("No unpaid invoices to analyze.")
        return [], pd.DataFrame()

    unpaid_invoices['Due Date'] = pd.to_datetime(unpaid_invoices['Due Date'])
    forecast_df['date'] = pd.to_datetime(forecast_df['date'])
    
    # Calculate customer-level average delay and payment percentage
    customer_avg_stats = forecast_df.groupby('Customer Name').agg({
        'days_delayed_q50': 'mean',
        'estimate_amount_percent_q50': 'mean'
    }).rename(columns={
        'days_delayed_q50': 'customer_avg_delay',
        'estimate_amount_percent_q50': 'customer_avg_payment_percent'
    })

    merged_df = pd.merge(
        unpaid_invoices,
        forecast_df,
        how='left',
        left_on=['Customer Name', 'Due Date'],
        right_on=['Customer Name', 'date']
    )
    
    # Merge customer average stats into the main dataframe
    merged_df = pd.merge(
        merged_df,
        customer_avg_stats,
        on='Customer Name',
        how='left'
    )
    
    merged_df.dropna(subset=['days_delayed_q50', 'customer_avg_delay'], inplace=True)
    
    if merged_df.empty:
        print("No forecast data available for the given unpaid invoices.")
        return [], unpaid_invoices

    today = datetime.datetime.now().date()
    merged_df['days_diff'] = (merged_df['Due Date'].dt.date - today).apply(lambda x: x.days)

    # New logic: select top 5 warnings based on the customer's average forecasted delay
    top_5_warnings_invoices = merged_df.sort_values(by='customer_avg_delay', ascending=False).head(5)

    warnings = []

    for _, row in top_5_warnings_invoices.iterrows():
        predicted_delay = row['days_delayed_q50']
        predicted_payment_percent = row['estimate_amount_percent_q50'] * 100
        
        days_diff = row['days_diff']
        if days_diff < 0:
            status = f"Overdue by {-days_diff} days"
        else:
            status = f"Upcoming in {days_diff} days"

        prompt = f"""
        Analyze the following Accounts Receivable invoice and provide a concise one-sentence insight as a 'WARNING'.

        - **Customer:** {row['Customer Name']}
        - **Customer Average Delay:** {row['customer_avg_delay']:.0f} days
        - **Customer Average Payment Amount:** {row['customer_avg_payment_percent'] * 100:.2f}%
        - **Invoice:** {row['Invoice No.']}
        - **Due Date:** {row['Due Date'].strftime('%Y-%m-%d')}
        - **Amount:** {row['Amount (AED)']}
        - **Status:** {status}
        - **Forecasted Delay for this Invoice:** {predicted_delay:.0f} days
        - **Forecasted Payment for this Invoice:** {predicted_payment_percent:.2f}% of total

        Generate a 'WARNING' about the risk of late or partial payment, considering the customer's history and the specific forecast for this invoice.
        The insight should be a single sentence. For example: 'High risk of delay for invoice {row['Invoice No.']} from a customer who is often late.'
        """

        warning_text = call_vllm(prompt)
        warnings.append({
            "Customer Name": row['Customer Name'],
            "Invoice No.": row['Invoice No.'],
            "Status": status,
            "Forecasted Delay": f"{predicted_delay:.0f} days",
            "Forecasted Payment Amount": f"{predicted_payment_percent:.2f}%",
            "Warning": warning_text
        })

    return warnings, unpaid_invoices

def get_opportunity_insights(unpaid_invoices):
    """
    Analyzes weekly payment patterns to find opportunities and links them to specific invoices.

    Args:
        unpaid_invoices (DataFrame): A DataFrame of unpaid invoices.

    Returns:
        list: A list of dictionaries, each describing a customer-specific opportunity with an example invoice.
    """
    ar_forecast_path = 'data/AR_forecast.csv'
    try:
        forecast_df = pd.read_csv(ar_forecast_path)
    except FileNotFoundError as e:
        return [f"Error: {e.filename} not found."]

    forecast_df['date'] = pd.to_datetime(forecast_df['date'])
    forecast_df['week_of_month'] = forecast_df['date'].apply(lambda d: (d.day - 1) // 7 + 1)
    
    unpaid_invoices['week_of_month'] = unpaid_invoices['Due Date'].apply(lambda d: (d.day - 1) // 7 + 1)


    opportunities = []
    for customer, group in forecast_df.groupby('Customer Name'):
        weekly_analysis = group.groupby('week_of_month').agg({
            'estimate_amount_percent_q50': 'mean',
            'days_delayed_q50': 'mean'
        }).reset_index()

        if not weekly_analysis.empty:
            # Opportunity 1: Best Early or On-Time Payment with High Percentage
            on_time_or_early_weeks = weekly_analysis[weekly_analysis['days_delayed_q50'] <= 0]
            if not on_time_or_early_weeks.empty:
                best_week = on_time_or_early_weeks.loc[on_time_or_early_weeks['estimate_amount_percent_q50'].idxmax()]
                
                # Find a relevant invoice for this opportunity
                invoice_for_opp = unpaid_invoices[
                    (unpaid_invoices['Customer Name'] == customer) &
                    (unpaid_invoices['week_of_month'] == best_week['week_of_month'])
                ]
                if not invoice_for_opp.empty:
                    invoice_no_opp = invoice_for_opp['Invoice No.'].iloc[0]
                    
                    avg_delay = best_week['days_delayed_q50']
                    if avg_delay == 0:
                        delay_str = "On time"
                    else:
                        delay_str = f"{abs(avg_delay):.0f} days early"

                    opportunities.append({
                        "Customer Name": customer,
                        "Type": "On-Time/Early & High %",
                        "Week of Month": int(best_week['week_of_month']),
                        "Average Delay": delay_str,
                        "Average Payment %": f"{best_week['estimate_amount_percent_q50']:.2%}",
                        "Example Invoice No.": invoice_no_opp
                    })

    return opportunities


if __name__ == '__main__':
    print("--- Top AR Warnings ---")
    warnings_data, unpaid_invoices_df = get_ar_warnings_and_unpaid_invoices()
    if warnings_data:
        # Manual table formatting for terminal output
        header = "| {:<25} | {:<12} | {:<25} | {:<18} | {:<28} | {:<70} |".format(
            "Customer Name", "Invoice No.", "Status", "Forecasted Delay", "Forecasted Payment Amount", "Warning"
        )
        print(header)
        print("-" * len(header))
        for row in warnings_data:
            print("| {:<25} | {:<12} | {:<25} | {:<18} | {:<28} | {:<70} |".format(
                row["Customer Name"],
                row["Invoice No."],
                row["Status"],
                row["Forecasted Delay"],
                row["Forecasted Payment Amount"],
                row["Warning"]
            ))

    if not unpaid_invoices_df.empty:
        print("\n--- Customer Payment Opportunities ---")
        opportunity_insights = get_opportunity_insights(unpaid_invoices_df)
        if opportunity_insights:
            # Manual table formatting for terminal output
            opp_header = "| {:<25} | {:<25} | {:<15} | {:<20} | {:<20} | {:<20} |".format(
                "Customer Name", "Type", "Week of Month", "Average Delay", "Average Payment %", "Example Invoice No."
            )
            print(opp_header)
            print("-" * len(opp_header))
            for opp_row in opportunity_insights:
                print("| {:<25} | {:<25} | {:<15} | {:<20} | {:<20} | {:<20} |".format(
                    opp_row["Customer Name"],
                    opp_row["Type"],
                    opp_row["Week of Month"],
                    opp_row["Average Delay"],
                    opp_row["Average Payment %"],
                    opp_row["Example Invoice No."]
                ))
