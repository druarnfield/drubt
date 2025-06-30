# DBT Metrics Manager TUI

A terminal user interface for discovering and managing metrics from dbt rollup models.

## Phase 1 Implementation Complete ✅

This implementation includes:

- **Project Structure**: Complete directory structure with all modules
- **Core Data Models**: `Metric` and `DbtModel` classes with validation
- **State Management**: `AppState` class with SQLite persistence
- **DBT Integration**: `DbtReader` service for parsing dbt artifacts
- **Basic TUI**: Dashboard and Settings screens with Textual framework
- **Configuration**: JSON-based config system with defaults
- **Testing**: Unit tests for core functionality

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Usage

```bash
# Run the application
python -m dbt_metrics_manager.app

# Or if installed as package
dbt-metrics
```

## Quick Start

1. **Prepare your dbt project**:
   ```bash
   cd /path/to/your/dbt/project
   dbt docs generate  # Generates manifest.json and catalog.json
   ```

2. **Launch the TUI**:
   ```bash
   dbt-metrics
   ```

3. **Configure project**:
   - Press F5 to open Settings
   - Browse or enter your dbt project path
   - Click "Load Project" to import rollup models

## Navigation

- **F1**: Dashboard (project overview and stats)
- **F5**: Settings (project configuration)
- **q**: Quit application
- **Ctrl+D**: Toggle dark/light mode
- **Ctrl+H**: Show help
- **r**: Refresh data (when on dashboard)
- **Escape**: Go back/cancel
- **Tab**: Move focus between panels

## Features Implemented

### ✅ Project Management
- Load and validate dbt projects
- Browse directory tree to select projects
- Recent projects history
- Project validation with helpful error messages

### ✅ Dashboard
- Project overview with statistics
- Stats cards showing metrics, models, and coverage
- Recent activity log
- Quick action buttons

### ✅ Settings
- Project path configuration
- Directory browser
- Recent projects list
- Validation and loading controls

### ✅ Data Models
- `Metric` class with validation for direct, ratio, and custom types
- `DbtModel` class with column information and rollup detection
- Serialization to/from dictionaries for persistence

### ✅ DBT Integration
- Parse `manifest.json` and `catalog.json` artifacts
- Extract rollup models (models starting with "rollup_")
- Combine manifest and catalog data for complete model information
- Column-level metadata extraction

## Testing

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run specific test
python -m pytest tests/unit/test_metric.py -v
```

## Project Structure

```
dbt_metrics_manager/
├── app.py                     # Main Textual application
├── config.py                  # Configuration management
├── models/                    # Data models
│   ├── metric.py              # Metric dataclass
│   └── dbt_model.py           # DBT model dataclass
├── state/                     # State management
│   └── app_state.py           # Global application state
├── services/                  # Business logic
│   └── dbt_reader.py          # DBT artifact parsing
├── screens/                   # UI screens
│   ├── dashboard.py           # Main dashboard
│   └── settings.py            # Project settings
├── widgets/                   # UI components
│   └── stats_cards.py         # Statistics cards
├── utils/                     # Utilities
│   └── constants.py           # Application constants
└── assets/
    └── app.css                # Textual CSS styles
```

## Next Steps (Phase 2)

The foundation is now complete. Phase 2 would add:

1. **Model Explorer**: Tree view of models with column details
2. **Metric Discovery**: Automatic pattern matching for metrics
3. **Metric Library**: CRUD operations for existing metrics
4. **Seed File Management**: Read/write metric_definitions.csv
5. **Advanced Widgets**: Forms, tables, and data entry components

## Technical Notes

- Uses Textual 0.45+ for the terminal interface
- SQLite for local persistence of settings and history
- JSON configuration with user-friendly defaults
- Comprehensive error handling and validation
- Modular architecture for easy extension

## Requirements

- Python 3.8+
- Terminal with 256+ color support
- dbt project with generated artifacts (manifest.json)

## Contributing

1. Install development dependencies
2. Run tests to ensure everything works
3. Make changes following the existing patterns
4. Add tests for new functionality
5. Update documentation as needed