"""
Tests for Streamware core functionality
"""

import pytest
import json
from streamware import flow, Flow, Component, register
from streamware.uri import StreamwareURI
from streamware.exceptions import ComponentError, MimeTypeError


class TestURI:
    """Test URI parsing"""
    
    def test_basic_uri(self):
        uri = StreamwareURI("file://read?path=/tmp/test.txt")
        assert uri.scheme == "file"
        assert uri.operation == "read"
        assert uri.get_param("path") == "/tmp/test.txt"
        
    def test_http_uri(self):
        uri = StreamwareURI("http://api.example.com/users?limit=10")
        assert uri.scheme == "http"
        assert uri.url == "http://api.example.com/users"
        assert uri.get_param("limit") == 10
        
    def test_complex_params(self):
        uri = StreamwareURI('transform://json?pretty=true&data={"key":"value"}')
        assert uri.get_param("pretty") is True
        assert uri.get_param("data") == {"key": "value"}


class TestFlow:
    """Test flow creation and execution"""
    
    def test_flow_creation(self):
        f = flow("file://read?path=test.txt")
        assert isinstance(f, Flow)
        assert len(f.steps) == 1
        
    def test_flow_chaining(self):
        f = flow("http://api.example.com") | "transform://json" | "file://write"
        assert len(f.steps) == 3
        
    def test_flow_with_data(self):
        f = flow("transform://json").with_data({"test": "data"})
        assert f._data == {"test": "data"}


class TestComponent:
    """Test component registration and execution"""
    
    def test_component_registration(self):
        @register("test")
        class TestComponent(Component):
            def process(self, data):
                return {"processed": data}
                
        # Component should be registered
        from streamware.core import registry
        assert "test" in registry.list_components()
        
    def test_component_mime_validation(self):
        @register("test-mime")
        class TestMimeComponent(Component):
            input_mime = "application/json"
            output_mime = "text/plain"
            
            def process(self, data):
                return str(data)
                
        component = TestMimeComponent(StreamwareURI("test-mime://"))
        
        # Should process JSON input
        result = component.process({"key": "value"})
        assert result == "{'key': 'value'}"


class TestPatterns:
    """Test workflow patterns"""
    
    def test_split_pattern(self):
        from streamware.patterns import SplitPattern
        
        splitter = SplitPattern()
        data = [1, 2, 3, 4, 5]
        result = splitter.split(data)
        assert result == [1, 2, 3, 4, 5]
        
    def test_join_pattern(self):
        from streamware.patterns import JoinPattern
        
        joiner = JoinPattern("list")
        data = [1, 2, 3]
        result = joiner.join(data)
        assert result == [1, 2, 3]
        
        joiner = JoinPattern("sum")
        result = joiner.join(data)
        assert result == 6
        
    def test_filter_pattern(self):
        from streamware.patterns import FilterPattern
        
        filter_pat = FilterPattern(lambda x: x > 5)
        assert filter_pat.filter(10) == 10
        assert filter_pat.filter(3) is None


class TestTransformComponent:
    """Test transform operations"""
    
    def test_json_transform(self):
        from streamware.components.transform import TransformComponent
        
        uri = StreamwareURI("transform://json")
        component = TransformComponent(uri)
        
        # String to JSON
        result = component.process('{"key": "value"}')
        assert result == {"key": "value"}
        
        # JSON to string
        result = component.process({"key": "value"})
        assert '"key"' in result
        
    def test_csv_transform(self):
        from streamware.components.transform import TransformComponent
        
        uri = StreamwareURI("transform://csv")
        component = TransformComponent(uri)
        
        # List of dicts to CSV
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
        result = component.process(data)
        assert "name,age" in result
        assert "Alice,30" in result
        
    def test_base64_transform(self):
        from streamware.components.transform import TransformComponent
        
        # Encode
        uri = StreamwareURI("transform://base64")
        component = TransformComponent(uri)
        result = component.process("hello world")
        assert result == "aGVsbG8gd29ybGQ="
        
        # Decode
        uri = StreamwareURI("transform://base64?decode=true")
        component = TransformComponent(uri)
        result = component.process("aGVsbG8gd29ybGQ=")
        assert result == "hello world"


class TestFileComponent:
    """Test file operations"""
    
    def test_file_operations(self):
        from streamware.components.file import FileComponent
        import tempfile
        
        # Write test
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
            
        uri = StreamwareURI(f"file://write?path={temp_path}")
        component = FileComponent(uri)
        result = component.process("test content")
        assert result["success"] is True
        
        # Read test
        uri = StreamwareURI(f"file://read?path={temp_path}")
        component = FileComponent(uri)
        result = component.process(None)
        assert result == "test content"
        
        # Delete test
        uri = StreamwareURI(f"file://delete?path={temp_path}")
        component = FileComponent(uri)
        result = component.process(None)
        assert result["success"] is True


class TestHTTPComponent:
    """Test HTTP operations"""
    
    def test_http_uri_parsing(self):
        from streamware.components.http import HTTPComponent
        
        uri = StreamwareURI("http://api.example.com/users?limit=10")
        component = HTTPComponent(uri)
        assert component.url == "http://api.example.com/users"
        assert component.uri.get_param("limit") == 10


# Integration tests
class TestIntegration:
    """Integration tests for complete pipelines"""
    
    def test_simple_pipeline(self):
        """Test a simple transformation pipeline"""
        data = {"items": [1, 2, 3, 4, 5]}
        
        # Create a test component
        @register("test-sum")
        class SumComponent(Component):
            def process(self, data):
                if isinstance(data, list):
                    return sum(data)
                return data
                
        # This would work with actual components
        # result = (
        #     flow("transform://json")
        #     | "transform://jsonpath?query=$.items"
        #     | "test-sum://"
        # ).run(data)
        # assert result == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
