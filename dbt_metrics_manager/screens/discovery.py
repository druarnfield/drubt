"""Discovery Wizard screen for guided metric discovery."""

from typing import List, Optional, Dict, Set
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Switch, Input, SelectionList, 
    ProgressBar, Tabs, TabPane, DataTable, Checkbox
)
from textual.binding import Binding
from textual.message import Message

from ..state import AppState
from ..models.dbt_model import DbtModel
from ..models.metric import Metric, MetricType
from ..services.metric_analyzer import MetricAnalyzer, MetricDiscovery
from ..services.seed_manager import SeedManager
from ..services.sql_parser import SqlParser


class DiscoveryWizardScreen(Screen):
    """Screen for guided metric discovery workflow."""
    
    BINDINGS = [
        Binding("f1", "show_dashboard", "Dashboard"),
        Binding("f2", "show_models", "Models"),
        Binding("f3", "show_metrics", "Metrics"),
        Binding("f5", "show_settings", "Settings"),
        Binding("ctrl+s", "save_metrics", "Save"),
        Binding("ctrl+a", "analyze_all", "Analyze All"),
        Binding("space", "toggle_selection", "Toggle"),
        Binding("enter", "confirm_action", "Confirm"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self, app_state: AppState, selected_model: Optional[DbtModel] = None):
        """Initialize the discovery wizard.
        
        Args:
            app_state: Global application state
            selected_model: Pre-selected model to analyze (optional)
        """
        super().__init__()
        self.app_state = app_state
        self.sql_parser = SqlParser()
        self.metric_analyzer = MetricAnalyzer(self.sql_parser)
        self.seed_manager = SeedManager()
        
        # Discovery state
        self.selected_model = selected_model
        self.discovery_results: Dict[str, MetricDiscovery] = {}
        self.selected_metrics: Set[str] = set()
        self.current_step = "select"  # select, analyze, review, save
        self.analysis_progress = 0
        
        # UI components
        self.tabs: Optional[Tabs] = None
        self.model_list: Optional[SelectionList] = None
        self.results_table: Optional[DataTable] = None
        self.progress_bar: Optional[ProgressBar] = None
    
    class MetricsDiscovered(Message):
        """Message sent when metrics are discovered."""
        
        def __init__(self, count: int) -> None:
            self.count = count
            super().__init__()
    
    class MetricsSaved(Message):
        """Message sent when metrics are saved."""
        
        def __init__(self, count: int, file_path: str) -> None:
            self.count = count
            self.file_path = file_path
            super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create the discovery wizard layout."""
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
                self._create_wizard_content(),
                classes="discovery-container"
            )
        
        yield Footer()
    
    def _create_wizard_content(self) -> Container:
        """Create the main wizard content with tabs."""
        self.tabs = Tabs(
            "Select Models",
            "Analyze & Discover", 
            "Review Results",
            "Save Metrics",
            id="discovery-tabs"
        )
        
        return Container(
            self._create_header_info(),
            self.tabs,
            self._create_tab_content(),
            classes="wizard-content"
        )
    
    def _create_header_info(self) -> Container:
        """Create header with project info and progress."""
        return Container(
            Horizontal(
                Static(f"Project: {self.app_state.project_name}", classes="project-info"),
                Static("Step 1 of 4: Select Models", id="step-info", classes="step-info"),
                classes="header-info"
            ),
            classes="discovery-header"
        )
    
    def _create_tab_content(self) -> Container:
        """Create content for all tabs."""
        return Container(
            # Tab 1: Select Models
            TabPane("Select Models", id="select-tab"),
            
            # Tab 2: Analyze & Discover  
            TabPane("Analyze & Discover", id="analyze-tab"),
            
            # Tab 3: Review Results
            TabPane("Review Results", id="review-tab"),
            
            # Tab 4: Save Metrics
            TabPane("Save Metrics", id="save-tab"),
            
            classes="tab-content"
        )
    
    def on_mount(self) -> None:
        """Initialize wizard when mounted."""
        self._setup_select_tab()
        
        # If a model was pre-selected, move to analysis
        if self.selected_model:
            self._add_preselected_model()
    
    def _setup_select_tab(self) -> None:
        """Setup the model selection tab."""
        select_tab = self.query_one("#select-tab")
        
        # Get rollup models
        rollup_models = [m for m in (self.app_state.models or []) if m.is_rollup]
        
        if not rollup_models:
            select_tab.mount(
                Container(
                    Static("No rollup models found in this project.", classes="info-message"),
                    Static("Rollup models are required for metric discovery.", classes="help-text"),
                    classes="no-models-container"
                )
            )
            return
        
        # Create model selection list
        model_options = []
        for model in rollup_models:
            columns_info = f" ({len(model.columns)} columns)" if model.columns else ""
            model_options.append((model.name + columns_info, model.name))
        
        self.model_list = SelectionList(
            *model_options,
            id="model-selection",
            classes="model-list"
        )
        
        select_tab.mount(
            Container(
                Static(f"Select rollup models to analyze ({len(rollup_models)} available):", 
                      classes="section-header"),
                self.model_list,
                Horizontal(
                    Button("Select All", id="select-all-btn", classes="action-button"),
                    Button("Clear All", id="clear-all-btn", classes="action-button"),
                    Button("Next: Analyze", id="analyze-btn", classes="primary-button"),
                    classes="selection-controls"
                ),
                classes="select-content"
            )
        )
    
    def _setup_analyze_tab(self) -> None:
        """Setup the analysis tab."""
        analyze_tab = self.query_one("#analyze-tab")
        
        self.progress_bar = ProgressBar(
            total=100,
            show_eta=True,
            id="analysis-progress"
        )
        
        analyze_tab.mount(
            Container(
                Static("Analyzing selected models for potential metrics...", 
                      classes="section-header"),
                self.progress_bar,
                Static("", id="analysis-status", classes="status-text"),
                Container(id="analysis-results", classes="analysis-results"),
                Horizontal(
                    Button("Back", id="back-to-select-btn", classes="action-button"),
                    Button("Start Analysis", id="start-analysis-btn", classes="primary-button"),
                    Button("Next: Review", id="review-btn", classes="primary-button", disabled=True),
                    classes="analysis-controls"
                ),
                classes="analyze-content"
            )
        )
    
    def _setup_review_tab(self) -> None:
        """Setup the results review tab."""
        review_tab = self.query_one("#review-tab")
        
        # Create results table
        self.results_table = DataTable(
            show_header=True,
            show_row_labels=False,
            zebra_stripes=True,
            id="results-table"
        )
        
        # Add columns
        self.results_table.add_columns(
            "Select", "Model", "Metric", "Type", "Category", "Confidence", "Description"
        )
        
        review_tab.mount(
            Container(
                Static("Review discovered metrics and select which to save:", 
                      classes="section-header"),
                Horizontal(
                    Button("Select All", id="select-all-metrics-btn", classes="action-button"),
                    Button("Select High Confidence", id="select-high-conf-btn", classes="action-button"),
                    Button("Clear Selection", id="clear-metrics-btn", classes="action-button"),
                    classes="review-controls"
                ),
                self.results_table,
                Horizontal(
                    Button("Back", id="back-to-analyze-btn", classes="action-button"),
                    Button("Next: Save", id="save-btn", classes="primary-button", disabled=True),
                    classes="review-navigation"
                ),
                classes="review-content"
            )
        )
    
    def _setup_save_tab(self) -> None:
        """Setup the save metrics tab."""
        save_tab = self.query_one("#save-tab")
        
        save_tab.mount(
            Container(
                Static("Save discovered metrics to seed file:", classes="section-header"),
                Container(
                    Static("Selected metrics will be added to your project's metric_definitions.csv file."),
                    Static("", id="save-summary", classes="save-summary"),
                    Input(
                        placeholder="data/metric_definitions.csv",
                        value="data/metric_definitions.csv",
                        id="save-path-input",
                        classes="save-path"
                    ),
                    Checkbox("Create backup of existing file", value=True, id="backup-checkbox"),
                    Checkbox("Merge with existing metrics", value=True, id="merge-checkbox"),
                    classes="save-options"
                ),
                Horizontal(
                    Button("Back", id="back-to-review-btn", classes="action-button"),
                    Button("Save Metrics", id="final-save-btn", classes="primary-button"),
                    classes="save-controls"
                ),
                Container(id="save-results", classes="save-results"),
                classes="save-content"
            )
        )
    
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab changes."""
        tab_id = event.tab.id
        
        if tab_id == "select-tab":
            self.current_step = "select"
            self._update_step_info("Step 1 of 4: Select Models")
        elif tab_id == "analyze-tab":
            self.current_step = "analyze"
            self._update_step_info("Step 2 of 4: Analyze & Discover")
            if not hasattr(self, '_analyze_tab_setup'):
                self._setup_analyze_tab()
                self._analyze_tab_setup = True
        elif tab_id == "review-tab":
            self.current_step = "review"
            self._update_step_info("Step 3 of 4: Review Results")
            if not hasattr(self, '_review_tab_setup'):
                self._setup_review_tab()
                self._review_tab_setup = True
        elif tab_id == "save-tab":
            self.current_step = "save"
            self._update_step_info("Step 4 of 4: Save Metrics")
            if not hasattr(self, '_save_tab_setup'):
                self._setup_save_tab()
                self._save_tab_setup = True
            self._update_save_summary()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "select-all-btn":
            self._select_all_models()
        elif button_id == "clear-all-btn":
            self._clear_all_models()
        elif button_id == "analyze-btn":
            self._move_to_analyze()
        elif button_id == "start-analysis-btn":
            self._start_analysis()
        elif button_id == "review-btn":
            self._move_to_review()
        elif button_id == "save-btn":
            self._move_to_save()
        elif button_id == "final-save-btn":
            self._save_metrics()
        elif button_id.startswith("back-"):
            self._handle_back_navigation(button_id)
        elif button_id in ["select-all-metrics-btn", "select-high-conf-btn", "clear-metrics-btn"]:
            self._handle_metric_selection(button_id)
    
    def _select_all_models(self) -> None:
        """Select all models in the list."""
        if self.model_list:
            for i in range(len(self.model_list._nodes)):
                self.model_list.select(i)
    
    def _clear_all_models(self) -> None:
        """Clear all model selections."""
        if self.model_list:
            self.model_list.clear()
    
    def _move_to_analyze(self) -> None:
        """Move to the analysis tab."""
        if self.tabs:
            self.tabs.active = "analyze-tab"
    
    def _start_analysis(self) -> None:
        """Start the metric discovery analysis."""
        if not self.model_list:
            return
        
        selected_models = self._get_selected_models()
        if not selected_models:
            self._show_status("Please select at least one model to analyze.")
            return
        
        # Start analysis
        self._run_analysis(selected_models)
    
    def _run_analysis(self, models: List[DbtModel]) -> None:
        """Run metric analysis on selected models."""
        total_models = len(models)
        
        self._update_analysis_status(f"Analyzing {total_models} models...")
        
        for i, model in enumerate(models):
            try:
                # Update progress
                progress = int((i / total_models) * 100)
                if self.progress_bar:
                    self.progress_bar.update(progress=progress)
                
                self._update_analysis_status(f"Analyzing {model.name}...")
                
                # Run analysis
                discovery = self.metric_analyzer.analyze_model(model)
                self.discovery_results[model.name] = discovery
                
            except Exception as e:
                self._update_analysis_status(f"Error analyzing {model.name}: {e}")
        
        # Complete analysis
        if self.progress_bar:
            self.progress_bar.update(progress=100)
        
        total_metrics = sum(len(d.suggested_metrics) for d in self.discovery_results.values())
        self._update_analysis_status(f"Analysis complete! Found {total_metrics} potential metrics.")
        
        # Enable next button
        review_btn = self.query_one("#review-btn")
        review_btn.disabled = False
        
        self.post_message(self.MetricsDiscovered(total_metrics))
    
    def _move_to_review(self) -> None:
        """Move to review tab and populate results."""
        if self.tabs:
            self.tabs.active = "review-tab"
        
        self._populate_results_table()
    
    def _populate_results_table(self) -> None:
        """Populate the results table with discovered metrics."""
        if not self.results_table:
            return
        
        self.results_table.clear()
        
        for model_name, discovery in self.discovery_results.items():
            for metric in discovery.suggested_metrics:
                # Create unique ID for selection tracking
                metric_id = f"{model_name}:{metric.name}"
                
                # Add row to table
                self.results_table.add_row(
                    "☐",  # Selection checkbox (text representation)
                    model_name,
                    metric.name,
                    metric.type.value,
                    metric.category or "General",
                    f"{metric.confidence_score:.1%}" if metric.confidence_score else "N/A",
                    metric.description or ""
                )
    
    def _handle_metric_selection(self, button_id: str) -> None:
        """Handle metric selection buttons."""
        if button_id == "select-all-metrics-btn":
            self._select_all_metrics()
        elif button_id == "select-high-conf-btn":
            self._select_high_confidence_metrics()
        elif button_id == "clear-metrics-btn":
            self._clear_metric_selection()
    
    def _select_all_metrics(self) -> None:
        """Select all metrics in the results."""
        for model_name, discovery in self.discovery_results.items():
            for metric in discovery.suggested_metrics:
                metric_id = f"{model_name}:{metric.name}"
                self.selected_metrics.add(metric_id)
        self._update_results_display()
    
    def _select_high_confidence_metrics(self) -> None:
        """Select metrics with high confidence (>70%)."""
        for model_name, discovery in self.discovery_results.items():
            for metric in discovery.suggested_metrics:
                if metric.confidence_score and metric.confidence_score > 0.7:
                    metric_id = f"{model_name}:{metric.name}"
                    self.selected_metrics.add(metric_id)
        self._update_results_display()
    
    def _clear_metric_selection(self) -> None:
        """Clear all metric selections."""
        self.selected_metrics.clear()
        self._update_results_display()
    
    def _update_results_display(self) -> None:
        """Update the results table display with current selections."""
        # This would update the checkboxes in the table
        # For now, just enable/disable the save button
        save_btn = self.query_one("#save-btn")
        save_btn.disabled = len(self.selected_metrics) == 0
    
    def _move_to_save(self) -> None:
        """Move to save tab."""
        if self.tabs:
            self.tabs.active = "save-tab"
    
    def _update_save_summary(self) -> None:
        """Update the save summary with selected metrics count."""
        summary_widget = self.query_one("#save-summary")
        count = len(self.selected_metrics)
        summary_widget.update(f"Ready to save {count} selected metrics.")
    
    def _save_metrics(self) -> None:
        """Save the selected metrics to file."""
        save_path_input = self.query_one("#save-path-input")
        backup_checkbox = self.query_one("#backup-checkbox")
        merge_checkbox = self.query_one("#merge-checkbox")
        
        save_path = Path(self.app_state.project_path) / save_path_input.value
        create_backup = backup_checkbox.value
        merge_existing = merge_checkbox.value
        
        try:
            # Collect selected metrics
            metrics_to_save = self._collect_selected_metrics()
            
            if merge_existing and save_path.exists():
                # Merge with existing
                self.seed_manager.add_metrics(save_path, metrics_to_save)
            else:
                # Write new file
                self.seed_manager.write_seed_file(save_path, metrics_to_save, backup=create_backup)
            
            # Show success
            results_container = self.query_one("#save-results")
            results_container.mount(
                Static(f"✅ Successfully saved {len(metrics_to_save)} metrics to {save_path}", 
                      classes="success-message")
            )
            
            self.post_message(self.MetricsSaved(len(metrics_to_save), str(save_path)))
            
        except Exception as e:
            # Show error
            results_container = self.query_one("#save-results")
            results_container.mount(
                Static(f"❌ Error saving metrics: {e}", classes="error-message")
            )
    
    def _collect_selected_metrics(self) -> List[Metric]:
        """Collect the selected metrics for saving."""
        metrics = []
        
        for model_name, discovery in self.discovery_results.items():
            for metric in discovery.suggested_metrics:
                metric_id = f"{model_name}:{metric.name}"
                if metric_id in self.selected_metrics:
                    # Set the model name for the metric
                    metric.model_name = model_name
                    metrics.append(metric)
        
        return metrics
    
    def _get_selected_models(self) -> List[DbtModel]:
        """Get the currently selected models."""
        if not self.model_list:
            return []
        
        selected_models = []
        for item in self.model_list.selection:
            model_name = item.value
            model = next((m for m in (self.app_state.models or []) if m.name == model_name), None)
            if model:
                selected_models.append(model)
        
        return selected_models
    
    def _add_preselected_model(self) -> None:
        """Add pre-selected model and move to analysis."""
        if self.selected_model and self.model_list:
            # Select the model in the list
            for i, option in enumerate(self.model_list._nodes):
                if option.value == self.selected_model.name:
                    self.model_list.select(i)
                    break
            
            # Move directly to analysis
            self._move_to_analyze()
    
    def _handle_back_navigation(self, button_id: str) -> None:
        """Handle back button navigation."""
        if button_id == "back-to-select-btn":
            if self.tabs:
                self.tabs.active = "select-tab"
        elif button_id == "back-to-analyze-btn":
            if self.tabs:
                self.tabs.active = "analyze-tab"
        elif button_id == "back-to-review-btn":
            if self.tabs:
                self.tabs.active = "review-tab"
    
    def _update_step_info(self, step_text: str) -> None:
        """Update the step information display."""
        step_info = self.query_one("#step-info")
        step_info.update(step_text)
    
    def _update_analysis_status(self, status: str) -> None:
        """Update the analysis status display."""
        status_widget = self.query_one("#analysis-status")
        status_widget.update(status)
    
    def _show_status(self, message: str) -> None:
        """Show a status message."""
        # Could update footer or show notification
        pass
    
    # Navigation actions
    def action_show_dashboard(self) -> None:
        """Navigate to dashboard."""
        self.app.pop_screen()
    
    def action_show_models(self) -> None:
        """Navigate to model explorer."""
        self.app.push_screen("models")
    
    def action_show_metrics(self) -> None:
        """Navigate to metrics library."""
        self.app.push_screen("metrics")
    
    def action_show_settings(self) -> None:
        """Navigate to settings."""
        self.app.push_screen("settings")
    
    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    def action_save_metrics(self) -> None:
        """Quick save selected metrics."""
        if self.current_step == "save":
            self._save_metrics()
    
    def action_analyze_all(self) -> None:
        """Quick analyze all models."""
        if self.current_step == "select":
            self._select_all_models()
            self._move_to_analyze()
            self._start_analysis()
    
    def action_toggle_selection(self) -> None:
        """Toggle selection in current context."""
        # Implementation depends on current tab and context
        pass
    
    def action_confirm_action(self) -> None:
        """Confirm current action."""
        # Implementation depends on current tab
        pass