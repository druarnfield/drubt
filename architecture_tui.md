# ARCHITECTURE.md

## System Overview

### Technology Stack
- **Framework**: Textual 0.45+ (Python TUI framework)
- **Python**: 3.8+ 
- **Database**: SQLite (for app state/history)
- **SQL Parser**: sqlglot
- **Data Processing**: pandas
- **Styling**: Textual CSS + Rich components

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    Terminal Interface                        │
├─────────────────────────────────────────────────────────────┤
│                    Textual Application                       │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐ │
│  │  Dashboard  │ Model Explorer│ Metric Editor│  Settings │ │
│  │   Screen    │    Screen     │    Screen    │  Screen   │ │
│  └─────────────┴──────────────┴──────────────┴───────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐ │
│  │   AppState  │  ModelState   │ MetricState  │FileState  │ │
│  └─────────────┴──────────────┴──────────────┴───────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                             │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐ │
│  │ DBT Reader  │  SQL Parser   │Seed Manager  │ Analyzer  │ │
│  └─────────────┴──────────────┴──────────────┴───────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    File System                               │
│  ┌─────────────┬──────────────┬──────────────┐            │
│  │manifest.json│ catalog.json  │ *.sql files  │            │
│  └─────────────┴──────────────┴──────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
dbt-metrics-manager-tui/
├── dbt_metrics_manager/
│   ├── __init__.py
│   ├── app.py                     # Main Textual app entry point
│   ├── config.py                  # App configuration loader
│   ├── state/
│   │   ├── __init__.py
│   │   ├── app_state.py           # Global app state
│   │   ├── model_state.py         # Model explorer state
│   │   ├── metric_state.py        # Metric management state
│   │   └── file_state.py          # File operations state
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard.py           # Dashboard screen
│   │   ├── models.py              # Model explorer screen
│   │   ├── metrics.py             # Metric editor screen
│   │   ├── discovery.py           # Discovery wizard screen
│   │   └── settings.py            # Settings screen
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── header.py              # App header widget
│   │   ├── stats_cards.py         # Dashboard stat cards
│   │   ├── metric_card.py         # Metric display card
│   │   ├── model_tree.py          # File tree widget
│   │   ├── metric_form.py         # Metric edit form
│   │   ├── data_table.py          # Reusable data table
│   │   ├── charts.py              # Terminal charts (sparklines)
│   │   └── common.py              # Common UI elements
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dbt_reader.py          # Read dbt artifacts
│   │   ├── sql_parser.py          # Parse SQL with sqlglot
│   │   ├── metric_analyzer.py     # Discover metrics
│   │   ├── seed_manager.py        # CSV file operations
│   │   └── validator.py           # Validation logic
│   ├── models/
│   │   ├── __init__.py
│   │   ├── metric.py              # Metric dataclass
│   │   ├── dbt_model.py           # Model dataclass
│   │   └── discovery_result.py    # Discovery dataclass
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── patterns.py            # Regex patterns
│   │   ├── formatters.py          # String formatters
│   │   ├── theme.py               # Terminal theme
│   │   └── constants.py           # App constants
│   └── assets/
│       ├── app.css                # Textual CSS styles
│       └── keybindings.toml       # Keyboard shortcuts
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_services.py
│   │   ├── test_analyzers.py
│   │   ├── test_validators.py
│   │   └── test_state.py
│   ├── integration/
│   │   └── test_workflows.py
│   └── fixtures/
│       ├── sample_manifest.json
│       ├── sample_catalog.json
│       ├── sample_metrics.csv
│       └── sample_models/
├── setup.py                       # Package setup
├── requirements.txt               # Python dependencies
├── README.md                      # User documentation
└── .gitignore
```

## Core Components

### 1. Entry Point (app.py)

```python
# dbt_metrics_manager/app.py

from textual.app import App
from textual.binding import Binding
from textual.driver import Driver

