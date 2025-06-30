"""Enhanced DataTable widget for displaying and managing tabular data."""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass

from textual.widgets import DataTable
from textual.message import Message
from textual.reactive import reactive
from textual import events


@dataclass
class ColumnConfig:
    """Configuration for a table column."""
    key: str
    label: str
    width: Optional[int] = None
    sortable: bool = True
    formatter: Optional[Callable[[Any], str]] = None
    alignment: str = "left"  # left, center, right


@dataclass
class RowData:
    """Data for a table row with metadata."""
    id: str
    data: Dict[str, Any]
    selectable: bool = True
    css_classes: Optional[List[str]] = None


class EnhancedDataTable(DataTable):
    """Enhanced DataTable with sorting, filtering, and selection capabilities."""
    
    # Reactive attributes
    show_row_numbers: reactive[bool] = reactive(True)
    allow_multiple_selection: reactive[bool] = reactive(True)
    show_header: reactive[bool] = reactive(True)
    
    def __init__(
        self,
        columns: List[ColumnConfig],
        data: Optional[List[RowData]] = None,
        sortable: bool = True,
        filterable: bool = True,
        selectable: bool = True,
        **kwargs
    ):
        """Initialize the enhanced data table.
        
        Args:
            columns: Column configurations
            data: Initial row data
            sortable: Enable column sorting
            filterable: Enable row filtering
            selectable: Enable row selection
            **kwargs: Additional DataTable arguments
        """
        super().__init__(**kwargs)
        
        self.column_configs = {col.key: col for col in columns}
        self.columns_order = [col.key for col in columns]
        self.row_data: Dict[str, RowData] = {}
        self.selected_rows: set = set()
        self.sort_column: Optional[str] = None
        self.sort_ascending: bool = True
        self.filter_text: str = ""
        
        self.sortable = sortable
        self.filterable = filterable
        self.selectable = selectable
        
        # Setup table
        self._setup_columns()
        
        if data:
            self.set_data(data)
    
    class RowSelected(Message):
        """Message sent when a row is selected."""
        
        def __init__(self, row_id: str, row_data: RowData) -> None:
            self.row_id = row_id
            self.row_data = row_data
            super().__init__()
    
    class RowDeselected(Message):
        """Message sent when a row is deselected."""
        
        def __init__(self, row_id: str) -> None:
            self.row_id = row_id
            super().__init__()
    
    class SelectionChanged(Message):
        """Message sent when selection changes."""
        
        def __init__(self, selected_rows: List[str]) -> None:
            self.selected_rows = selected_rows
            super().__init__()
    
    class CellClicked(Message):
        """Message sent when a cell is clicked."""
        
        def __init__(self, row_id: str, column_key: str, value: Any) -> None:
            self.row_id = row_id
            self.column_key = column_key
            self.value = value
            super().__init__()
    
    def _setup_columns(self) -> None:
        """Setup table columns based on configuration."""
        column_keys = []
        
        # Add row selection column if selectable
        if self.selectable:
            column_keys.append("_select")
            self.add_column("", key="_select", width=3)
        
        # Add configured columns
        for col_config in self.column_configs.values():
            column_keys.append(col_config.key)
            self.add_column(
                col_config.label,
                key=col_config.key,
                width=col_config.width
            )
        
        self.columns_order = column_keys
    
    def set_data(self, data: List[RowData]) -> None:
        """Set the table data.
        
        Args:
            data: List of row data objects
        """
        # Store row data
        self.row_data = {row.id: row for row in data}
        
        # Clear existing rows
        self.clear()
        
        # Add rows
        self._refresh_display()
    
    def add_row_data(self, row: RowData) -> None:
        """Add a single row to the table.
        
        Args:
            row: Row data to add
        """
        self.row_data[row.id] = row
        self._add_table_row(row)
    
    def update_row_data(self, row_id: str, data: Dict[str, Any]) -> None:
        """Update data for an existing row.
        
        Args:
            row_id: ID of row to update
            data: New data for the row
        """
        if row_id in self.row_data:
            self.row_data[row_id].data.update(data)
            self._refresh_display()
    
    def remove_row_data(self, row_id: str) -> None:
        """Remove a row from the table.
        
        Args:
            row_id: ID of row to remove
        """
        if row_id in self.row_data:
            del self.row_data[row_id]
            self.selected_rows.discard(row_id)
            self._refresh_display()
    
    def get_row_data(self, row_id: str) -> Optional[RowData]:
        """Get data for a specific row.
        
        Args:
            row_id: ID of row to get
            
        Returns:
            Row data if found, None otherwise
        """
        return self.row_data.get(row_id)
    
    def get_selected_rows(self) -> List[RowData]:
        """Get data for all selected rows.
        
        Returns:
            List of selected row data
        """
        return [self.row_data[row_id] for row_id in self.selected_rows 
                if row_id in self.row_data]
    
    def select_row(self, row_id: str) -> None:
        """Select a specific row.
        
        Args:
            row_id: ID of row to select
        """
        if row_id in self.row_data and self.row_data[row_id].selectable:
            if not self.allow_multiple_selection:
                self.selected_rows.clear()
            
            self.selected_rows.add(row_id)
            self._refresh_display()
            self.post_message(self.RowSelected(row_id, self.row_data[row_id]))
            self.post_message(self.SelectionChanged(list(self.selected_rows)))
    
    def deselect_row(self, row_id: str) -> None:
        """Deselect a specific row.
        
        Args:
            row_id: ID of row to deselect
        """
        if row_id in self.selected_rows:
            self.selected_rows.remove(row_id)
            self._refresh_display()
            self.post_message(self.RowDeselected(row_id))
            self.post_message(self.SelectionChanged(list(self.selected_rows)))
    
    def toggle_row_selection(self, row_id: str) -> None:
        """Toggle selection of a specific row.
        
        Args:
            row_id: ID of row to toggle
        """
        if row_id in self.selected_rows:
            self.deselect_row(row_id)
        else:
            self.select_row(row_id)
    
    def select_all_rows(self) -> None:
        """Select all selectable rows."""
        if self.allow_multiple_selection:
            for row_id, row in self.row_data.items():
                if row.selectable:
                    self.selected_rows.add(row_id)
            self._refresh_display()
            self.post_message(self.SelectionChanged(list(self.selected_rows)))
    
    def clear_selection(self) -> None:
        """Clear all row selections."""
        self.selected_rows.clear()
        self._refresh_display()
        self.post_message(self.SelectionChanged([]))
    
    def sort_by_column(self, column_key: str, ascending: bool = True) -> None:
        """Sort table by a specific column.
        
        Args:
            column_key: Key of column to sort by
            ascending: Sort direction
        """
        if column_key not in self.column_configs:
            return
        
        self.sort_column = column_key
        self.sort_ascending = ascending
        self._refresh_display()
    
    def filter_rows(self, filter_text: str) -> None:
        """Filter rows based on text search.
        
        Args:
            filter_text: Text to search for in row data
        """
        self.filter_text = filter_text.lower()
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh the table display with current data."""
        # Clear existing rows
        self.clear()
        
        # Get filtered and sorted rows
        display_rows = self._get_filtered_sorted_rows()
        
        # Add rows to table
        for row in display_rows:
            self._add_table_row(row)
    
    def _get_filtered_sorted_rows(self) -> List[RowData]:
        """Get rows after applying filters and sorting.
        
        Returns:
            List of filtered and sorted rows
        """
        rows = list(self.row_data.values())
        
        # Apply filter
        if self.filterable and self.filter_text:
            filtered_rows = []
            for row in rows:
                if self._row_matches_filter(row):
                    filtered_rows.append(row)
            rows = filtered_rows
        
        # Apply sort
        if self.sortable and self.sort_column:
            rows.sort(
                key=lambda r: self._get_sort_value(r, self.sort_column),
                reverse=not self.sort_ascending
            )
        
        return rows
    
    def _row_matches_filter(self, row: RowData) -> bool:
        """Check if a row matches the current filter.
        
        Args:
            row: Row to check
            
        Returns:
            True if row matches filter
        """
        if not self.filter_text:
            return True
        
        # Search in all string values
        for value in row.data.values():
            if isinstance(value, str) and self.filter_text in value.lower():
                return True
        
        return False
    
    def _get_sort_value(self, row: RowData, column_key: str) -> Any:
        """Get the sort value for a row and column.
        
        Args:
            row: Row data
            column_key: Column to get value for
            
        Returns:
            Sort value
        """
        value = row.data.get(column_key, "")
        
        # Handle None values
        if value is None:
            return ""
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            return value
        
        # Handle string values
        return str(value).lower()
    
    def _add_table_row(self, row: RowData) -> None:
        """Add a row to the table display.
        
        Args:
            row: Row data to add
        """
        row_values = []
        
        # Add selection checkbox if selectable
        if self.selectable:
            checkbox = "☑" if row.id in self.selected_rows else "☐"
            row_values.append(checkbox)
        
        # Add data columns
        for col_key in self.columns_order:
            if col_key == "_select":
                continue
            
            value = row.data.get(col_key, "")
            
            # Apply formatter if available
            col_config = self.column_configs.get(col_key)
            if col_config and col_config.formatter:
                value = col_config.formatter(value)
            
            row_values.append(str(value))
        
        # Add row to table
        self.add_row(*row_values, key=row.id)
    
    def on_data_table_cell_selected(self, event) -> None:
        """Handle cell selection."""
        if not self.selectable:
            return
        
        # Get row ID from event
        row_key = event.cell_key.row_key
        column_key = event.cell_key.column_key
        
        if row_key in self.row_data:
            # If clicking selection column, toggle selection
            if column_key == "_select":
                self.toggle_row_selection(row_key)
            else:
                # Post cell clicked message
                value = self.row_data[row_key].data.get(column_key.value, "")
                self.post_message(self.CellClicked(row_key, column_key.value, value))
    
    def on_data_table_header_selected(self, event) -> None:
        """Handle header selection for sorting."""
        if not self.sortable:
            return
        
        column_key = event.column_key.value
        
        if column_key == "_select":
            # Toggle select all
            if len(self.selected_rows) == len([r for r in self.row_data.values() if r.selectable]):
                self.clear_selection()
            else:
                self.select_all_rows()
        elif column_key in self.column_configs:
            # Sort by column
            if self.sort_column == column_key:
                # Toggle sort direction
                self.sort_by_column(column_key, not self.sort_ascending)
            else:
                # Sort by new column
                self.sort_by_column(column_key, True)
    
    def get_column_config(self, column_key: str) -> Optional[ColumnConfig]:
        """Get configuration for a specific column.
        
        Args:
            column_key: Key of column to get config for
            
        Returns:
            Column configuration if found
        """
        return self.column_configs.get(column_key)
    
    def update_column_config(self, column_key: str, **kwargs) -> None:
        """Update configuration for a column.
        
        Args:
            column_key: Key of column to update
            **kwargs: Configuration parameters to update
        """
        if column_key in self.column_configs:
            config = self.column_configs[column_key]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def export_data(self, format: str = "dict") -> Union[List[Dict], str]:
        """Export table data in specified format.
        
        Args:
            format: Export format ('dict', 'csv', 'json')
            
        Returns:
            Exported data
        """
        rows = self._get_filtered_sorted_rows()
        
        if format == "dict":
            return [row.data for row in rows]
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=self.columns_order[1:])  # Skip select column
            writer.writeheader()
            for row in rows:
                writer.writerow(row.data)
            return output.getvalue()
        elif format == "json":
            import json
            return json.dumps([row.data for row in rows], indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the table.
        
        Returns:
            Dictionary with table statistics
        """
        return {
            "total_rows": len(self.row_data),
            "displayed_rows": len(self._get_filtered_sorted_rows()),
            "selected_rows": len(self.selected_rows),
            "columns": len(self.column_configs),
            "sort_column": self.sort_column,
            "sort_ascending": self.sort_ascending,
            "filter_active": bool(self.filter_text)
        }