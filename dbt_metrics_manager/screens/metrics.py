"""Metrics Library screen for managing existing metrics."""

from typing import List, Optional, Dict, Set
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, Select, TextArea, 
    Checkbox, Label, Tabs, TabPane
)
from textual.binding import Binding
from textual.message import Message

from ..widgets.data_table import EnhancedDataTable, ColumnConfig, RowData
from ..state import AppState
from ..models.metric import Metric, MetricType
from ..services.seed_manager import SeedManager


class MetricFormModal(ModalScreen):
    """Modal screen for editing metric definitions."""
    
    def __init__(self, metric: Optional[Metric] = None, models: List[str] = None):
        """Initialize the metric form modal.
        
        Args:
            metric: Existing metric to edit (None for new metric)
            models: Available model names for selection
        """
        super().__init__()
        self.metric = metric
        self.models = models or []
        self.is_edit_mode = metric is not None
    
    class MetricSaved(Message):
        """Message sent when metric is saved."""
        
        def __init__(self, metric: Metric, is_new: bool) -> None:
            self.metric = metric
            self.is_new = is_new
            super().__init__()
    
    class FormCancelled(Message):
        """Message sent when form is cancelled."""
        
        def __init__(self) -> None:
            super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create the metric form layout."""
        title = "Edit Metric" if self.is_edit_mode else "Create New Metric"
        
        yield Container(
            Container(
                Static(title, classes="modal-title"),
                self._create_form_content(),
                self._create_form_buttons(),
                classes="metric-form-modal"
            ),
            classes="modal-container"
        )
    
    def _create_form_content(self) -> Container:
        """Create the form content."""
        # Basic information
        basic_section = Container(
            Label("Basic Information", classes="section-label"),
            Horizontal(
                Container(
                    Label("Name:"),
                    Input(
                        value=self.metric.name if self.metric else "",
                        placeholder="Metric name",
                        id="name-input"
                    ),
                    classes="form-field"
                ),
                Container(
                    Label("Short Code:"),
                    Input(
                        value=self.metric.short if self.metric else "",
                        placeholder="Short identifier",
                        id="short-input"
                    ),
                    classes="form-field"
                ),
                classes="form-row"
            ),
            Horizontal(
                Container(
                    Label("Type:"),
                    Select(
                        [(t.value.title(), t.value) for t in MetricType],
                        value=self.metric.type.value if self.metric else MetricType.DIRECT.value,
                        id="type-select"
                    ),
                    classes="form-field"
                ),
                Container(
                    Label("Category:"),
                    Input(
                        value=self.metric.category if self.metric else "",
                        placeholder="Category (e.g., Financial, Marketing)",
                        id="category-input"
                    ),
                    classes="form-field"
                ),
                classes="form-row"
            ),
            classes="form-section"
        )
        
        # Type-specific fields
        type_section = Container(
            Label("Type-Specific Configuration", classes="section-label"),
            self._create_type_fields(),
            classes="form-section",
            id="type-section"
        )
        
        # Additional information
        additional_section = Container(
            Label("Additional Information", classes="section-label"),
            Container(
                Label("Model Name:"),
                Select(
                    [("Select a model...", "")] + [(m, m) for m in self.models],
                    value=self.metric.model_name if self.metric else "",
                    id="model-select"
                ),
                classes="form-field"
            ),
            Container(
                Label("Description:"),
                TextArea(
                    text=self.metric.description if self.metric else "",
                    id="description-input"
                ),
                classes="form-field"
            ),
            Horizontal(
                Container(
                    Label("Owner:"),
                    Input(
                        value=self.metric.owner if self.metric else "",
                        placeholder="Team or person responsible",
                        id="owner-input"
                    ),
                    classes="form-field"
                ),
                Container(
                    Label("Tags:"),
                    Input(
                        value=", ".join(self.metric.tags) if self.metric and self.metric.tags else "",
                        placeholder="tag1, tag2, tag3",
                        id="tags-input"
                    ),
                    classes="form-field"
                ),
                classes="form-row"
            ),
            classes="form-section"
        )
        
        return ScrollableContainer(
            basic_section,
            type_section,
            additional_section,
            classes="form-content"
        )
    
    def _create_type_fields(self) -> Container:
        """Create type-specific form fields."""
        # Start with direct type fields
        return Container(
            # Direct type fields
            Container(
                Label("Value Column:"),
                Input(
                    value=self.metric.value if self.metric else "",
                    placeholder="Column name for direct metrics",
                    id="value-input"
                ),
                classes="form-field direct-field"
            ),
            
            # Ratio type fields
            Horizontal(
                Container(
                    Label("Numerator:"),
                    Input(
                        value=self.metric.numerator if self.metric else "",
                        placeholder="Numerator column",
                        id="numerator-input"
                    ),
                    classes="form-field ratio-field"
                ),
                Container(
                    Label("Denominator:"),
                    Input(
                        value=self.metric.denominator if self.metric else "",
                        placeholder="Denominator column",
                        id="denominator-input"
                    ),
                    classes="form-field ratio-field"
                ),
                classes="form-row ratio-field"
            ),
            
            # Custom type fields
            Container(
                Label("SQL Expression:"),
                TextArea(
                    text=self.metric.sql if self.metric else "",
                    id="sql-input"
                ),
                classes="form-field custom-field"
            ),
            
            id="type-fields"
        )
    
    def _create_form_buttons(self) -> Container:
        """Create form action buttons."""
        return Container(
            Horizontal(
                Button("Cancel", id="cancel-btn", classes="cancel-button"),
                Button("Save", id="save-btn", classes="save-button"),
                classes="form-buttons"
            ),
            classes="button-container"
        )
    
    def on_mount(self) -> None:
        """Initialize form when mounted."""
        self._update_type_fields()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select field changes."""
        if event.select.id == "type-select":
            self._update_type_fields()
    
    def _update_type_fields(self) -> None:
        """Update visibility of type-specific fields based on selected type."""
        type_select = self.query_one("#type-select")
        selected_type = type_select.value
        
        # Hide all type fields first
        for field_type in ["direct-field", "ratio-field", "custom-field"]:
            for widget in self.query(f".{field_type}"):
                widget.display = False
        
        # Show relevant fields
        if selected_type == "direct":
            for widget in self.query(".direct-field"):
                widget.display = True
        elif selected_type == "ratio":
            for widget in self.query(".ratio-field"):
                widget.display = True
        elif selected_type == "custom":
            for widget in self.query(".custom-field"):
                widget.display = True
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._save_metric()
        elif event.button.id == "cancel-btn":
            self._cancel_form()
    
    def _save_metric(self) -> None:
        """Save the metric with current form values."""
        try:
            # Collect form values
            metric_data = self._collect_form_data()
            
            # Create or update metric
            if self.is_edit_mode:
                # Update existing metric
                for key, value in metric_data.items():
                    setattr(self.metric, key, value)
                metric = self.metric
            else:
                # Create new metric
                metric = Metric(**metric_data)
            
            # Validate metric
            errors = metric.validate()
            if errors:
                self._show_validation_errors(errors)
                return
            
            # Send success message
            self.post_message(self.MetricSaved(metric, not self.is_edit_mode))
            self.dismiss()
            
        except Exception as e:
            self._show_error(f"Failed to save metric: {e}")
    
    def _collect_form_data(self) -> Dict:
        """Collect all form field values."""
        # Basic fields
        name_input = self.query_one("#name-input")
        short_input = self.query_one("#short-input")
        type_select = self.query_one("#type-select")
        category_input = self.query_one("#category-input")
        
        # Type-specific fields
        value_input = self.query_one("#value-input")
        numerator_input = self.query_one("#numerator-input")
        denominator_input = self.query_one("#denominator-input")
        sql_input = self.query_one("#sql-input")
        
        # Additional fields
        model_select = self.query_one("#model-select")
        description_input = self.query_one("#description-input")
        owner_input = self.query_one("#owner-input")
        tags_input = self.query_one("#tags-input")
        
        # Parse tags
        tags_text = tags_input.value.strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()] if tags_text else None
        
        # Build metric data
        metric_data = {
            "name": name_input.value.strip(),
            "short": short_input.value.strip(),
            "type": MetricType(type_select.value),
            "category": category_input.value.strip() or None,
            "model_name": model_select.value or None,
            "description": description_input.text.strip() or None,
            "owner": owner_input.value.strip() or None,
            "tags": tags
        }
        
        # Add type-specific fields
        if type_select.value == "direct":
            metric_data["value"] = value_input.value.strip() or None
        elif type_select.value == "ratio":
            metric_data["numerator"] = numerator_input.value.strip() or None
            metric_data["denominator"] = denominator_input.value.strip() or None
        elif type_select.value == "custom":
            metric_data["sql"] = sql_input.text.strip() or None
        
        return metric_data
    
    def _cancel_form(self) -> None:
        """Cancel the form."""
        self.post_message(self.FormCancelled())
        self.dismiss()
    
    def _show_validation_errors(self, errors: List[str]) -> None:
        """Show validation errors to user."""
        # Could show in a notification or error container
        pass
    
    def _show_error(self, message: str) -> None:
        """Show error message to user."""
        # Could show in a notification
        pass