from .screens import (
    DashboardScreen,
    ModelsScreen, 
    MetricsScreen,
    DiscoveryScreen,
    SettingsScreen
)
from .state import AppState
from .config import get_config

class DbtMetricsManagerApp(App[None]):
    """Main TUI application for DBT Metrics Manager"""
    
    CSS_PATH = "assets/app.css"
    
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
        self.state = AppState()
        self.dark = True
    
    def on_mount(self) -> None:
        """Initialize app on startup"""
        self.push_screen(DashboardScreen())
    
    def action_toggle_dark(self) -> None:
        """Toggle between light and dark mode"""
        self.dark = not self.dark
    
    def action_show_dashboard(self) -> None:
        """Show dashboard screen"""
        self.push_screen(DashboardScreen())
    
    def action_show_models(self) -> None:
        """Show models screen"""
        self.push_screen(ModelsScreen())
    
    def action_show_metrics(self) -> None:
        """Show metrics screen"""
        self.push_screen(MetricsScreen())
    
    def action_show_discovery(self) -> None:
        """Show discovery screen"""
        self.push_screen(DiscoveryScreen())
    
    def action_show_settings(self) -> None:
        """Show settings screen"""
        self.push_screen(SettingsScreen())

def main():
    """Main entry point"""
    app = DbtMetricsManagerApp()
    app.run()

if __name__ == "__main__":
    main()
```

### 2. Configuration (config.py)

```python
# dbt_metrics_manager/config.py

import os
from pathlib import Path
from typing import Dict, Any
import toml

