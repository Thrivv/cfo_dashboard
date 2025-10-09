import pandas as pd
import warnings
from datetime import datetime


def parse_quarterly_date(date_str):
    """Parse quarterly date strings like '2021Q1' to proper datetime"""
    try:
        if 'Q' in str(date_str):
            year, quarter = str(date_str).split('Q')
            # Convert quarter to month (Q1=March, Q2=June, Q3=September, Q4=December)
            quarter_months = {'1': '03', '2': '06', '3': '09', '4': '12'}
            month = quarter_months.get(quarter, '03')
            return pd.to_datetime(f"{year}-{month}-01", format='%Y-%m-%d')
        else:
            return pd.to_datetime(date_str)
    except:
        return pd.to_datetime(date_str)


def parse_date_column(date_series):
    """Parse date column with multiple format support - optimized version"""
    # Try to parse the entire series at once for better performance
    try:
        # Try MM/DD/YYYY format first
        result = pd.to_datetime(date_series, format='%m/%d/%Y', errors='coerce')
        if not result.isna().all():
            return result
    except (ValueError, TypeError):
        pass
    
    try:
        # Try DD-MM-YY format
        result = pd.to_datetime(date_series, format='%d-%m-%y', errors='coerce')
        if not result.isna().all():
            return result
    except (ValueError, TypeError):
        pass
    
    try:
        # Try YYYY-MM-DD format
        result = pd.to_datetime(date_series, format='%Y-%m-%d', errors='coerce')
        if not result.isna().all():
            return result
    except (ValueError, TypeError):
        pass
    
    try:
        # Try automatic parsing
        result = pd.to_datetime(date_series, errors='coerce')
        if not result.isna().all():
            return result
    except (ValueError, TypeError):
        pass
    
    # If all fails, return NaT for all values
    return pd.Series([pd.NaT] * len(date_series), index=date_series.index)


def apply_date_range_filter(df, date_range):
    """Apply date range filtering"""
    if 'Date' not in df.columns or df.empty:
        return df
    
    # Ensure Date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
    
    if df.empty:
        return df
    
    max_date = df['Date'].max()
    
    if date_range == "Last 30 Days":
        start_date = max_date - pd.Timedelta(days=30)
    elif date_range == "Last 90 Days":
        start_date = max_date - pd.Timedelta(days=90)
    elif date_range == "Last 6 Months":
        start_date = max_date - pd.Timedelta(days=180)
    elif date_range == "Last Year":
        start_date = max_date - pd.Timedelta(days=365)
    elif date_range == "All Time":
        return df
    else:
        # Default to last 30 days
        start_date = max_date - pd.Timedelta(days=30)
    
    return df[df['Date'] >= start_date]


def apply_period_aggregation(df, period_type):
    """Apply period-based aggregation"""
    if 'Date' not in df.columns or df.empty:
        return df
    
    # Create period column
    if period_type == "Quarterly":
        df['Period'] = df['Date'].dt.to_period('Q')
    elif period_type == "Yearly":
        df['Period'] = df['Date'].dt.to_period('Y')
    else:
        return df
    
    # Get numeric columns for aggregation
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if 'Date' in numeric_cols:
        numeric_cols.remove('Date')
    
    if not numeric_cols:
        return df
    
    # Group by period and business unit (if exists)
    group_cols = ['Period']
    if 'Business Unit / Department' in df.columns:
        group_cols.append('Business Unit / Department')
    
    # Aggregate numeric columns
    agg_dict = {col: 'sum' for col in numeric_cols}
    aggregated_df = df.groupby(group_cols).agg(agg_dict).reset_index()
    
    # Update Date / Period column for display
    if period_type == "Quarterly":
        aggregated_df['Date / Period'] = aggregated_df['Period'].astype(str)
        # Create Date column for charts
        aggregated_df['Date'] = aggregated_df['Period'].dt.end_time
    elif period_type == "Yearly":
        aggregated_df['Date / Period'] = aggregated_df['Period'].astype(str)
        # Create Date column for charts
        aggregated_df['Date'] = aggregated_df['Period'].dt.end_time
    
    return aggregated_df


