"""Model Explorer screen implementation."""

from typing import List, Optional
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Switch, Input
from textual.binding import Binding
from textual.message import Message

from ..widgets.model_tree import ModelTree, ModelDetailsPanel
from ..state import AppState
from ..models.dbt_model import DbtModel
from ..services.sql_parser import SqlParser, SqlParseResult
from ..services.metric_analyzer import MetricAnalyzer


class ModelExplorerScreen(Screen):
    """Screen for exploring and analyzing dbt models."""
    
    BINDINGS = [
        Binding("f1", "show_dashboard", "Dashboard"),
        Binding("f3", "show_metrics", "Metrics"),
        Binding("f4", "show_discovery", "Discovery"),
        Binding("f5", "show_settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "analyze_model", "Analyze"),
        Binding("d", "discover_metrics", "Discover"),
        Binding("ctrl+f", "search", "Search"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self, app_state: AppState):
        """Initialize the model explorer screen.
        
        Args:
            app_state: Global application state
        """
        super().__init__()
        self.app_state = app_state
        self.sql_parser = SqlParser()
        self.metric_analyzer = MetricAnalyzer(self.sql_parser)
        self.model_tree: Optional[ModelTree] = None
        self.details_panel: Optional[ModelDetailsPanel] = None
        self.current_model: Optional[DbtModel] = None
        self.search_term: str = ""
        self.show_rollup_only: bool = False
    
    class AnalyzeModelRequested(Message):
        """Message sent when model analysis is requested."""
        
        def __init__(self, model: DbtModel) -> None:
            self.model = model
            super().__init__()
    
    class DiscoverMetricsRequested(Message):
        """Message sent when metric discovery is requested."""
        
        def __init__(self, model: DbtModel) -> None:
            self.model = model
            super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create the model explorer layout."""
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
                self._create_toolbar(),
                self._create_main_content(),
                classes="explorer-container"
            )
        
        yield Footer()
    
    def _create_toolbar(self) -> Container:
        """Create the toolbar with controls and filters."""
        return Container(
            Horizontal(
                # Left side - info and search
                Container(
                    Static(f"Project: {self.app_state.project_name}", classes="project-name"),
                    Input(placeholder="Search models...", id="search-input", classes="search-input"),
                    classes="toolbar-left"
                ),
                
                # Right side - filters and actions
                Container(
                    Horizontal(
                        Static("Rollup Only:", classes="filter-label"),
                        Switch(id="rollup-filter", classes="rollup-switch"),
                        Button("Refresh", id="refresh-btn", classes="action-button"),
                        Button("Analyze", id="analyze-btn", classes="action-button", disabled=True),
                        Button("Discover", id="discover-btn", classes="action-button", disabled=True),
                        classes="toolbar-controls"
                    ),
                    classes="toolbar-right"
                ),
                classes="toolbar-horizontal"
            ),
            classes="toolbar"
        )
    
    def _create_main_content(self) -> Container:
        """Create the main content area with tree and details."""
        # Get models for the tree
        models = self.app_state.models or []
        
        return Container(
            Horizontal(
                # Left panel - model tree
                Container(
                    self._create_tree_panel(models),
                    classes="tree-panel"
                ),
                
                # Right panel - model details
                Container(
                    self._create_details_panel(),
                    classes="details-panel"
                ),
                classes="main-horizontal"
            ),
            classes="main-content"
        )
    
    def _create_tree_panel(self, models: List[DbtModel]) -> Container:
        """Create the tree panel with model navigation."""
        self.model_tree = ModelTree(models, id="model-tree", classes="model-tree")
        
        return Container(
            Static(f"Models ({len(models)})", classes="panel-header"),
            self.model_tree,
            classes="tree-container"
        )
    
    def _create_details_panel(self) -> Container:
        """Create the details panel for model information."""
        self.details_panel = ModelDetailsPanel(id="details-panel", classes="details-panel")
        
        return Container(
            Static("Model Details", classes="panel-header"),
            self.details_panel,
            classes="details-container"
        )
    
    def on_mount(self) -> None:
        """Initialize screen when mounted."""
        if self.app_state.project_loaded and self.model_tree:
            self._update_model_counts()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_term = event.value
            self._filter_models()
    
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle filter switch changes."""
        if event.switch.id == "rollup-filter":
            self.show_rollup_only = event.value
            if self.model_tree:
                self.model_tree.show_rollup_only = event.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-btn":
            self.action_refresh()
        elif event.button.id == "analyze-btn":
            self.action_analyze_model()
        elif event.button.id == "discover-btn":
            self.action_discover_metrics()
    
    def on_model_tree_model_selected(self, event: ModelTree.ModelSelected) -> None:
        """Handle model selection from tree."""
        self.current_model = event.model
        self._update_details_panel()
        self._update_action_buttons()
    
    def action_refresh(self) -> None:
        """Refresh the model data."""
        if self.app_state.project_loaded:
            # Reload models from project
            try:
                self.app_state.load_project(self.app_state.project_path)
                models = self.app_state.models or []
                
                if self.model_tree:
                    self.model_tree.refresh_models(models)
                
                self._update_model_counts()
                self._show_status("Models refreshed successfully")
                
            except Exception as e:
                self._show_error(f"Failed to refresh models: {e}")
    
    def action_analyze_model(self) -> None:
        """Analyze the currently selected model."""
        if self.current_model:
            self.post_message(self.AnalyzeModelRequested(self.current_model))
            self._analyze_model_async()
    
    def action_discover_metrics(self) -> None:
        """Discover metrics in the currently selected model."""
        if self.current_model:
            self.post_message(self.DiscoverMetricsRequested(self.current_model))
            # This would typically navigate to the discovery screen
            self.app.push_screen("discovery", self.current_model)
    
    def action_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one("#search-input")
        search_input.focus()
    
    def action_show_dashboard(self) -> None:
        """Navigate to dashboard."""
        self.app.pop_screen()
    
    def action_show_metrics(self) -> None:
        """Navigate to metrics library."""
        self.app.push_screen("metrics")
    
    def action_show_discovery(self) -> None:
        """Navigate to discovery wizard."""
        self.app.push_screen("discovery")
    
    def action_show_settings(self) -> None:
        """Navigate to settings."""
        self.app.push_screen("settings")
    
    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    def _update_details_panel(self) -> None:
        """Update the details panel with current model info."""
        if not self.details_panel or not self.current_model:
            return
        
        # Parse SQL if file exists
        sql_result = None
        if self.current_model.file_path and Path(self.current_model.file_path).exists():
            try:
                sql_result = self.sql_parser.parse_file(Path(self.current_model.file_path))
            except Exception as e:
                # Handle parsing errors gracefully
                pass
        
        self.details_panel.update_model(self.current_model, sql_result)
    
    def _update_action_buttons(self) -> None:
        """Update the state of action buttons based on selection."""
        has_selection = self.current_model is not None
        
        try:
            analyze_btn = self.query_one("#analyze-btn")
            discover_btn = self.query_one("#discover-btn")
            
            analyze_btn.disabled = not has_selection
            discover_btn.disabled = not (has_selection and self.current_model.is_rollup)
        except:
            # Buttons might not exist yet
            pass
    
    def _update_model_counts(self) -> None:
        """Update model count displays."""
        if not self.model_tree:
            return
        
        counts = self.model_tree.get_model_count()
        
        # Update header with counts
        try:
            header_widget = self.query_one(".panel-header")
            header_widget.update(
                f"Models ({counts['visible']}/{counts['total']}) - "
                f"Rollup: {counts['rollup']}, Regular: {counts['regular']}"
            )
        except:
            pass
    
    def _filter_models(self) -> None:
        """Apply search and other filters to the model tree."""
        if not self.model_tree or not self.search_term:
            return
        
        # Filter models by search term
        filtered_models = []
        for model in self.app_state.models or []:
            if (self.search_term.lower() in model.name.lower() or
                (model.file_path and self.search_term.lower() in model.file_path.lower())):
                filtered_models.append(model)
        
        self.model_tree.refresh_models(filtered_models)
        self._update_model_counts()
    
    def _analyze_model_async(self) -> None:
        """Analyze the current model asynchronously."""
        if not self.current_model:
            return
        
        try:
            # Run metric analysis
            discovery = self.metric_analyzer.analyze_model(self.current_model)
            
            # Update details panel with analysis results
            self._show_analysis_results(discovery)
            
        except Exception as e:
            self._show_error(f"Analysis failed: {e}")
    
    def _show_analysis_results(self, discovery) -> None:
        """Show analysis results in the details panel."""
        # This could open a modal or update the details panel
        # For now, we'll add it to the status
        metric_count = len(discovery.suggested_metrics)
        confidence = discovery.confidence_score
        self._show_status(
            f"Analysis complete: {metric_count} metrics found "
            f"(confidence: {confidence:.1%})"
        )
    
    def _show_status(self, message: str) -> None:
        """Show a status message."""
        # Could update footer or show a toast notification
        pass
    
    def _show_error(self, message: str) -> None:
        """Show an error message."""
        # Could show error modal or update status
        pass
    
    def get_selected_model(self) -> Optional[DbtModel]:
        """Get the currently selected model."""
        return self.current_model
    
    def select_model_by_name(self, model_name: str) -> bool:
        """Select a model by name."""
        if self.model_tree:
            return self.model_tree.select_model(model_name)
        return False