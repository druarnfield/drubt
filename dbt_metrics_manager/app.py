"""Main Textual application entry point."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from .screens import DashboardScreen, SettingsScreen
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
    
    def action_show_settings(self) -> None:
        """Show settings screen."""
        self.push_screen(SettingsScreen(self.app_state))
    
    def action_help(self) -> None:
        """Show help information."""
        help_text = """
DBT Metrics Manager TUI - Keyboard Shortcuts

Navigation:
- F1: Dashboard (project overview and stats)
- F5: Settings (project configuration)
- q: Quit application
- Ctrl+D: Toggle dark/light mode
- Ctrl+H: Show this help

Dashboard Actions:
- r: Refresh project data
- Enter: Select highlighted item

General:
- Tab: Move focus between panels
- Escape: Go back/cancel
- Enter: Confirm/select
- Space: Toggle selection (where applicable)

For more information, visit the project documentation.
        """
        self.notify(help_text, title="Help", timeout=10)


def main():
    """Main entry point."""
    app = DbtMetricsManagerApp()
    app.run()


if __name__ == "__main__":
    main()