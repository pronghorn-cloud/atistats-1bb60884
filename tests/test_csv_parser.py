"""Unit tests for CSV parser service."""

import pytest
from src.services.ingestion.csv_parser import CSVParser, CSVParseError


class TestCSVParser:
    """Test cases for CSVParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create a CSVParser instance."""
        return CSVParser()
    
    def test_parse_simple_csv_string(self, parser):
        """Test parsing a simple CSV string."""
        csv_data = """name,value,count
alice,100,5
bob,200,10
charlie,300,15"""
        result = parser.parse_string(csv_data)
        
        assert len(result) == 3
        assert result[0]['name'] == 'alice'
        assert result[0]['value'] == '100'
        assert result[0]['count'] == '5'
        assert result[1]['name'] == 'bob'
        assert result[2]['name'] == 'charlie'
    
    def test_parse_csv_with_row_numbers(self, parser):
        """Test that parsed records include row numbers."""
        csv_data = """col1,col2
a,b
c,d"""
        result = parser.parse_string(csv_data)
        
        assert result[0]['_row_number'] == 2  # Row 1 is header
        assert result[1]['_row_number'] == 3
    
    def test_skip_blank_rows(self, parser):
        """Test that blank rows are skipped by default."""
        csv_data = """name,value
alice,100
,,
bob,200"""
        result = parser.parse_string(csv_data)
        
        assert len(result) == 2
        assert result[0]['name'] == 'alice'
        assert result[1]['name'] == 'bob'
    
    def test_include_blank_rows_when_configured(self):
        """Test that blank rows can be included."""
        parser = CSVParser(skip_blank_rows=False)
        csv_data = """name,value
alice,100
,
bob,200"""
        result = parser.parse_string(csv_data)
        
        # Blank row should be included
        assert len(result) == 3
    
    def test_strip_whitespace(self, parser):
        """Test that values are stripped of whitespace."""
        csv_data = """name,value
  alice  ,  100  
 bob , 200"""
        result = parser.parse_string(csv_data)
        
        assert result[0]['name'] == 'alice'
        assert result[0]['value'] == '100'
        assert result[1]['name'] == 'bob'
    
    def test_no_strip_when_disabled(self):
        """Test that stripping can be disabled."""
        parser = CSVParser(strip_values=False)
        csv_data = """name,value
  alice  ,  100  """
        result = parser.parse_string(csv_data)
        
        assert result[0]['name'] == '  alice  '
        assert result[0]['value'] == '  100  '
    
    def test_empty_values_converted_to_none(self, parser):
        """Test that empty string values become None."""
        csv_data = """name,value,extra
alice,100,
bob,,note"""
        result = parser.parse_string(csv_data)
        
        assert result[0]['extra'] is None
        assert result[1]['value'] is None
        assert result[1]['extra'] == 'note'
    
    def test_detect_comma_delimiter(self, parser):
        """Test auto-detection of comma delimiter."""
        csv_data = "name,value\nalice,100"
        parser.parse_string(csv_data)
        
        assert parser.detected_delimiter == ','
    
    def test_detect_semicolon_delimiter(self):
        """Test auto-detection of semicolon delimiter."""
        parser = CSVParser()
        csv_data = "name;value\nalice;100"
        parser.parse_string(csv_data)
        
        assert parser.detected_delimiter == ';'
    
    def test_detect_tab_delimiter(self):
        """Test auto-detection of tab delimiter."""
        parser = CSVParser()
        csv_data = "name\tvalue\nalice\t100"
        parser.parse_string(csv_data)
        
        assert parser.detected_delimiter == '\t'
    
    def test_explicit_delimiter_override(self):
        """Test that explicit delimiter overrides auto-detection."""
        parser = CSVParser(delimiter=';')
        csv_data = "name;value\nalice;100"
        result = parser.parse_string(csv_data)
        
        assert parser.detected_delimiter == ';'
        assert result[0]['name'] == 'alice'
    
    def test_get_headers(self, parser):
        """Test that headers are captured."""
        csv_data = """first_name,last_name,email
john,doe,john@example.com"""
        parser.parse_string(csv_data)
        
        assert parser.headers == ['first_name', 'last_name', 'email']
    
    def test_get_row_count(self, parser):
        """Test that row count is tracked."""
        csv_data = """col1,col2
a,b
c,d
e,f"""
        parser.parse_string(csv_data)
        
        assert parser.row_count == 3
    
    def test_get_metadata(self, parser):
        """Test metadata retrieval."""
        csv_data = "name,value\nalice,100\nbob,200"
        parser.parse_string(csv_data)
        metadata = parser.get_metadata()
        
        assert 'encoding' in metadata
        assert metadata['delimiter'] == ','
        assert metadata['headers'] == ['name', 'value']
        assert metadata['row_count'] == 2
    
    def test_parse_bytes_utf8(self, parser):
        """Test parsing UTF-8 encoded bytes."""
        csv_data = "name,value\nalice,100\nbob,200"
        result = parser.parse_bytes(csv_data.encode('utf-8'))
        
        assert len(result) == 2
        assert result[0]['name'] == 'alice'
    
    def test_parse_bytes_with_unicode(self, parser):
        """Test parsing bytes with unicode characters."""
        csv_data = "name,city\nMarie,Montréal\nJosé,São Paulo"
        result = parser.parse_bytes(csv_data.encode('utf-8'))
        
        assert result[0]['city'] == 'Montréal'
        assert result[1]['city'] == 'São Paulo'
    
    def test_parse_bytes_latin1(self):
        """Test parsing Latin-1 encoded bytes."""
        parser = CSVParser(encoding='latin-1')
        csv_data = "name,city\nMarie,Montréal"
        result = parser.parse_bytes(csv_data.encode('latin-1'))
        
        assert result[0]['city'] == 'Montréal'
    
    def test_quoted_values(self, parser):
        """Test handling of quoted values with commas."""
        csv_data = '''name,description
alice,"Hello, World"
bob,"Value with ""quotes"""
'''
        result = parser.parse_string(csv_data)
        
        assert result[0]['description'] == 'Hello, World'
        assert result[1]['description'] == 'Value with "quotes"'
    
    def test_multiline_values(self, parser):
        """Test handling of multiline quoted values."""
        csv_data = '''name,description
alice,"Line 1
Line 2"
bob,simple
'''
        result = parser.parse_string(csv_data)
        
        assert 'Line 1\nLine 2' in result[0]['description']
        assert result[1]['description'] == 'simple'


class TestCSVParserErrors:
    """Test error handling in CSVParser."""
    
    def test_file_not_found_error(self):
        """Test that FileNotFoundError is raised for missing files."""
        parser = CSVParser()
        
        with pytest.raises(CSVParseError) as exc_info:
            parser.parse_file('/nonexistent/path/file.csv')
        
        assert 'not found' in str(exc_info.value).lower()
    
    def test_unsupported_file_type(self, tmp_path):
        """Test that unsupported file types are rejected."""
        parser = CSVParser()
        test_file = tmp_path / "test.xlsx"
        test_file.write_text("dummy")
        
        with pytest.raises(CSVParseError) as exc_info:
            parser.parse_file(test_file)
        
        assert 'unsupported' in str(exc_info.value).lower()
    
    def test_invalid_encoding_error(self):
        """Test handling of decode errors."""
        parser = CSVParser(encoding='ascii')
        # UTF-8 encoded data with non-ASCII characters
        data = "name,city\nMarie,Montréal".encode('utf-8')
        
        with pytest.raises(CSVParseError) as exc_info:
            parser.parse_bytes(data)
        
        assert 'decode' in str(exc_info.value).lower() or 'Failed' in str(exc_info.value)
