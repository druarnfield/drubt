"""Statistics cards widget for dashboard."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Horizontal
from textual.widgets import Static
from rich.text import Text

from ..state import AppState


class StatCard(Static):
    """Individual stat card widget."""
    
    def __init__(self, title: str, value: str, subtitle: str = "", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.border_title = title
    
    def render(self) -> Text:
        """Render stat card content."""
        content = Text()
        content.append(f"{self.value}\n", style="bold cyan")
        if self.subtitle:
            content.append(self.subtitle, style="dim white")
        return content


class StatsCards(Widget):
    """Container for dashboard stat cards."""
    
    def __init__(self, app_state: AppState, **kwargs):
        super().__init__(**kwargs)
        self.app_state = app_state
    
    def compose(self) -> ComposeResult:
        """Compose stats cards layout."""
        with Horizontal(classes="stats-row"):
            yield StatCard(
                "Metrics",
                str(self.app_state.total_metrics),
                "defined in seed",
                classes="stat-card"
            )
            yield StatCard(
                "Models", 
                str(self.app_state.total_models),
                "rollup models",
                classes="stat-card"
            )
            yield StatCard(
                "Coverage",
                f"{self.app_state.coverage_percentage:.1f}%",
                "models with metrics",
                classes="stat-card"
            )
            yield StatCard(
                "Discovered",
                str(len(self.app_state.discovered_metrics)),
                "new metrics found",
                classes="stat-card"
            )