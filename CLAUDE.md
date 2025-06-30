# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📋 Important: Check Development History
- **ALWAYS check `actions.log`** for detailed development progress and implementation notes
- **Review git commit messages** for context on recent changes and decisions
- **Read through recent commit history** with `git log --oneline -10` to understand current state

## Project Overview

This is a **DBT Metrics Manager TUI** project - a terminal-based application built with Textual (Python) that provides a rich text user interface for discovering, managing, and maintaining metrics from dbt rollup models. The app parses dbt artifacts (manifest.json, catalog.json) and SQL files to identify metric columns, then helps users maintain a centralized metric_definitions.csv seed file through an intuitive terminal interface.

## Technology Stack

- **Framework**: Textual 0.45+ (Python TUI framework)
- **Python**: 3.8+
- **Database**: SQLite (for app state/history)
- **SQL Parser**: sqlglot
- **Data Processing**: pandas
- **Styling**: Textual CSS + Rich components

## Development Commands

### Setup and Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install textual rich pandas sqlglot pyyaml

# Install in development mode (when setup.py exists)
pip install -e .

# Verify Textual installation
textual --version
```

### Running the Application
```bash
# Run the main application
python -m dbt_metrics_manager.app

# Or when installed as package
dbt-metrics
```

### Testing
```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run all tests with coverage
pytest --cov=dbt_metrics_manager

# Run specific test file
pytest tests/unit/test_metric_analyzer.py -v
```

### Code Quality
```bash
# Format code
black dbt_metrics_manager/

# Check linting
flake8 dbt_metrics_manager/

# Type checking (if configured)
mypy dbt_metrics_manager/
```

## Architecture

### High-Level Structure
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
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure (when implemented)
```
dbt_metrics_manager/
├── app.py                     # Main Textual app entry point
├── config.py                  # App configuration loader
├── state/                     # Application state management
│   ├── app_state.py           # Global app state
│   ├── model_state.py         # Model explorer state
│   ├── metric_state.py        # Metric management state
│   └── file_state.py          # File operations state
├── screens/                   # Textual screens
│   ├── dashboard.py           # Dashboard screen
│   ├── models.py              # Model explorer screen
│   ├── metrics.py             # Metric editor screen
│   ├── discovery.py           # Discovery wizard screen
│   └── settings.py            # Settings screen
├── widgets/                   # Reusable UI components
│   ├── header.py              # App header widget
│   ├── stats_cards.py         # Dashboard stat cards
│   ├── model_tree.py          # File tree widget
│   ├── metric_form.py         # Metric edit form
│   └── data_table.py          # Reusable data table
├── services/                  # Business logic
│   ├── dbt_reader.py          # Read dbt artifacts
│   ├── sql_parser.py          # Parse SQL with sqlglot
│   ├── metric_analyzer.py     # Discover metrics
│   ├── seed_manager.py        # CSV file operations
│   └── validator.py           # Validation logic
├── models/                    # Data models
│   ├── metric.py              # Metric dataclass
│   ├── dbt_model.py           # Model dataclass
│   └── discovery_result.py    # Discovery dataclass
├── utils/                     # Utilities
│   ├── patterns.py            # Regex patterns
│   ├── formatters.py          # String formatters
│   ├── theme.py               # Terminal theme
│   └── constants.py           # App constants
└── assets/
    ├── app.css                # Textual CSS styles
    └── keybindings.toml       # Keyboard shortcuts
```

## Core Components

### Entry Point Pattern
The main application entry point follows this pattern:
```python
from textual.app import App
from textual.binding import Binding

class DbtMetricsManagerApp(App[None]):
    """Main TUI application for DBT Metrics Manager"""
    
    CSS_PATH = "assets/app.css"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        Binding("f1", "show_dashboard", "Dashboard"),
        # ... other bindings
    ]
    
    def on_mount(self) -> None:
        """Initialize app on startup"""
        self.push_screen(DashboardScreen())
```

### State Management Pattern
Application state is managed centrally with reactive updates:
```python
class AppState:
    """Global application state with persistence"""
    
    def __init__(self):
        self.project_loaded: bool = False
        self.models: List[DbtModel] = []
        self.metrics: List[Metric] = []
        
    def load_project(self, path: str) -> bool:
        """Load project with progress tracking"""
        # Validation, loading, service initialization
```

### Data Models
Core data structures use dataclasses with validation:
```python
@dataclass
class Metric:
    """Core metric data model"""
    name: str
    short: str
    type: str  # "direct", "ratio", "custom"
    value: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate metric configuration"""
```

## Key Features

### Metric Discovery
- Pattern matching for _value, _numerator, _denominator columns
- Smart naming suggestions based on column names
- Category inference from model names
- Confidence scoring for discovered metrics

### Supported Metric Types
1. **Direct Metrics**: Columns ending in `_value` or `_count`
2. **Ratio Metrics**: Paired `_numerator` and `_denominator` columns
3. **Custom Metrics**: Complex calculations with SQL expressions

### UI Navigation
- **F1**: Dashboard (project overview and stats)
- **F2**: Model Explorer (browse dbt models with tree view)
- **F3**: Metrics Library (manage existing metrics)
- **F4**: Discovery Wizard (find and add new metrics)
- **F5**: Settings (project configuration)
- **q**: Quit application
- **Ctrl+D**: Toggle dark/light mode

## Data Sources
1. **dbt artifacts**:
   - `target/manifest.json` - Model metadata
   - `target/catalog.json` - Column information
2. **SQL files**: `models/**/*.sql` - Model SQL definitions
3. **Seed file**: `data/metric_definitions.csv` - Existing metrics

## Development Guidelines

### When Adding New Features
1. Create data models in `models/`
2. Implement business logic in `services/`
3. Create reusable UI components in `widgets/`
4. Build screens in `screens/`
5. Add comprehensive unit and integration tests
6. Update CSS styling in `assets/app.css`

### Testing Strategy
- Unit tests for all services and data models
- Integration tests for complete workflows using Textual's test framework
- Performance tests for large datasets (1000+ models)
- Terminal compatibility tests across platforms

### Performance Considerations
- Lazy loading of expensive data
- SQLite for persistent state and history
- Efficient rendering with reactive updates
- Memory optimization with `__slots__` for data classes

## Common Tasks

### Adding a New Screen
1. Create screen class inheriting from `Screen`
2. Define `BINDINGS` for keyboard shortcuts
3. Implement `compose()` method for layout
4. Add navigation binding to main app
5. Register screen in app routing

### Adding a New Widget
1. Create widget class inheriting from appropriate base
2. Implement `compose()` for child components
3. Add event handlers for user interactions
4. Style with CSS classes
5. Add unit tests for widget behavior

### Adding a New Service
1. Create service class with clear responsibilities
2. Add error handling and validation
3. Write comprehensive unit tests
4. Integrate with appropriate state classes
5. Document public methods and usage patterns

## Prerequisites for Development
- Python 3.8+ environment
- Terminal with 256+ color support
- Understanding of Textual framework patterns
- Familiarity with dbt project structure and artifacts