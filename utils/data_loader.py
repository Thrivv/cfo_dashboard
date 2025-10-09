import pandas as pd
import os
import streamlit as st
from typing import Optional, Dict, Any


class DataLoaderService:
    """Centralized service for loading and managing CFO dashboard data."""

    def __init__(self):
        self._raw_data: Optional[pd.DataFrame] = None
        self._processed_data: Optional[pd.DataFrame] = None
        self._data_path = "data/cfo_dashboard_data.csv"
        self._is_loaded = False

    def load_data(self) -> bool:
        """
        Load data from CSV file and perform initial processing.

        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self._data_path):
                print(f"Data file not found: {self._data_path}")
                return False

            print(f"Loading data from: {self._data_path}")
            self._raw_data = pd.read_csv(self._data_path)

            if self._raw_data.empty:
                print("Data file is empty")
                return False

            self._process_data()

            self._is_loaded = True
            print(
                f"Data loaded successfully: {self._raw_data.shape[0]} records, {self._raw_data.shape[1]} columns"
            )
            return True

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False

    def _process_data(self):
        """Process raw data for application use."""
        if self._raw_data is None:
            return

        self._processed_data = self._raw_data.copy()

        try:
            self._processed_data["Date"] = pd.to_datetime(
                self._processed_data["Date / Period"], format="%m/%d/%Y"
            )
        except ValueError:
            try:
                self._processed_data["Date"] = pd.to_datetime(
                    self._processed_data["Date / Period"], format="%d-%m-%y"
                )
            except ValueError:
                self._processed_data["Date"] = pd.to_datetime(
                    self._processed_data["Date / Period"]
                )

        numeric_columns = [
            "Revenue (Actual)",
            "Revenue (Budget / Forecast)",
            "Cost of Goods Sold (COGS)",
            "Gross Profit",
            "Operating Expenses (OPEX)",
            "EBITDA",
            "Net Income",
            "Cash Inflows",
            "Cash Outflows",
            "Net Cash Flow",
            "Cash Balance",
            "Total Assets",
            "Total Liabilities",
            "Equity",
            "Working Capital",
            "Current Ratio",
            "Debt-to-Equity Ratio",
            "Return on Equity (ROE)",
            "Return on Assets (ROA)",
            "Inventory Value",
            "Inventory Turnover",
        ]

        for col in numeric_columns:
            if col in self._processed_data.columns:
                self._processed_data[col] = pd.to_numeric(
                    self._processed_data[col], errors="coerce"
                )

    def get_raw_data(self) -> Optional[pd.DataFrame]:
        """
        Get the raw, unprocessed data with caching.

        Returns:
            pd.DataFrame or None: Raw data if loaded, None otherwise
        """
        # Use Streamlit caching for better performance
        cache_key = "cfo_raw_data"
        if cache_key not in st.session_state:
            if not self.load_data():
                return None
            st.session_state[cache_key] = self._raw_data
        return st.session_state[cache_key]

    def get_processed_data(self) -> Optional[pd.DataFrame]:
        """
        Get the processed data with proper data types and formatting.

        Returns:
            pd.DataFrame or None: Processed data if loaded, None otherwise
        """
        # Use Streamlit caching for better performance
        cache_key = "cfo_processed_data"
        if cache_key not in st.session_state:
            if not self.load_data():
                return None
            st.session_state[cache_key] = self._processed_data
        return st.session_state[cache_key]

    def get_latest_data(self) -> Optional[pd.Series]:
        """
        Get the latest data record (most recent period).

        Returns:
            pd.Series or None: Latest data record if available, None otherwise
        """
        processed_data = self.get_processed_data()
        if processed_data is not None and not processed_data.empty:
            return processed_data.iloc[-1]
        return None

    def clear_cache(self):
        """Clear cached data to force reload."""
        cache_keys = ["cfo_raw_data", "cfo_processed_data"]
        for key in cache_keys:
            if key in st.session_state:
                del st.session_state[key]
        self._is_loaded = False

    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the loaded data.

        Returns:
            Dict[str, Any]: Data summary information
        """
        if not self._is_loaded:
            self.load_data()

        if self._raw_data is None:
            return {"status": "no_data", "message": "No data loaded"}

        return {
            "status": "loaded",
            "records": len(self._raw_data),
            "columns": len(self._raw_data.columns),
            "date_range": {
                "start": self._raw_data["Date / Period"].min(),
                "end": self._raw_data["Date / Period"].max(),
            },
            "business_units": self._raw_data["Business Unit / Department"]
            .unique()
            .tolist()
            if "Business Unit / Department" in self._raw_data.columns
            else [],
            "file_path": self._data_path,
        }

    def is_data_loaded(self) -> bool:
        """
        Check if data is currently loaded.

        Returns:
            bool: True if data is loaded, False otherwise
        """
        return self._is_loaded

    def reload_data(self) -> bool:
        """
        Reload data from the source file.

        Returns:
            bool: True if reloaded successfully, False otherwise
        """
        self._is_loaded = False
        self._raw_data = None
        self._processed_data = None
        return self.load_data()


_data_loader = DataLoaderService()


def get_data_loader() -> DataLoaderService:
    """
    Get the global data loader instance.

    Returns:
        DataLoaderService: Global data loader instance
    """
    return _data_loader


def load_cfo_data() -> Optional[pd.DataFrame]:
    """
    Load CFO data from centralized data loader, converted to simplified schema used by UI.

    Returns:
        pd.DataFrame or None: CFO data with simplified schema if available, None otherwise
    """
    try:
        raw_df = _data_loader.get_raw_data()

        if raw_df is None or raw_df.empty:
            return None

        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(raw_df["Date / Period"], errors="coerce"),
                "Cash_on_Hand": pd.to_numeric(raw_df["Cash Balance"], errors="coerce"),
                "Burn_Rate": pd.to_numeric(raw_df["Cash Outflows"], errors="coerce"),
                "Runway_Months": (
                    pd.to_numeric(raw_df["Cash Balance"], errors="coerce")
                    / (pd.to_numeric(raw_df["Cash Outflows"], errors="coerce") / 30)
                ).round(1),
                "Outstanding_Invoices": pd.to_numeric(
                    raw_df["Accounts Receivable (AR)"], errors="coerce"
                ),
            }
        )
        return df.dropna().sort_values("Date")
    except Exception:
        return None


def load_raw_dataframe() -> Optional[pd.DataFrame]:
    """
    Load raw dataframe for backward compatibility.

    Returns:
        pd.DataFrame or None: Raw dataframe if available, None otherwise
    """
    return _data_loader.get_raw_data()


def get_latest_cfo_data() -> Optional[pd.Series]:
    """
    Get latest CFO data record.

    Returns:
        pd.Series or None: Latest data record if available, None otherwise
    """
    return _data_loader.get_latest_data()


def get_data_summary() -> Dict[str, Any]:
    """
    Get data summary information.

    Returns:
        Dict[str, Any]: Data summary
    """
    return _data_loader.get_data_summary()


def initialize_data() -> bool:
    """
    Initialize and load data for the application.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    return _data_loader.load_data()


if __name__ != "__main__":
    initialize_data()
