"""Unit tests for EnhancedDataTable widget."""

import pytest
from unittest.mock import Mock, patch

from dbt_metrics_manager.widgets.data_table import (
    EnhancedDataTable, 
    ColumnConfig,
    RowSelectedMessage,
    TableDataChangedMessage
)
from dbt_metrics_manager.models.metric import Metric, MetricType


class TestEnhancedDataTable:
    """Unit tests for EnhancedDataTable widget functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return [
            {
                "name": "Total Revenue",
                "short": "rev", 
                "type": "direct",
                "category": "Financial",
                "value": "total_revenue_value",
                "model_name": "customer_rollup"
            },
            {
                "name": "Order Count",
                "short": "ord",
                "type": "direct", 
                "category": "Operations",
                "value": "order_count",
                "model_name": "customer_rollup"
            },
            {
                "name": "Conversion Rate",
                "short": "conv",
                "type": "ratio",
                "category": "Marketing", 
                "numerator": "conversion_numerator",
                "denominator": "conversion_denominator",
                "model_name": "customer_rollup"
            }
        ]
    
    @pytest.fixture
    def column_configs(self):
        """Create column configurations for testing."""
        return [
            ColumnConfig(key="name", label="Name", width=20, sortable=True),
            ColumnConfig(key="short", label="Short", width=10, sortable=True),
            ColumnConfig(key="type", label="Type", width=10, sortable=True),
            ColumnConfig(key="category", label="Category", width=15, sortable=True),
            ColumnConfig(key="model_name", label="Model", width=20, sortable=True)
        ]
    
    @pytest.fixture
    def data_table(self, column_configs):
        """Create EnhancedDataTable widget instance."""
        return EnhancedDataTable(
            columns=column_configs,
            id="test-table",
            selectable=True,
            multi_select=True
        )
    
    def test_data_table_initialization(self, data_table, column_configs):
        """Test EnhancedDataTable widget initialization."""
        assert data_table.id == "test-table"
        assert data_table.selectable == True
        assert data_table.multi_select == True
        assert len(data_table.columns) == 5
        assert data_table.columns[0].key == "name"
    
    def test_update_data(self, data_table, sample_data):
        """Test updating table data."""
        data_table.update_data(sample_data)
        
        assert len(data_table.data) == 3
        assert data_table.data[0]["name"] == "Total Revenue"
        assert data_table.data[1]["short"] == "ord"
    
    def test_add_row(self, data_table, sample_data):
        """Test adding a new row."""
        data_table.update_data(sample_data)
        
        new_row = {
            "name": "New Metric",
            "short": "new",
            "type": "direct",
            "category": "Test",
            "model_name": "test_model"
        }
        
        data_table.add_row(new_row)
        assert len(data_table.data) == 4
        assert data_table.data[3]["name"] == "New Metric"
    
    def test_remove_row(self, data_table, sample_data):
        """Test removing a row."""
        data_table.update_data(sample_data)
        
        data_table.remove_row(1)  # Remove second row
        assert len(data_table.data) == 2
        assert data_table.data[1]["name"] == "Conversion Rate"  # Third row moved to index 1
    
    def test_update_row(self, data_table, sample_data):
        """Test updating a row."""
        data_table.update_data(sample_data)
        
        updated_data = {"name": "Updated Revenue", "short": "upd_rev"}
        data_table.update_row(0, updated_data)
        
        assert data_table.data[0]["name"] == "Updated Revenue"
        assert data_table.data[0]["short"] == "upd_rev"
        # Other fields should remain unchanged
        assert data_table.data[0]["type"] == "direct"
    
    def test_sorting_functionality(self, data_table, sample_data):
        """Test sorting by column."""
        data_table.update_data(sample_data)
        
        # Sort by name (ascending)
        data_table.sort_by_column("name", ascending=True)
        sorted_data = data_table._get_filtered_data()
        
        # Should be sorted alphabetically
        names = [row["name"] for row in sorted_data]
        assert names == sorted(names)
        
        # Sort by name (descending)
        data_table.sort_by_column("name", ascending=False)
        sorted_data = data_table._get_filtered_data()
        
        names = [row["name"] for row in sorted_data]
        assert names == sorted(names, reverse=True)
    
    def test_filtering_functionality(self, data_table, sample_data):
        """Test filtering table data."""
        data_table.update_data(sample_data)
        
        # Filter by text
        data_table.set_filter("revenue")
        filtered_data = data_table._get_filtered_data()
        
        assert len(filtered_data) == 1
        assert filtered_data[0]["name"] == "Total Revenue"
        
        # Filter by category
        data_table.set_filter("Financial")
        filtered_data = data_table._get_filtered_data()
        
        assert len(filtered_data) == 1
        assert filtered_data[0]["category"] == "Financial"
    
    def test_case_insensitive_filtering(self, data_table, sample_data):
        """Test that filtering is case insensitive."""
        data_table.update_data(sample_data)
        
        # Test uppercase filter
        data_table.set_filter("REVENUE")
        filtered_data = data_table._get_filtered_data()
        assert len(filtered_data) == 1
        
        # Test mixed case filter
        data_table.set_filter("Revenue")
        filtered_data = data_table._get_filtered_data()
        assert len(filtered_data) == 1
    
    def test_row_selection(self, data_table, sample_data):
        """Test row selection functionality."""
        data_table.update_data(sample_data)
        
        # Mock post_message method
        with patch.object(data_table, 'post_message') as mock_post:
            data_table.select_row(1)
            
            # Should post RowSelectedMessage
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert isinstance(call_args, RowSelectedMessage)
            assert call_args.row_index == 1
            assert call_args.row_data["name"] == "Order Count"
    
    def test_multi_selection(self, data_table, sample_data):
        """Test multi-row selection."""
        data_table.update_data(sample_data)
        
        data_table.select_row(0)
        data_table.select_row(2, extend_selection=True)
        
        selected_rows = data_table.get_selected_rows()
        assert len(selected_rows) == 2
        assert 0 in selected_rows
        assert 2 in selected_rows
    
    def test_clear_selection(self, data_table, sample_data):
        """Test clearing selection."""
        data_table.update_data(sample_data)
        
        data_table.select_row(0)
        data_table.select_row(1, extend_selection=True)
        assert len(data_table.get_selected_rows()) == 2
        
        data_table.clear_selection()
        assert len(data_table.get_selected_rows()) == 0
    
    def test_export_to_dict(self, data_table, sample_data):
        """Test exporting data to dictionary."""
        data_table.update_data(sample_data)
        
        exported_data = data_table.export_data()
        assert len(exported_data) == 3
        assert exported_data[0]["name"] == "Total Revenue"
        assert exported_data == sample_data
    
    def test_export_selected_rows(self, data_table, sample_data):
        """Test exporting only selected rows."""
        data_table.update_data(sample_data)
        
        data_table.select_row(0)
        data_table.select_row(2, extend_selection=True)
        
        exported_data = data_table.export_selected()
        assert len(exported_data) == 2
        assert exported_data[0]["name"] == "Total Revenue"
        assert exported_data[1]["name"] == "Conversion Rate"
    
    def test_column_width_adjustment(self, data_table):
        """Test column width adjustments."""
        original_width = data_table.columns[0].width
        
        data_table.set_column_width("name", 30)
        assert data_table.columns[0].width == 30
        assert data_table.columns[0].width != original_width
    
    def test_column_visibility(self, data_table):
        """Test hiding/showing columns."""
        data_table.set_column_visible("short", False)
        visible_columns = [col for col in data_table.columns if col.visible]
        
        assert len(visible_columns) == 4  # One column hidden
        assert all(col.key != "short" for col in visible_columns)
        
        # Show column again
        data_table.set_column_visible("short", True)
        visible_columns = [col for col in data_table.columns if col.visible]
        assert len(visible_columns) == 5
    
    def test_empty_data_handling(self, data_table):
        """Test behavior with empty data."""
        data_table.update_data([])
        
        assert len(data_table.data) == 0
        filtered_data = data_table._get_filtered_data()
        assert len(filtered_data) == 0
        
        # Should handle operations gracefully
        data_table.sort_by_column("name")
        data_table.set_filter("test")
        assert len(data_table._get_filtered_data()) == 0
    
    def test_invalid_row_operations(self, data_table, sample_data):
        """Test handling of invalid row operations."""
        data_table.update_data(sample_data)
        
        # Try to remove invalid index
        original_length = len(data_table.data)
        data_table.remove_row(10)  # Invalid index
        assert len(data_table.data) == original_length
        
        # Try to update invalid index
        data_table.update_row(10, {"name": "Invalid"})
        assert data_table.data[0]["name"] == "Total Revenue"  # Unchanged
    
    def test_data_change_notifications(self, data_table, sample_data):
        """Test that data changes trigger notifications."""
        data_table.update_data(sample_data)
        
        with patch.object(data_table, 'post_message') as mock_post:
            data_table.add_row({"name": "New Row"})
            
            # Should post TableDataChangedMessage
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert isinstance(call_args, TableDataChangedMessage)


class TestColumnConfig:
    """Unit tests for ColumnConfig class."""
    
    def test_column_config_creation(self):
        """Test creating ColumnConfig."""
        config = ColumnConfig(
            key="test_key",
            label="Test Label",
            width=15,
            sortable=True,
            formatter=str.upper
        )
        
        assert config.key == "test_key"
        assert config.label == "Test Label"
        assert config.width == 15
        assert config.sortable == True
        assert config.formatter == str.upper
        assert config.visible == True  # Default
    
    def test_column_config_defaults(self):
        """Test ColumnConfig default values."""
        config = ColumnConfig(key="test", label="Test")
        
        assert config.width == 10  # Default width
        assert config.sortable == False  # Default sortable
        assert config.formatter is None  # Default formatter
        assert config.visible == True  # Default visible
        assert config.align == "left"  # Default alignment
    
    def test_column_formatter_application(self):
        """Test applying column formatter."""
        config = ColumnConfig(
            key="test",
            label="Test", 
            formatter=lambda x: x.upper()
        )
        
        result = config.format_value("hello")
        assert result == "HELLO"
        
        # Test with None formatter
        config_no_formatter = ColumnConfig(key="test", label="Test")
        result = config_no_formatter.format_value("hello")
        assert result == "hello"


class TestTableMessages:
    """Unit tests for table message classes."""
    
    def test_row_selected_message(self):
        """Test RowSelectedMessage creation."""
        row_data = {"name": "Test", "value": 123}
        message = RowSelectedMessage(1, row_data)
        
        assert message.row_index == 1
        assert message.row_data == row_data
        assert message.can_bubble
    
    def test_table_data_changed_message(self):
        """Test TableDataChangedMessage creation."""
        message = TableDataChangedMessage("add", 2)
        
        assert message.change_type == "add"
        assert message.row_index == 2
        assert message.can_bubble