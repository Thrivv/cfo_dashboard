import json
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import get_data_loader


class DataChunkService:
    """Service for providing dataset to LLM in manageable chunks."""

    def __init__(self):
        self.data_loader = get_data_loader()
        self._chunks: List[Dict[str, Any]] = []
        self._chunk_size = 0
        self._total_records = 0

    def load_and_chunk_data(self) -> bool:
        """Load data and split into 5 chunks for LLM processing.

        Returns:
            bool: True if data loaded and chunked successfully
        """
        try:
            # Load data using existing data loader
            if not self.data_loader.load_data():
                return False

            raw_data = self.data_loader.get_raw_data()
            if raw_data is None or raw_data.empty:
                return False

            self._total_records = len(raw_data)
            self._chunk_size = max(
                1, self._total_records // 5
            )  # Ensure at least 1 record per chunk

            # Split data into 5 chunks
            self._chunks = []
            for i in range(5):
                start_idx = i * self._chunk_size
                end_idx = start_idx + self._chunk_size if i < 4 else self._total_records

                chunk_data = raw_data.iloc[start_idx:end_idx]

                chunk_info = {
                    "chunk_number": i + 1,
                    "total_chunks": 5,
                    "start_index": start_idx,
                    "end_index": end_idx - 1,
                    "record_count": len(chunk_data),
                    "data": chunk_data.to_dict("records"),
                    "columns": list(chunk_data.columns),
                    "summary": self._generate_chunk_summary(chunk_data, i + 1),
                }

                self._chunks.append(chunk_info)

            return True

        except Exception as e:
            print(f"Error loading and chunking data: {str(e)}")
            return False

    def _generate_chunk_summary(
        self, chunk_data: pd.DataFrame, chunk_num: int
    ) -> Dict[str, Any]:
        """Generate summary statistics for a data chunk."""
        try:
            summary = {
                "chunk_number": chunk_num,
                "record_count": len(chunk_data),
                "date_range": None,
                "key_metrics": {},
            }

            # Get date range if date column exists
            date_columns = [
                col
                for col in chunk_data.columns
                if "date" in col.lower() or "time" in col.lower()
            ]
            if date_columns:
                date_col = date_columns[0]
                summary["date_range"] = {
                    "start": str(chunk_data[date_col].min()),
                    "end": str(chunk_data[date_col].max()),
                }

            # Calculate key financial metrics for this chunk
            numeric_columns = chunk_data.select_dtypes(include=["number"]).columns

            for col in numeric_columns:
                if chunk_data[col].notna().any():
                    summary["key_metrics"][col] = {
                        "sum": float(chunk_data[col].sum()),
                        "mean": float(chunk_data[col].mean()),
                        "min": float(chunk_data[col].min()),
                        "max": float(chunk_data[col].max()),
                    }

            return summary

        except Exception as e:
            print(f"Error generating chunk summary: {str(e)}")
            return {"chunk_number": chunk_num, "error": str(e)}

    def get_chunk(self, chunk_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific data chunk.

        Args:
            chunk_number: Chunk number (1-5)

        Returns:
            Dict containing chunk data or None if not found
        """
        if not self._chunks or chunk_number < 1 or chunk_number > 5:
            return None

        return self._chunks[chunk_number - 1]

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Get all data chunks."""
        return self._chunks

    def get_chunk_summary(self) -> Dict[str, Any]:
        """Get summary of all chunks."""
        if not self._chunks:
            return {"error": "No data chunks available"}

        return {
            "total_chunks": len(self._chunks),
            "total_records": self._total_records,
            "chunk_size": self._chunk_size,
            "chunks": [
                {
                    "chunk_number": chunk["chunk_number"],
                    "record_count": chunk["record_count"],
                    "summary": chunk["summary"],
                }
                for chunk in self._chunks
            ],
        }

    def get_chunk_for_llm(self, chunk_number: int) -> str:
        """Get a data chunk formatted for LLM consumption.

        Args:
            chunk_number: Chunk number (1-5)

        Returns:
            String formatted for LLM input
        """
        chunk = self.get_chunk(chunk_number)
        if not chunk:
            return "Chunk not available"

        # Format chunk data for LLM (optimized for size)
        llm_format = f"""DATA CHUNK {chunk['chunk_number']} of {chunk['total_chunks']}:
Record Range: {chunk['start_index']} to {chunk['end_index']} (Total: {chunk['record_count']} records)

COLUMNS: {', '.join(chunk['columns'])}

SUMMARY STATISTICS:
{json.dumps(chunk['summary'], indent=2)}

SAMPLE DATA (first 3 records):
{json.dumps(chunk['data'][:3], indent=2)}
"""
        return llm_format

    def get_all_chunks_for_llm(self) -> str:
        """Get all chunks formatted for LLM consumption with aggregated data."""
        if not self._chunks:
            return "No data chunks available"

        # Get raw data for aggregation
        raw_data = self.data_loader.get_raw_data()
        if raw_data is None or raw_data.empty:
            return "No data available"

        # Calculate aggregated metrics by department
        dept_metrics = raw_data.groupby('Business Unit / Department').agg({
            'Revenue (Actual)': 'sum',
            'Revenue (Budget / Forecast)': 'sum',
            'Cost of Goods Sold (COGS)': 'sum',
            'Gross Profit': 'sum',
            'Operating Expenses (OPEX)': 'sum',
            'EBITDA': 'sum',
            'Net Income': 'sum',
            'Cash Inflows': 'sum',
            'Cash Outflows': 'sum',
            'Net Cash Flow': 'sum',
            'Total Assets': 'sum',
            'Total Liabilities': 'sum',
            'Equity': 'sum',
            'Headcount': 'sum',
            'Capital Expenditure (CapEx)': 'sum',
            'Operational Expenditure (OpEx)': 'sum'
        }).round(0)

        # Calculate totals
        total_revenue = dept_metrics['Revenue (Actual)'].sum()
        total_records = len(raw_data)
        date_range = f"{raw_data['Date / Period'].min()} to {raw_data['Date / Period'].max()}"

        # Format for LLM
        llm_format = f"""FINANCIAL DATA SUMMARY:
Total Records: {total_records:,}
Date Range: {date_range}
Total Revenue (Actual): ${total_revenue:,.0f}

DEPARTMENTAL FINANCIAL METRICS:
"""

        # Add department metrics
        for dept in dept_metrics.index:
            dept_data = dept_metrics.loc[dept]
            llm_format += f"""
{dept}:
  Revenue (Actual): ${dept_data['Revenue (Actual)']:,.0f}
  Revenue (Budget): ${dept_data['Revenue (Budget / Forecast)']:,.0f}
  Gross Profit: ${dept_data['Gross Profit']:,.0f}
  EBITDA: ${dept_data['EBITDA']:,.0f}
  Net Income: ${dept_data['Net Income']:,.0f}
  Cash Inflows: ${dept_data['Cash Inflows']:,.0f}
  Cash Outflows: ${dept_data['Cash Outflows']:,.0f}
  Net Cash Flow: ${dept_data['Net Cash Flow']:,.0f}
  Total Assets: ${dept_data['Total Assets']:,.0f}
  Headcount: {dept_data['Headcount']:,.0f}
  CapEx: ${dept_data['Capital Expenditure (CapEx)']:,.0f}
  OpEx: ${dept_data['Operational Expenditure (OpEx)']:,.0f}
"""

        # Add complete historical data by year
        llm_format += f"""

COMPLETE HISTORICAL DATA BY YEAR:
"""
        
        # Group by year and show all years
        raw_data['Year'] = pd.to_datetime(raw_data['Date / Period']).dt.year
        yearly_data = raw_data.groupby(['Year', 'Business Unit / Department']).agg({
            'Revenue (Actual)': 'sum',
            'Revenue (Budget / Forecast)': 'sum',
            'Gross Profit': 'sum',
            'Net Income': 'sum'
        }).round(0)
        
        # Show data for each year
        for year in sorted(raw_data['Year'].unique()):
            year_data = yearly_data.loc[year]
            llm_format += f"\nYEAR {year}:\n"
            for dept in year_data.index:
                dept_data = year_data.loc[dept]
                llm_format += f"  {dept}:\n"
                llm_format += f"    Revenue (Actual): ${dept_data['Revenue (Actual)']:,.0f}\n"
                llm_format += f"    Revenue (Budget): ${dept_data['Revenue (Budget / Forecast)']:,.0f}\n"
                llm_format += f"    Gross Profit: ${dept_data['Gross Profit']:,.0f}\n"
                llm_format += f"    Net Income: ${dept_data['Net Income']:,.0f}\n"

        return llm_format


# Global instance
_chunk_service = None


def get_chunk_service() -> DataChunkService:
    """Get the global data chunk service instance."""
    global _chunk_service
    if _chunk_service is None:
        _chunk_service = DataChunkService()
    return _chunk_service
