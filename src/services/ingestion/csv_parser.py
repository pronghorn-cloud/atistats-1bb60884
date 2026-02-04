"""CSV file parser for ATI data ingestion."""

import csv
import io
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, BinaryIO, TextIO, Union
import chardet


class CSVParseError(Exception):
    """Raised when CSV parsing fails."""
    pass


class CSVParser:
    """Parser for CSV files containing ATI data.
    
    Supports:
    - Auto-detection of encoding
    - Auto-detection of delimiter
    - Header normalization
    - Streaming large files
    """
    
    # Common delimiters to try
    DELIMITERS = [',', ';', '\t', '|']
    
    # Maximum bytes to read for encoding detection
    ENCODING_SAMPLE_SIZE = 10000
    
    def __init__(
        self,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
        skip_blank_rows: bool = True,
        strip_values: bool = True,
    ):
        """Initialize CSV parser.
        
        Args:
            delimiter: CSV delimiter (auto-detected if None)
            encoding: File encoding (auto-detected if None)
            skip_blank_rows: Whether to skip rows with all empty values
            strip_values: Whether to strip whitespace from values
        """
        self.delimiter = delimiter
        self.encoding = encoding
        self.skip_blank_rows = skip_blank_rows
        self.strip_values = strip_values
        
        # Metadata populated during parsing
        self.detected_encoding: Optional[str] = None
        self.detected_delimiter: Optional[str] = None
        self.headers: List[str] = []
        self.row_count: int = 0
    
    def parse_file(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Parse a CSV file and return list of records.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of dictionaries, one per row
        """
        path = Path(file_path)
        if not path.exists():
            raise CSVParseError(f"File not found: {file_path}")
        
        if not path.suffix.lower() in ('.csv', '.txt', '.tsv'):
            raise CSVParseError(f"Unsupported file type: {path.suffix}")
        
        with open(path, 'rb') as f:
            return self.parse_bytes(f.read(), filename=path.name)
    
    def parse_bytes(self, data: bytes, filename: str = "upload.csv") -> List[Dict[str, Any]]:
        """Parse CSV data from bytes.
        
        Args:
            data: Raw CSV data as bytes
            filename: Original filename for error messages
            
        Returns:
            List of dictionaries, one per row
        """
        # Detect encoding
        encoding = self.encoding or self._detect_encoding(data)
        self.detected_encoding = encoding
        
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError as e:
            raise CSVParseError(f"Failed to decode file with {encoding}: {e}")
        
        return self.parse_string(text, filename=filename)
    
    def parse_string(self, data: str, filename: str = "upload.csv") -> List[Dict[str, Any]]:
        """Parse CSV data from string.
        
        Args:
            data: CSV data as string
            filename: Original filename for error messages
            
        Returns:
            List of dictionaries, one per row
        """
        # Detect delimiter
        delimiter = self.delimiter or self._detect_delimiter(data)
        self.detected_delimiter = delimiter
        
        # Parse CSV
        reader = csv.DictReader(
            io.StringIO(data),
            delimiter=delimiter,
        )
        
        records = []
        self.row_count = 0
        
        try:
            self.headers = reader.fieldnames or []
        except csv.Error as e:
            raise CSVParseError(f"Failed to read CSV headers: {e}")
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            self.row_count += 1
            
            # Process row
            processed = self._process_row(row)
            
            # Skip blank rows if configured
            if self.skip_blank_rows and self._is_blank_row(processed):
                continue
            
            # Add row number for error tracking
            processed['_row_number'] = row_num
            records.append(processed)
        
        return records
    
    def iter_file(self, file_path: Union[str, Path], chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Iterate over a CSV file in chunks for memory efficiency.
        
        Args:
            file_path: Path to the CSV file
            chunk_size: Number of records per chunk
            
        Yields:
            Lists of dictionaries, chunk_size records at a time
        """
        path = Path(file_path)
        if not path.exists():
            raise CSVParseError(f"File not found: {file_path}")
        
        # Read sample for encoding/delimiter detection
        with open(path, 'rb') as f:
            sample = f.read(self.ENCODING_SAMPLE_SIZE)
        
        encoding = self.encoding or self._detect_encoding(sample)
        self.detected_encoding = encoding
        
        with open(path, 'r', encoding=encoding, newline='') as f:
            # Detect delimiter from first few lines
            sample_text = f.read(self.ENCODING_SAMPLE_SIZE)
            delimiter = self.delimiter or self._detect_delimiter(sample_text)
            self.detected_delimiter = delimiter
            
            # Reset and create reader
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            self.headers = reader.fieldnames or []
            
            chunk = []
            row_num = 1  # Header is row 1
            
            for row in reader:
                row_num += 1
                self.row_count += 1
                
                processed = self._process_row(row)
                
                if self.skip_blank_rows and self._is_blank_row(processed):
                    continue
                
                processed['_row_number'] = row_num
                chunk.append(processed)
                
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            
            if chunk:
                yield chunk
    
    def _detect_encoding(self, data: bytes) -> str:
        """Detect file encoding."""
        result = chardet.detect(data[:self.ENCODING_SAMPLE_SIZE])
        encoding = result.get('encoding', 'utf-8')
        
        # Map common encoding variations
        encoding_map = {
            'ascii': 'utf-8',
            'ISO-8859-1': 'latin-1',
            'Windows-1252': 'cp1252',
        }
        
        return encoding_map.get(encoding, encoding) or 'utf-8'
    
    def _detect_delimiter(self, data: str) -> str:
        """Detect CSV delimiter."""
        # Try csv.Sniffer first
        try:
            sample = data[:8192]
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
            return dialect.delimiter
        except csv.Error:
            pass
        
        # Fall back to counting delimiters in first line
        first_line = data.split('\n')[0] if '\n' in data else data
        
        delimiter_counts = {
            d: first_line.count(d) for d in self.DELIMITERS
        }
        
        # Return delimiter with highest count (minimum 1)
        best = max(delimiter_counts, key=delimiter_counts.get)
        if delimiter_counts[best] > 0:
            return best
        
        return ','  # Default to comma
    
    def _process_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single row."""
        processed = {}
        
        for key, value in row.items():
            # Handle None keys (extra columns)
            if key is None:
                continue
            
            # Strip whitespace if configured
            if self.strip_values and isinstance(value, str):
                value = value.strip()
            
            # Convert empty strings to None
            if value == '':
                value = None
            
            processed[key] = value
        
        return processed
    
    def _is_blank_row(self, row: Dict[str, Any]) -> bool:
        """Check if a row has all blank/None values."""
        for key, value in row.items():
            if key.startswith('_'):  # Skip metadata fields
                continue
            if value is not None and value != '':
                return False
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get parsing metadata."""
        return {
            'encoding': self.detected_encoding,
            'delimiter': self.detected_delimiter,
            'headers': self.headers,
            'row_count': self.row_count,
        }