class MetricsLibraryScreen(Screen):
    """Screen for managing existing metrics library."""
    
    BINDINGS = [
        Binding("f1", "show_dashboard", "Dashboard"),
        Binding("f2", "show_models", "Models"),
        Binding("f4", "show_discovery", "Discovery"),
        Binding("f5", "show_settings", "Settings"),
        Binding("n", "new_metric", "New"),
        Binding("e", "edit_metric", "Edit"),
        Binding("d", "delete_metric", "Delete"),
        Binding("ctrl+s", "save_to_file", "Save"),
        Binding("ctrl+o", "load_from_file", "Load"),
        Binding("ctrl+f", "filter_metrics", "Filter"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self, app_state: AppState):
        """Initialize the metrics library screen.
        
        Args:
            app_state: Global application state
        """
        super().__init__()
        self.app_state = app_state
        self.seed_manager = SeedManager()
        
        # Screen state
        self.metrics: List[Metric] = []
        self.filtered_metrics: List[Metric] = []
        self.selected_metric_ids: Set[str] = set()
        self.current_seed_file: Optional[Path] = None
        self.filter_text: str = ""
        self.filter_type: Optional[str] = None
        self.filter_category: Optional[str] = None
        
        # UI components
        self.metrics_table: Optional[EnhancedDataTable] = None
        self.tabs: Optional[Tabs] = None
    
    class MetricUpdated(Message):
        """Message sent when a metric is updated."""
        
        def __init__(self, metric: Metric) -> None:
            self.metric = metric
            super().__init__()
    
    class MetricsLoaded(Message):
        """Message sent when metrics are loaded from file."""
        
        def __init__(self, count: int, file_path: str) -> None:
            self.count = count
            self.file_path = file_path
            super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create the metrics library layout."""
        yield Header()
        
        if not self.app_state.project_loaded:
            yield Container(
                Static(
                    "No project loaded. Please load a project from the Settings screen (F5).",
                    classes="error-message"
                ),
                classes="center-container"
            )
        else:
            yield Container(
                self._create_library_content(),
                classes="metrics-library-container"
            )
        
        yield Footer()
    
    def _create_library_content(self) -> Container:
        """Create the main library content."""
        return Container(
            self._create_header_section(),
            self._create_tabs_section(),
            classes="library-content"
        )
    
    def _create_header_section(self) -> Container:
        """Create header with project info and controls."""
        return Container(
            Horizontal(
                Container(
                    Static(f"Project: {self.app_state.project_name}", classes="project-info"),
                    Static("", id="metrics-count", classes="metrics-count"),
                    classes="header-left"
                ),
                Container(
                    Horizontal(
                        Input(placeholder="Filter metrics...", id="filter-input", classes="filter-input"),
                        Select(
                            [("All Types", ""), ("Direct", "direct"), ("Ratio", "ratio"), ("Custom", "custom")],
                            id="type-filter",
                            classes="type-filter"
                        ),
                        Button("Load", id="load-btn", classes="action-button"),
                        Button("Save", id="save-btn", classes="action-button"),
                        Button("New", id="new-btn", classes="primary-button"),
                        classes="header-controls"
                    ),
                    classes="header-right"
                ),
                classes="library-header"
            ),
            classes="header-section"
        )
    
    def _create_tabs_section(self) -> Container:
        """Create tabs for different views."""
        self.tabs = Tabs(
            "All Metrics",
            "By Category",
            "By Model",
            id="metrics-tabs"
        )
        
        return Container(
            self.tabs,
            Container(
                # Tab 1: All Metrics
                TabPane("All Metrics", id="all-tab"),
                
                # Tab 2: By Category
                TabPane("By Category", id="category-tab"),
                
                # Tab 3: By Model
                TabPane("By Model", id="model-tab"),
                
                classes="tab-content"
            ),
            classes="tabs-section"
        )
    
    def on_mount(self) -> None:
        """Initialize screen when mounted."""
        self._setup_all_metrics_tab()
        self._load_metrics_from_project()
    
    def _setup_all_metrics_tab(self) -> None:
        """Setup the all metrics tab with data table."""
        all_tab = self.query_one("#all-tab")
        
        # Create metrics table
        columns = [
            ColumnConfig("name", "Name", width=25),
            ColumnConfig("short", "Short", width=10),
            ColumnConfig("type", "Type", width=10),
            ColumnConfig("category", "Category", width=15),
            ColumnConfig("model_name", "Model", width=20),
            ColumnConfig("owner", "Owner", width=15),
            ColumnConfig("description", "Description", width=30)
        ]
        
        self.metrics_table = EnhancedDataTable(
            columns=columns,
            sortable=True,
            filterable=True,
            selectable=True,
            id="metrics-table",
            classes="metrics-table"
        )
        
        all_tab.mount(
            Container(
                self.metrics_table,
                self._create_table_controls(),
                classes="all-metrics-content"
            )
        )
    
    def _create_table_controls(self) -> Container:
        """Create controls for the metrics table."""
        return Container(
            Horizontal(
                Static("", id="selection-info", classes="selection-info"),
                Container(
                    Button("Edit", id="edit-btn", classes="action-button", disabled=True),
                    Button("Duplicate", id="duplicate-btn", classes="action-button", disabled=True),
                    Button("Delete", id="delete-btn", classes="danger-button", disabled=True),
                    classes="table-actions"
                ),
                classes="table-controls"
            ),
            classes="controls-section"
        )
    
    def _load_metrics_from_project(self) -> None:
        """Load existing metrics from project seed files."""
        try:
            # Find seed files in project
            seed_files = self.seed_manager.find_seed_files(Path(self.app_state.project_path))
            
            if seed_files:
                # Load from first found seed file
                self.current_seed_file = seed_files[0]
                self.metrics = self.seed_manager.read_seed_file(self.current_seed_file)
                self._update_metrics_display()
                
                self.post_message(self.MetricsLoaded(len(self.metrics), str(self.current_seed_file)))
            else:
                # No seed files found
                self.metrics = []
                self._update_metrics_display()
                
        except Exception as e:
            self._show_error(f"Failed to load metrics: {e}")
    
    def _update_metrics_display(self) -> None:
        """Update the metrics display with current data."""
        # Apply filters
        self._apply_filters()
        
        # Update table
        if self.metrics_table:
            row_data = []
            for i, metric in enumerate(self.filtered_metrics):
                row_data.append(RowData(
                    id=f"metric_{i}",
                    data={
                        "name": metric.name,
                        "short": metric.short,
                        "type": metric.type.value,
                        "category": metric.category or "",
                        "model_name": metric.model_name or "",
                        "owner": metric.owner or "",
                        "description": metric.description or ""
                    }
                ))
            
            self.metrics_table.set_data(row_data)
        
        # Update counts
        self._update_metrics_count()
    
    def _apply_filters(self) -> None:
        """Apply current filters to metrics list."""
        filtered = self.metrics
        
        # Apply text filter
        if self.filter_text:
            text_lower = self.filter_text.lower()
            filtered = [m for m in filtered if (
                text_lower in m.name.lower() or
                text_lower in (m.description or "").lower() or
                text_lower in (m.category or "").lower() or
                text_lower in (m.model_name or "").lower()
            )]
        
        # Apply type filter
        if self.filter_type:
            filtered = [m for m in filtered if m.type.value == self.filter_type]
        
        # Apply category filter
        if self.filter_category:
            filtered = [m for m in filtered if m.category == self.filter_category]
        
        self.filtered_metrics = filtered
    
    def _update_metrics_count(self) -> None:
        """Update the metrics count display."""
        count_widget = self.query_one("#metrics-count")
        total = len(self.metrics)
        filtered = len(self.filtered_metrics)
        
        if total == filtered:
            count_text = f"{total} metrics"
        else:
            count_text = f"{filtered} of {total} metrics"
        
        count_widget.update(count_text)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "filter-input":
            self.filter_text = event.value
            self._update_metrics_display()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "type-filter":
            self.filter_type = event.value if event.value else None
            self._update_metrics_display()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "new-btn":
            self.action_new_metric()
        elif button_id == "edit-btn":
            self.action_edit_metric()
        elif button_id == "duplicate-btn":
            self._duplicate_selected_metric()
        elif button_id == "delete-btn":
            self._delete_selected_metrics()
        elif button_id == "load-btn":
            self._load_metrics_dialog()
        elif button_id == "save-btn":
            self.action_save_to_file()
    
    def on_enhanced_data_table_selection_changed(self, event) -> None:
        """Handle table selection changes."""
        selected_rows = event.selected_rows
        self.selected_metric_ids = {row for row in selected_rows}
        
        # Update button states
        has_selection = len(self.selected_metric_ids) > 0
        single_selection = len(self.selected_metric_ids) == 1
        
        edit_btn = self.query_one("#edit-btn")
        duplicate_btn = self.query_one("#duplicate-btn")
        delete_btn = self.query_one("#delete-btn")
        
        edit_btn.disabled = not single_selection
        duplicate_btn.disabled = not single_selection
        delete_btn.disabled = not has_selection
        
        # Update selection info
        selection_info = self.query_one("#selection-info")
        if has_selection:
            selection_info.update(f"{len(self.selected_metric_ids)} selected")
        else:
            selection_info.update("")
    
    def on_metric_form_modal_metric_saved(self, event: MetricFormModal.MetricSaved) -> None:
        """Handle metric saved from form modal."""
        if event.is_new:
            self.metrics.append(event.metric)
        else:
            # Find and update existing metric
            for i, metric in enumerate(self.metrics):
                if metric.name == event.metric.name:  # Assuming name is unique
                    self.metrics[i] = event.metric
                    break
        
        self._update_metrics_display()
        self.post_message(self.MetricUpdated(event.metric))
    
    def action_new_metric(self) -> None:
        """Create a new metric."""
        model_names = [m.name for m in (self.app_state.models or [])]
        modal = MetricFormModal(models=model_names)
        self.app.push_screen(modal)
    
    def action_edit_metric(self) -> None:
        """Edit the selected metric."""
        if len(self.selected_metric_ids) == 1:
            # Get selected metric
            metric_index = int(list(self.selected_metric_ids)[0].split("_")[1])
            metric = self.filtered_metrics[metric_index]
            
            model_names = [m.name for m in (self.app_state.models or [])]
            modal = MetricFormModal(metric=metric, models=model_names)
            self.app.push_screen(modal)
    
    def action_save_to_file(self) -> None:
        """Save metrics to file."""
        if self.current_seed_file:
            try:
                self.seed_manager.write_seed_file(self.current_seed_file, self.metrics)
                self._show_status(f"Saved {len(self.metrics)} metrics to {self.current_seed_file}")
            except Exception as e:
                self._show_error(f"Failed to save metrics: {e}")
    
    def _duplicate_selected_metric(self) -> None:
        """Duplicate the selected metric."""
        if len(self.selected_metric_ids) == 1:
            metric_index = int(list(self.selected_metric_ids)[0].split("_")[1])
            original = self.filtered_metrics[metric_index]
            
            # Create duplicate with modified name
            duplicate = Metric(
                name=f"{original.name} (Copy)",
                short=f"{original.short}_copy",
                type=original.type,
                category=original.category,
                value=original.value,
                numerator=original.numerator,
                denominator=original.denominator,
                sql=original.sql,
                model_name=original.model_name,
                description=original.description,
                owner=original.owner,
                tags=original.tags.copy() if original.tags else None
            )
            
            self.metrics.append(duplicate)
            self._update_metrics_display()
    
    def _delete_selected_metrics(self) -> None:
        """Delete selected metrics."""
        if self.selected_metric_ids:
            # Get metrics to delete
            indices_to_delete = []
            for metric_id in self.selected_metric_ids:
                index = int(metric_id.split("_")[1])
                indices_to_delete.append(index)
            
            # Remove metrics (in reverse order to maintain indices)
            for index in sorted(indices_to_delete, reverse=True):
                if index < len(self.filtered_metrics):
                    metric_to_remove = self.filtered_metrics[index]
                    self.metrics.remove(metric_to_remove)
            
            self.selected_metric_ids.clear()
            self._update_metrics_display()
    
    def _load_metrics_dialog(self) -> None:
        """Show dialog to load metrics from different file."""
        # This would show a file picker or input dialog
        # For now, just reload from current file
        self._load_metrics_from_project()
    
    def _show_status(self, message: str) -> None:
        """Show status message."""
        # Could show in footer or notification
        pass
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        # Could show error modal or notification
        pass
    
    # Navigation actions
    def action_show_dashboard(self) -> None:
        """Navigate to dashboard."""
        self.app.pop_screen()
    
    def action_show_models(self) -> None:
        """Navigate to model explorer."""
        self.app.push_screen("models")
    
    def action_show_discovery(self) -> None:
        """Navigate to discovery wizard."""
        self.app.push_screen("discovery")
    
    def action_show_settings(self) -> None:
        """Navigate to settings."""
        self.app.push_screen("settings")
    
    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    def action_filter_metrics(self) -> None:
        """Focus the filter input."""
        filter_input = self.query_one("#filter-input")
        filter_input.focus()
    
    def get_metrics_summary(self) -> Dict:
        """Get summary of current metrics."""
        return self.seed_manager.get_metrics_summary(self.metrics)