def apply_filters(df, filters):
    """
    Apply comprehensive filtering to the dataframe based on user selections
    
    Args:
        df: Raw dataframe
        filters: Dictionary containing filter settings
    
    Returns:
        Filtered dataframe
    """
    if df is None or df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Step 1: Parse dates properly for chart compatibility
    if 'Date / Period' in filtered_df.columns:
        filtered_df['Date'] = parse_date_column(filtered_df['Date / Period'])
        # Remove rows where date parsing failed
        filtered_df = filtered_df.dropna(subset=['Date'])
        
        # Ensure Date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['Date']):
            filtered_df['Date'] = pd.to_datetime(filtered_df['Date'], errors='coerce')
            filtered_df = filtered_df.dropna(subset=['Date'])
    
    # Step 2: Apply business unit filter
    if filters.get('unit') and filters['unit'] != "All":
        filtered_df = filtered_df[filtered_df['Business Unit / Department'] == filters['unit']]
    
    # Step 3: Apply date range filter
    date_range = filters.get('date_range')
    
    if date_range and isinstance(date_range, list) and len(date_range) >= 1:
        start_date = date_range[0]
        end_date = date_range[1] if len(date_range) > 1 else start_date
        
        if start_date:
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(filtered_df['Date']):
                filtered_df['Date'] = pd.to_datetime(filtered_df['Date'])
            
            # Apply date range filter
            filtered_df = filtered_df[
                (filtered_df['Date'] >= pd.to_datetime(start_date)) & 
                (filtered_df['Date'] <= pd.to_datetime(end_date))
            ]
    
    # Step 4: Apply period aggregation
    period_type = filters.get('period', 'Monthly')
    
    if period_type and period_type != "Monthly":
        filtered_df = apply_period_aggregation(filtered_df, period_type)
    
    return filtered_df


def get_filter_summary(filtered_df, filters):
    """
    Get a summary of applied filters and data statistics
    
    Args:
        filtered_df: Filtered dataframe
        filters: Applied filter settings
    
    Returns:
        Dictionary with filter summary information
    """
    summary = {
        'record_count': len(filtered_df),
        'active_filters': [],
        'data_shape': filtered_df.shape if not filtered_df.empty else (0, 0)
    }
    
    # Check which filters are active
    if filters.get('unit') and filters['unit'] != "All":
        summary['active_filters'].append(f"Unit: {filters['unit']}")
    
    date_range = filters.get('date_range')
    
    if date_range and isinstance(date_range, list) and len(date_range) >= 1:
        start_date = date_range[0]
        end_date = date_range[1] if len(date_range) > 1 else start_date
        
        if start_date:
            if start_date == end_date:
                summary['active_filters'].append(f"Date: {start_date}")
            else:
                summary['active_filters'].append(f"Date Range: {start_date} to {end_date}")
    
    # Check period filter - only show if it's been explicitly changed from default
    period = filters.get('period', 'Yearly')  # Updated default to match new default
    if period and period != "Yearly":  # Only show if not the default
        summary['active_filters'].append(f"Period: {period}")
    
    return summary


def validate_filters(filters):
    """
    Validate filter settings and provide defaults if needed
    
    Args:
        filters: Filter dictionary
    
    Returns:
        Validated filter dictionary
    """
    default_filters = {
        'unit': "All",
        'start_date': None,
        'end_date': None,
        'date_range': None,
        'period': "Yearly"
    }
    
    # Merge with defaults
    validated_filters = {**default_filters, **filters}
    
    # Validate period
    valid_periods = ["Monthly", "Quarterly", "Yearly"]
    if validated_filters['period'] not in valid_periods:
        validated_filters['period'] = "Monthly"
    
    return validated_filters