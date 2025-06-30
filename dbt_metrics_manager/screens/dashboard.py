"""Dashboard screen implementation."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding

from ..widgets import StatsCards
from ..state import AppState


class DashboardScreen(Screen):
    """Main dashboard screen."""
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
    
    def compose(self) -> ComposeResult:
        """Create dashboard layout."""
        yield Header()
        
        if self.app_state.project_loaded:
            yield Container(
                self._create_project_info(),
                self._create_stats_section(),
                self._create_content_section(),
                classes="dashboard-container"
            )
        else:
            yield Container(
                self._create_welcome_section(),
                classes="welcome-container"
            )
        
        yield Footer()
    
    def _create_project_info(self) -> Container:
        """Create project information header."""
        return Container(
            Static(
                f"Project: {self.app_state.project_name} ({self.app_state.project_path})",
                classes="project-info"
            ),
            classes="project-header"
        )
    
    def _create_stats_section(self) -> Container:
        """Create statistics cards section."""
        return Container(
            StatsCards(self.app_state),
            classes="stats-section"
        )
    
    def _create_content_section(self) -> Container:
        """Create main content section."""
        return Container(
            Horizontal(
                self._create_activity_panel(),
                self._create_actions_panel(),
                classes="content-row"
            ),
            classes="content-section"
        )
    
    def _create_activity_panel(self) -> Container:
        """Create recent activity panel."""
        activities = []
        
        if self.app_state.success_message:
            activities.append(f"✓ {self.app_state.success_message}")
        
        if self.app_state.project_loaded:
            activities.extend([
                f"• Loaded {self.app_state.total_models} rollup models",
                f"• Found {self.app_state.total_metrics} existing metrics",
                f"• Coverage: {self.app_state.coverage_percentage:.1f}%"
            ])
        
        if not activities:
            activities = ["No recent activity"]
        
        return Container(
            Static("Recent Activity", classes="panel-title"),
            Static("\\n".join(activities), classes="activity-list"),
            classes="activity-panel"
        )
    
    def _create_actions_panel(self) -> Container:
        """Create quick actions panel."""
        return Container(
            Static("Quick Actions", classes="panel-title"),
            Button("Load Project [F5]", id="load-project-btn"),
            Button("Refresh Data [r]", id="refresh-btn", disabled=not self.app_state.project_loaded),
            classes="actions-panel"
        )
    
    def _create_welcome_section(self) -> Container:
        """Create welcome section for when no project is loaded."""
        return Container(
            Static("Welcome to DBT Metrics Manager", classes="welcome-title"),
            Static("A terminal interface for managing dbt rollup model metrics", classes="welcome-subtitle"),
            Static("", classes="spacer"),
            Static("To get started:", classes="instructions-title"),
            Static("1. Ensure you have a dbt project with rollup models", classes="instruction"),
            Static("2. Run 'dbt docs generate' in your project", classes="instruction"),
            Static("3. Press F5 to configure and load your project", classes="instruction"),
            Static("", classes="spacer"),
            Button("Configure Project [F5]", id="configure-btn", variant="primary"),
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id in ("load-project-btn", "configure-btn"):
            self.action_settings()
        elif event.button.id == "refresh-btn":
            self.action_refresh()
    
    def action_refresh(self) -> None:
        """Refresh project data."""
        if self.app_state.project_loaded:
            success = self.app_state.load_project(self.app_state.project_path)
            if success:
                self.refresh()
                self.notify("Project data refreshed")
            else:
                self.notify(f"Failed to refresh: {self.app_state.error_message}", severity="error")
    
    def action_settings(self) -> None:
        """Open settings screen."""
        from .settings import SettingsScreen
        self.app.push_screen(SettingsScreen(self.app_state))
    
    def action_back(self) -> None:
        """Handle back action."""
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
    
    def on_mount(self) -> None:
        """Handle screen mount."""
        # Clear any previous messages after showing them
        if self.app_state.error_message:
            self.notify(self.app_state.error_message, severity="error")
            self.app_state.clear_error()
        
        if self.app_state.success_message:
            self.app_state.clear_success()