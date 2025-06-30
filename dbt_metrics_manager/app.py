"""Main Textual application entry point."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from .screens import DashboardScreen, SettingsScreen
from .screens.models import ModelExplorerScreen
from .screens.discovery import DiscoveryWizardScreen
from .screens.metrics import MetricsLibraryScreen
from .state import AppState


class DbtMetricsManagerApp(App[None]):
    """Main TUI application for DBT Metrics Manager."""
    
    CSS_PATH = "assets/app.css"
    
    TITLE = "DBT Metrics Manager"
    SUB_TITLE = "Terminal UI for managing dbt metrics"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        Binding("ctrl+h", "help", "Help"),
        Binding("f1", "show_dashboard", "Dashboard"),
        Binding("f2", "show_models", "Models"),
        Binding("f3", "show_metrics", "Metrics"),
        Binding("f4", "show_discovery", "Discovery"),
        Binding("f5", "show_settings", "Settings"),
    ]
    
    def __init__(self):
        super().__init__()
        self.app_state = AppState()
        self.dark = True
    
    def on_mount(self) -> None:
        """Initialize app on startup."""
        self.push_screen(DashboardScreen(self.app_state))
    
    def action_toggle_dark(self) -> None:
        """Toggle between light and dark mode."""
        self.dark = not self.dark
    
    def action_show_dashboard(self) -> None:
        """Show dashboard screen."""
        self.push_screen(DashboardScreen(self.app_state))
    
    def action_show_models(self) -> None:
        """Show model explorer screen."""
        if not self.app_state.project_loaded:
            self.notify("Please load a project first (F5)", severity="warning")
            return
        self.push_screen(ModelExplorerScreen(self.app_state))
    
    def action_show_metrics(self) -> None:
        """Show metrics library screen."""
        if not self.app_state.project_loaded:
            self.notify("Please load a project first (F5)", severity="warning")
            return
        self.push_screen(MetricsLibraryScreen(self.app_state))
    
    def action_show_discovery(self) -> None:
        """Show discovery wizard screen."""
        if not self.app_state.project_loaded:
            self.notify("Please load a project first (F5)", severity="warning")
            return
        self.push_screen(DiscoveryWizardScreen(self.app_state))
    
    def action_show_settings(self) -> None:
        """Show settings screen."""
        self.push_screen(SettingsScreen(self.app_state))
    
    def action_help(self) -> None:
        """Show help information."""
        help_text = """
DBT Metrics Manager TUI - Keyboard Shortcuts

Navigation:
- F1: Dashboard (project overview and stats)
- F2: Model Explorer (browse and analyze models)
- F3: Metrics Library (manage existing metrics)
- F4: Discovery Wizard (find new metrics)
- F5: Settings (project configuration)
- q: Quit application
- Ctrl+D: Toggle dark/light mode
- Ctrl+H: Show this help

Screen-Specific Actions:
- r: Refresh data
- n: New item (where applicable)
- e: Edit selected item
- d: Delete selected item
- Ctrl+S: Save to file
- Ctrl+F: Filter/search
- Space: Toggle selection
- Enter: Confirm/select
- Escape: Go back/cancel

Model Explorer:
- a: Analyze selected model
- d: Discover metrics in model
- Ctrl+F: Search models

Discovery Wizard:
- Ctrl+A: Analyze all models
- Space: Toggle metric selection

Metrics Library:
- n: Create new metric
- e: Edit selected metric
- d: Delete selected metrics
- Ctrl+O: Load from file

For more information, visit the project documentation.
        """
        self.notify(help_text, title="Help", timeout=15)


def main():
    """Main entry point."""
    app = DbtMetricsManagerApp()
    app.run()


if __name__ == "__main__":
    main()