class Config:
    """Application configuration"""
    
    def __init__(self):
        self.app_dir = Path.home() / ".dbt-metrics-manager"
        self.config_file = self.app_dir / "config.toml"
        self.db_file = self.app_dir / "app.db"
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from config file"""
        default_settings = {
            "ui": {
                "theme": "dark",
                "items_per_page": 20,
                "auto_save": True,
                "show_line_numbers": True
            },
            "project": {
                "default_path": "",
                "auto_discover": True,
                "backup_count": 10
            },
            "patterns": {
                "direct_value": r".*_value$",
                "direct_count": r".*_count$",
                "ratio_numerator": r".*_numerator$",
                "ratio_denominator": r".*_denominator$",
            }
        }
        
        if self.config_file.exists():
            user_settings = toml.load(self.config_file)
            return {**default_settings, **user_settings}
        
        return default_settings
    
    def save_settings(self) -> None:
        """Save current settings to config file"""
        self.app_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            toml.dump(self.settings, f)

def get_config() -> Config:
    """Get global config instance"""
    return Config()
```

### 3. State Management Structure

#### Base State (state/app_state.py)

```python
# dbt_metrics_manager/state/app_state.py

import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from ..models import Metric, DbtModel
from ..services import DbtReader, MetricAnalyzer, SeedManager
from ..config import get_config

class AppState:
    """Global application state with persistence"""
    
    def __init__(self):
        self.config = get_config()
        self.db_path = self.config.db_file
        self._init_database()
        
        # Project state
        self.project_path: str = ""
        self.project_loaded: bool = False
        self.project_name: str = ""
        
        # Data
        self.models: List[DbtModel] = []
        self.metrics: List[Metric] = []
        self.discovered_metrics: List[Metric] = []
        
        # UI state
        self.loading: bool = False
        self.loading_message: str = ""
        self.error_message: str = ""
        
        # Services
        self.dbt_reader: Optional[DbtReader] = None
        self.analyzer: Optional[MetricAnalyzer] = None
        self.seed_manager: Optional[SeedManager] = None
    
    def _init_database(self) -> None:
        """Initialize SQLite database for persistence"""
        self.config.app_dir.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_history (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    name TEXT,
                    last_opened TIMESTAMP,
                    model_count INTEGER,
                    metric_count INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
    
    def load_project(self, path: str) -> bool:
        """Load a dbt project from specified path"""
        try:
            self.loading = True
            self.loading_message = "Loading project..."
            
            # Validate project
            self.dbt_reader = DbtReader(path)
            valid, message = self.dbt_reader.validate_project()
            
            if not valid:
                self.error_message = message
                return False
            
            # Load project data
            self.project_path = path
            self.project_name = self.dbt_reader.get_project_name()
            self.models = self.dbt_reader.get_rollup_models()
            self.metrics = self.dbt_reader.load_seed_metrics()
            
            # Initialize services
            self.analyzer = MetricAnalyzer()
            self.seed_manager = SeedManager(path)
            
            self.project_loaded = True
            self._save_project_to_history()
            
            return True
            
        except Exception as e:
            self.error_message = str(e)
            return False
        finally:
            self.loading = False
            self.loading_message = ""
    
    def _save_project_to_history(self) -> None:
        """Save project to recent history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO project_history 
                (path, name, last_opened, model_count, metric_count)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.project_path,
                self.project_name,
                datetime.now(),
                len(self.models),
                len(self.metrics)
            ))
    
    def get_recent_projects(self) -> List[Dict[str, Any]]:
        """Get recently opened projects"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT path, name, last_opened, model_count, metric_count
                FROM project_history
                ORDER BY last_opened DESC
                LIMIT 10
            """)
            
            return [
                {
                    "path": row[0],
                    "name": row[1],
                    "last_opened": row[2],
                    "model_count": row[3],
                    "metric_count": row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def clear_error(self) -> None:
        """Clear error message"""
        self.error_message = ""
    
    @property
    def total_metrics(self) -> int:
        """Total number of defined metrics"""
        return len(self.metrics)
    
    @property
    def total_models(self) -> int:
        """Total number of rollup models"""
        return len(self.models)
    
    @property
    def models_with_metrics(self) -> int:
        """Number of models that have metrics defined"""
        model_names = {metric.source_model for metric in self.metrics if metric.source_model}
        return len(model_names)
    
    @property
    def coverage_percentage(self) -> float:
        """Percentage of models with at least one metric"""
        if not self.models:
            return 0.0
        return (self.models_with_metrics / len(self.models)) * 100
```

### 4. Screen Structure

#### Dashboard Screen (screens/dashboard.py)

```python
# dbt_metrics_manager/screens/dashboard.py

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button

from ..widgets import StatsCards, RecentActivity, QuickActions
from ..state import AppState

class DashboardScreen(Screen):
    """Main dashboard screen"""
    
    BINDINGS = [
        ("d", "discover", "Discover Metrics"),
        ("e", "export", "Export Seed"),
        ("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
    
    def compose(self) -> ComposeResult:
        """Compose dashboard layout"""
        yield Header()
        
        if self.app_state.project_loaded:
            yield Container(
                Vertical(
                    StatsCards(self.app_state),
                    Horizontal(
                        RecentActivity(self.app_state),
                        QuickActions(self.app_state),
                        classes="content-row"
                    ),
                    classes="dashboard-content"
                ),
                classes="main-container"
            )
        else:
            yield Container(
                Static("No project loaded. Press F5 for Settings.", classes="welcome"),
                classes="welcome-container"
            )
        
        yield Footer()
    
    def action_discover(self) -> None:
        """Run metric discovery"""
        self.app.push_screen("discovery")
    
    def action_export(self) -> None:
        """Export seed file"""
        if self.app_state.seed_manager:
            self.app_state.seed_manager.write_metrics(self.app_state.metrics)
            self.notify("Seed file exported successfully")
    
    def action_refresh(self) -> None:
        """Refresh dashboard data"""
        if self.app_state.project_loaded:
            self.app_state.load_project(self.app_state.project_path)
            self.refresh()
```

#### Model Explorer Screen (screens/models.py)

```python
# dbt_metrics_manager/screens/models.py

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input

from ..widgets import ModelTree, ModelDetails, ModelSearch
from ..state import AppState, ModelState

class ModelsScreen(Screen):
    """Model explorer screen with tree view and details"""
    
    BINDINGS = [
        ("ctrl+f", "focus_search", "Search"),
        ("ctrl+r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
    ]
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.model_state = ModelState(app_state)
    
    def compose(self) -> ComposeResult:
        """Compose model explorer layout"""
        yield Header()
        
        yield Horizontal(
            Vertical(
                ModelSearch(self.model_state),
                ModelTree(self.model_state),
                classes="sidebar",
                id="models-sidebar"
            ),
            ModelDetails(self.model_state),
            classes="main-content"
        )
        
        yield Footer()
    
    def action_focus_search(self) -> None:
        """Focus search input"""
        search_input = self.query_one("#model-search", Input)
        search_input.focus()
    
    def action_refresh(self) -> None:
        """Refresh model data"""
        self.model_state.refresh_models()
        self.refresh()
    
    def action_back(self) -> None:
        """Return to dashboard"""
        self.app.pop_screen()
```

### 5. Widget Structure

#### Stats Cards Widget (widgets/stats_cards.py)

```python
# dbt_metrics_manager/widgets/stats_cards.py

from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Horizontal
from textual.widgets import Static
from rich.text import Text

from ..state import AppState

class StatCard(Static):
    """Individual stat card widget"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.subtitle = subtitle
    
    def render(self) -> Text:
        """Render stat card content"""
        content = Text()
        content.append(f"{self.value}\n", style="bold cyan")
        content.append(f"{self.title}\n", style="white")
        if self.subtitle:
            content.append(self.subtitle, style="dim white")
        return content

class StatsCards(Widget):
    """Container for dashboard stat cards"""
    
    def __init__(self, app_state: AppState, **kwargs):
        super().__init__(**kwargs)
        self.app_state = app_state
    
    def compose(self) -> ComposeResult:
        """Compose stats cards layout"""
        yield Horizontal(
            StatCard(
                "Total Metrics",
                str(self.app_state.total_metrics),
                "defined in seed"
            ),
            StatCard(
                "Total Models", 
                str(self.app_state.total_models),
                "rollup models"
            ),
            StatCard(
                "Coverage",
                f"{self.app_state.coverage_percentage:.1f}%",
                "models with metrics"
            ),
            StatCard(
                "Discovered",
                str(len(self.app_state.discovered_metrics)),
                "new metrics found"
            ),
            classes="stats-row"
        )
```

#### Model Tree Widget (widgets/model_tree.py)

```python
# dbt_metrics_manager/widgets/model_tree.py

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from ..state import ModelState
from ..models import DbtModel

class ModelTree(Widget):
    """Tree view of dbt models"""
    
    def __init__(self, model_state: ModelState, **kwargs):
        super().__init__(**kwargs)
        self.model_state = model_state
    
    def compose(self) -> ComposeResult:
        """Compose tree widget"""
        tree = Tree("Models", id="model-tree")
        self._populate_tree(tree)
        yield tree
    
    def _populate_tree(self, tree: Tree) -> None:
        """Populate tree with models"""
        # Group models by directory
        folders = {}
        
        for model in self.model_state.filtered_models:
            path_parts = model.original_file_path.split("/") if model.original_file_path else ["unknown"]
            folder = "/".join(path_parts[:-1]) or "root"
            
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(model)
        
        # Create tree nodes
        for folder, models in folders.items():
            folder_node = tree.root.add(folder, expand=True)
            
            for model in models:
                # Add visual indicator for metric coverage
                has_metrics = any(m.source_model == model.name for m in self.model_state.app_state.metrics)
                icon = "●" if has_metrics else "○"
                
                model_node = folder_node.add(f"{icon} {model.name}", data=model)
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle model selection"""
        if isinstance(event.node.data, DbtModel):
            self.model_state.select_model(event.node.data.unique_id)
```

### 6. Data Table Widget

#### Data Table (widgets/data_table.py)

```python
# dbt_metrics_manager/widgets/data_table.py

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable
from textual.coordinate import Coordinate
from typing import List, Dict, Any, Optional, Callable

class InteractiveDataTable(Widget):
    """Enhanced data table with search, sort, and pagination"""
    
    def __init__(
        self, 
        data: List[Dict[str, Any]],
        columns: List[Dict[str, str]],
        on_row_select: Optional[Callable] = None,
        selectable: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.data = data
        self.columns = columns
        self.on_row_select = on_row_select
        self.selectable = selectable
        self.selected_rows = set()
    
    def compose(self) -> ComposeResult:
        """Compose data table"""
        table = DataTable(id="data-table")
        
        # Add columns
        for col in self.columns:
            table.add_column(col["title"], key=col["key"])
        
        # Add rows
        for i, row in enumerate(self.data):
            table.add_row(*[str(row.get(col["key"], "")) for col in self.columns], key=str(i))
        
        yield table
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        if self.on_row_select:
            row_index = int(event.row_key.value)
            row_data = self.data[row_index]
            self.on_row_select(row_data)
        
        if self.selectable:
            row_key = event.row_key.value
            if row_key in self.selected_rows:
                self.selected_rows.remove(row_key)
            else:
                self.selected_rows.add(row_key)
```

## Testing Structure

### Unit Tests

```python
# tests/unit/test_app_state.py

import pytest
import tempfile
from pathlib import Path

from dbt_metrics_manager.state import AppState
from dbt_metrics_manager.models import Metric

def test_app_state_initialization():
    """Test app state initializes correctly"""
    state = AppState()
    assert not state.project_loaded
    assert len(state.models) == 0
    assert len(state.metrics) == 0

def test_load_project_invalid_path():
    """Test loading invalid project path"""
    state = AppState()
    result = state.load_project("/invalid/path")
    assert not result
    assert state.error_message != ""

@pytest.fixture
def temp_dbt_project():
    """Create temporary dbt project for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create basic dbt project structure
        target_dir = project_dir / "target"
        target_dir.mkdir()
        
        # Create minimal manifest.json
        manifest = {
            "nodes": {},
            "metadata": {"project_name": "test_project"}
        }
        
        with open(target_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        yield project_dir
```

### Integration Tests

```python
# tests/integration/test_tui_workflows.py

import pytest
from textual.pilot import Pilot

from dbt_metrics_manager.app import DbtMetricsManagerApp

@pytest.mark.asyncio
async def test_dashboard_navigation():
    """Test navigating between screens"""
    app = DbtMetricsManagerApp()
    
    async with app.run_test() as pilot:
        # Test pressing F2 to go to models screen
        await pilot.press("f2")
        assert app.screen.title == "Models"
        
        # Test escape to go back
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)

@pytest.mark.asyncio
async def test_metric_discovery_flow():
    """Test complete metric discovery workflow"""
    app = DbtMetricsManagerApp()
    
    async with app.run_test() as pilot:
        # Load test project
        # Run discovery
        # Select metrics
        # Save results
        pass
```

## Deployment & Distribution

### Package Setup (setup.py)

```python
# setup.py

from setuptools import setup, find_packages

setup(
    name="dbt-metrics-manager",
    version="1.0.0",
    description="Terminal UI for managing DBT metrics",
    packages=find_packages(),
    install_requires=[
        "textual>=0.45.0",
        "rich>=13.0.0",
        "pandas>=2.0.0",
        "sqlglot>=18.0.0",
        "pyyaml>=6.0.0",
        "toml>=0.10.0",
    ],
    entry_points={
        "console_scripts": [
            "dbt-metrics=dbt_metrics_manager.app:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
```

### Requirements.txt

```
textual==0.45.1
rich==13.7.0
pandas==2.1.3
sqlglot==18.15.0
pyyaml==6.0.1
toml==0.10.2
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.10.1
```