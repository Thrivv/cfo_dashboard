import pandas as pd
import json
from typing import List, Dict, Any, Optional
from .data_loader import get_data_loader


class DataChunkService:
    """Service for providing dataset to LLM in manageable chunks."""
    
    def __init__(self):
        self.data_loader = get_data_loader()
        self._chunks: List[Dict[str, Any]] = []
        self._chunk_size = 0
        self._total_records = 0
        
    def load_and_chunk_data(self) -> bool:
        """
        Load data and split into 5 chunks for LLM processing.
        
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
            self._chunk_size = max(1, self._total_records // 5)  # Ensure at least 1 record per chunk
            
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
                    "data": chunk_data.to_dict('records'),
                    "columns": list(chunk_data.columns),
                    "summary": self._generate_chunk_summary(chunk_data, i + 1)
                }
                
                self._chunks.append(chunk_info)
            
            return True
            
        except Exception as e:
            print(f"Error loading and chunking data: {str(e)}")
            return False
    
    def _generate_chunk_summary(self, chunk_data: pd.DataFrame, chunk_num: int) -> Dict[str, Any]:
        """Generate summary statistics for a data chunk."""
        try:
            summary = {
                "chunk_number": chunk_num,
                "record_count": len(chunk_data),
                "date_range": None,
                "key_metrics": {}
            }
            
            # Get date range if date column exists
            date_columns = [col for col in chunk_data.columns if 'date' in col.lower() or 'time' in col.lower()]
            if date_columns:
                date_col = date_columns[0]
                summary["date_range"] = {
                    "start": str(chunk_data[date_col].min()),
                    "end": str(chunk_data[date_col].max())
                }
            
            # Calculate key financial metrics for this chunk
            numeric_columns = chunk_data.select_dtypes(include=['number']).columns
            
            for col in numeric_columns:
                if chunk_data[col].notna().any():
                    summary["key_metrics"][col] = {
                        "sum": float(chunk_data[col].sum()),
                        "mean": float(chunk_data[col].mean()),
                        "min": float(chunk_data[col].min()),
                        "max": float(chunk_data[col].max())
                    }
            
            return summary
            
        except Exception as e:
            print(f"Error generating chunk summary: {str(e)}")
            return {"chunk_number": chunk_num, "error": str(e)}
    
    def get_chunk(self, chunk_number: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific data chunk.
        
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
                    "summary": chunk["summary"]
                }
                for chunk in self._chunks
            ]
        }
    
    def get_chunk_for_llm(self, chunk_number: int) -> str:
        """
        Get a data chunk formatted for LLM consumption.
        
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
        """Get all chunks formatted for LLM consumption (optimized for size)."""
        if not self._chunks:
            return "No data chunks available"
        
        # Create a more compact format for LLM
        llm_format = f"""FINANCIAL DATASET OVERVIEW:
Total Records: {self._total_records}
Total Chunks: {len(self._chunks)}
Chunk Size: {self._chunk_size} records per chunk

DATASET STRUCTURE:
"""
        
        for chunk in self._chunks:
            llm_format += f"""
CHUNK {chunk['chunk_number']}:
- Records: {chunk['record_count']} (Range: {chunk['start_index']}-{chunk['end_index']})
- Key Metrics: {len(chunk['summary'].get('key_metrics', {}))} financial indicators
- Date Range: {chunk['summary'].get('date_range', 'N/A')}
- Sample Data: {len(chunk['data'][:2])} sample records available

SAMPLE RECORDS:
"""
            # Add actual sample records
            for i, record in enumerate(chunk['data'][:2], 1):
                llm_format += f"Record {i}: {record}\n"
        
        # Add aggregated summary statistics
        llm_format += f"""

AGGREGATED SUMMARY:
"""
        
        # Calculate overall statistics
        all_metrics = {}
        for chunk in self._chunks:
            for metric, stats in chunk['summary'].get('key_metrics', {}).items():
                if metric not in all_metrics:
                    all_metrics[metric] = {'sum': 0, 'count': 0, 'min': float('inf'), 'max': float('-inf')}
                all_metrics[metric]['sum'] += stats['sum']
                all_metrics[metric]['count'] += 1
                all_metrics[metric]['min'] = min(all_metrics[metric]['min'], stats['min'])
                all_metrics[metric]['max'] = max(all_metrics[metric]['max'], stats['max'])
        
        for metric, stats in all_metrics.items():
            if stats['count'] > 0:
                llm_format += f"- {metric}: Total={stats['sum']:.2f}, Min={stats['min']:.2f}, Max={stats['max']:.2f}\n"
        
        return llm_format


# Global instance
_chunk_service = None

def get_chunk_service() -> DataChunkService:
    """Get the global data chunk service instance."""
    global _chunk_service
    if _chunk_service is None:
        _chunk_service = DataChunkService()
    return _chunk_service
