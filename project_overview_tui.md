# PROJECT_OVERVIEW.md

## Project Name: DBT Metrics Manager TUI

## Executive Summary

A terminal-based application built with Textual (Python) that provides a rich text user interface for discovering, managing, and maintaining metrics from dbt rollup models. The app parses dbt artifacts (manifest.json, catalog.json) and SQL files to identify metric columns, then helps users maintain a centralized metric_definitions.csv seed file through an intuitive terminal interface.

## Core Problem

Data teams manually maintain metric definitions in CSV files by:
- Inspecting rollup models for metric columns
- Manually editing metric_definitions.csv
- Risk of missing metrics when models change
- No visual representation of metric coverage
- Difficult to validate metric configurations
- Switching between terminal and browser disrupts workflow

## Solution

A rich terminal application that:
1. Automatically discovers metrics from dbt models
2. Provides keyboard-driven TUI for metric management
3. Validates configurations in real-time
4. Exports properly formatted seed files
5. Tracks changes and provides version history
6. Integrates seamlessly into terminal-based workflows

## Technical Requirements

### Terminal Interface
- **Framework**: Textual (Python TUI framework)
- **Terminal Support**: Any terminal with 256+ colors
- **Minimum Size**: 80x24 characters (recommended: 120x30+)
- **Keyboard Navigation**: Full keyboard support with vim-like bindings
- **Accessibility**: Screen reader compatible

### Backend  
- **Language**: Python 3.8+
- **TUI Framework**: Textual (built on Rich)
- **SQL Parsing**: sqlglot library
- **Data Processing**: pandas
- **File Format**: CSV (metric_definitions.csv)
- **Storage**: SQLite for app state and history

### Data Sources
1. **dbt artifacts**:
   - `target/manifest.json` - Model metadata
   - `target/catalog.json` - Column information
2. **SQL files**: 
   - `models/**/*.sql` - Model SQL definitions
3. **Seed file**:
   - `data/metric_definitions.csv` - Existing metrics

## Core Features

### 1. Dashboard Screen
- **Purpose**: Overview of metrics and models
- **Components**:
  - Metric count card
  - Model count card  
  - Coverage percentage card
  - New metrics discovered card
  - Recent activity log
  - Quick action buttons
- **Keybindings**:
  - `d` - Discover new metrics
  - `e` - Export seed file
  - `r` - Refresh data

### 2. Model Explorer Screen
- **Purpose**: Browse and inspect dbt models
- **Layout**: 
  - Left panel: Tree view of models (30% width)
  - Right panel: Model details (70% width)
- **Features**:
  - Hierarchical folder structure
  - Search/filter models (`Ctrl+F`)
  - View model columns with types
  - Preview SQL with syntax highlighting
  - See associated metrics
  - Visual indicators for metric coverage (●/○)
- **Navigation**:
  - `j/k` - Move up/down in tree
  - `Enter` - Select model
  - `Space` - Toggle folder expansion
  - `Tab` - Switch between panels

### 3. Metric Library Screen
- **Purpose**: Manage existing metrics
- **Features**:
  - Table view of all metrics
  - Search by name, type, category (`/`)
  - Inline editing (`e`)
  - Bulk operations (`x` to select, `X` for bulk actions)
  - Category filtering
  - Sort by columns
- **Metric Properties**:
  - name: Human-readable name
  - short: Short code (e.g., "LOS_4HR")
  - type: direct, ratio, or custom
  - category: emergency, surgical, etc.
  - value/numerator/denominator: Column references
  - multiplier: For ratio calculations

### 4. Discovery Wizard Screen
- **Purpose**: Find and add new metrics
- **Process**:
  1. Scan rollup models (progress bar)
  2. Show discovered metrics in table
  3. Multi-select with checkbox column
  4. Edit properties in modal forms
  5. Bulk add to library
- **Intelligence**:
  - Pattern matching for _value, _numerator, _denominator
  - Smart naming suggestions
  - Category inference from model name
  - Confidence scoring

### 5. Settings Screen
- **Project Configuration**:
  - Project directory path browser
  - Pattern customization form
  - Naming conventions setup
- **UI Preferences**:
  - Theme selection (dark/light)
  - Items per page
  - Auto-save interval
  - Keybinding customization

## User Workflows

### Primary Workflow: Discover New Metrics
```
1. User presses F4 (Discovery) or 'd' on dashboard
2. System scans all rollup_* models (with progress bar)
3. Table shows discovered metrics not in seed
4. User navigates with j/k, selects with Space
5. User presses Enter to edit selected metric
6. Modal form opens for editing properties
7. User saves with Ctrl+S, closes with Escape
8. User presses 'a' to add selected metrics
9. Success notification appears
10. User presses 'e' to export updated seed file
```

### Secondary Workflow: Edit Existing Metric
```
1. User presses F3 to open Metric Library
2. User types '/' to search, enters query
3. User navigates to metric with j/k
4. User presses 'e' to edit
5. Modal form opens with current values
6. User updates fields with Tab navigation
7. Real-time validation shows errors
8. User saves with Ctrl+S
```

### Tertiary Workflow: Browse Models
```
1. User presses F2 to open Model Explorer
2. User navigates tree with j/k
3. User presses Space to expand folders
4. User selects model with Enter
5. Right panel shows columns and SQL
6. User sees unmapped columns highlighted
7. User presses 'm' to quick-add metric for column
```

## Metric Types

### Direct Metrics
- Pattern: `*_value`, `*_count`
- Example: `presentations_value`
- Configuration:
  ```csv
  name,short,type,value
  "ED Presentations","PRESENTATIONS","direct","presentations_value"
  ```

### Ratio Metrics  
- Pattern: `*_numerator` + `*_denominator`
- Example: `los_4_hours_numerator`, `los_4_hours_denominator`
- Configuration:
  ```csv
  name,short,type,numerator,denominator,multiplier
  "ED LOS ≤ 4 Hours Rate","LOS_4HR","ratio","los_4_hours_numerator","los_4_hours_denominator",100
  ```

### Custom Metrics
- Complex calculations
- SQL expressions
- Manual configuration

## TUI Mockups

### Dashboard Layout (120x30 terminal)
```
┌── DBT Metrics Manager ────────────────────────────────────────────────────────────────── [F1-F5] ──┐
│                                                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                                  │
│  │     156     │ │     42      │ │     12      │ │   92.3%     │                                  │
│  │   Metrics   │ │   Models    │ │    New      │ │  Coverage   │                                  │
│  │   defined   │ │    found    │ │ discovered  │ │  achieved   │                                  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘                                  │
│                                                                                                      │
│  Recent Activity                          Quick Actions                                             │
│  ┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐                 │
│  │ • Added 3 emergency metrics         │ │  [d] Discover New Metrics           │                 │
│  │ • Updated LOS_4HR definition        │ │  [e] Export Seed File               │                 │
│  │ • Archived 2 unused metrics         │ │  [r] Refresh Project Data           │                 │
│  │ • Exported metrics_definitions.csv  │ │  [F3] Open Metrics Library          │                 │
│  │ • Backup created automatically      │ │  [F5] Project Settings              │                 │
│  └─────────────────────────────────────┘ └─────────────────────────────────────┘                 │
│                                                                                                      │
│ Project: healthcare_dbt (/home/user/projects/healthcare_dbt)        Last updated: 2 minutes ago    │
│                                                                                                      │
└── F1:Dashboard F2:Models F3:Metrics F4:Discovery F5:Settings | q:Quit Ctrl+D:Dark ──────────────┘
```

### Model Explorer Layout (120x30 terminal)
```
┌── Model Explorer ────────────────────────────────────────────────────────────────────────────────┐
│ Search: emergency_exec                                                                   [Ctrl+F] │
├────────────────────────────┬─────────────────────────────────────────────────────────────────────┤
│ 📁 models/                 │ rollup_emergency_exec_emergency                                     │
│  └📁 rollup/               │                                                                     │
│   ├📄 emergency_exec    ●  │ Database: prod_dwh                                                  │
│   ├📄 surgical_exec     ●  │ Schema: marts                                                       │
│   ├📄 financial_exec    ○  │ Description: Emergency department executive rollup                  │
│   └📄 pediatric_exec    ○  │                                                                     │
│                            │ Columns (15)                                    [m] Add Metric      │
│ Legend:                    │ ┌─────────────────────────────────────────────────────────────────┐ │
│ ● Has metrics              │ │ ✓ presentations_value          │ INTEGER │ Total presentations   │ │
│ ○ No metrics               │ │ ✓ admitted_value               │ INTEGER │ Total admissions      │ │
│                            │ │ ? los_4hr_numerator            │ INTEGER │ LOS ≤ 4hrs count     │ │
│                            │ │ ? los_4hr_denominator          │ INTEGER │ Total LOS records    │ │
│                            │ │ ? lwbs_numerator               │ INTEGER │ Left without being   │ │
│                            │ │ ? lwbs_denominator             │ INTEGER │ Total presentations  │ │
│                            │ │   created_at                   │ TIMESTAMP│ Record created     │ │
│                            │ │   etl_updated                  │ TIMESTAMP│ ETL timestamp      │ │
│                            │ └─────────────────────────────────────────────────────────────────┘ │
│                            │                                                                     │
│                            │ SQL Preview                                           [Tab] Switch  │
│                            │ ┌─────────────────────────────────────────────────────────────────┐ │
│                            │ │ SELECT                                                          │ │
│                            │ │   presentations_value,                                          │ │
│                            │ │   admitted_value,                                               │ │
│                            │ │   los_4hr_numerator,                                            │ │
│                            │ │   los_4hr_denominator                                           │ │
│                            │ │ FROM {{ ref('dim_emergency') }}                                 │ │
│                            │ └─────────────────────────────────────────────────────────────────┘ │
└── j/k:Navigate Enter:Select Space:Expand Tab:Switch Panel Escape:Back ─────────────────────────┘
```

### Metrics Library Layout (120x30 terminal)
```
┌── Metrics Library ───────────────────────────────────────────────────────────────────────────────┐
│ Search: /los                              Filter: [All Categories ▼] [All Types ▼]    [156 total] │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│☐│Name                     │Short    │Type  │Category  │Source Model         │Updated     │Actions│
├─┼─────────────────────────┼─────────┼──────┼──────────┼─────────────────────┼────────────┼───────┤
│☐│ED LOS ≤ 4 Hours Rate    │LOS_4HR  │ratio │emergency │rollup_emergency_exec│2024-01-15  │ [e]   │
│☐│ED LOS Average Minutes   │LOS_AVG  │direct│emergency │rollup_emergency_exec│2024-01-15  │ [e]   │
│☐│Surgery LOS Median Days  │SLOS_MED │direct│surgical  │rollup_surgical_exec │2024-01-12  │ [e]   │
│☐│ICU LOS ≤ 2 Days Rate    │ILOS_2D  │ratio │surgical  │rollup_surgical_exec │2024-01-12  │ [e]   │
│☐│ED Presentations Total   │ED_PRES  │direct│emergency │rollup_emergency_exec│2024-01-10  │ [e]   │
│☐│Surgery Complications    │SURG_COMP│direct│surgical  │rollup_surgical_exec │2024-01-10  │ [e]   │
│☐│Financial Revenue Daily  │FIN_REV  │direct│financial │rollup_financial_exec│2024-01-08  │ [e]   │
│☐│Cost Per Case Average    │COST_CASE│ratio │financial │rollup_financial_exec│2024-01-08  │ [e]   │
│ │                         │         │      │          │                     │            │       │
│ │                         │         │      │          │                     │            │       │
│ │                         │         │      │          │                     │            │       │
│ │                         │         │      │          │                     │            │       │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ x:Select X:Bulk Actions e:Edit d:Delete n:New Metric /:Search                     Page 1 of 8     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Discovery Wizard Layout (120x30 terminal)
```
┌── Discovery Wizard ──────────────────────────────────────────────────────────────────────────────┐
│ Step 2 of 3: Review Discovered Metrics                                              [12 found]     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│☑│Confidence│Suggested Name              │Short     │Type  │Model                │Column          │
├─┼──────────┼────────────────────────────┼──────────┼──────┼─────────────────────┼────────────────┤
│☑│   95%    │ED LWBS Rate                │LWBS_RATE │ratio │rollup_emergency_exec│lwbs_numerator  │
│☑│   95%    │ED LWBS Rate                │LWBS_RATE │ratio │rollup_emergency_exec│lwbs_denominator│
│☑│   90%    │Surgery Case Volume         │SURG_VOL  │direct│rollup_surgical_exec │cases_value     │
│☑│   85%    │ICU Occupancy Rate          │ICU_OCC   │ratio │rollup_surgical_exec │icu_numerator   │
│☑│   85%    │ICU Occupancy Rate          │ICU_OCC   │ratio │rollup_surgical_exec │icu_denominator │
│☐│   80%    │Readmission Rate            │READM_RT  │ratio │rollup_surgical_exec │readm_numerator │
│☐│   80%    │Readmission Rate            │READM_RT  │ratio │rollup_surgical_exec │readm_denomin..│
│☐│   75%    │Revenue Per Patient         │REV_PAT   │direct│rollup_financial_exec│revenue_per_pat │
│☐│   70%    │Cost Efficiency Ratio       │COST_EFF  │ratio │rollup_financial_exec│cost_numerator  │
│☐│   70%    │Cost Efficiency Ratio       │COST_EFF  │ratio │rollup_financial_exec│cost_denomin... │
│ │          │                            │          │      │                     │                │
│ │          │                            │          │      │                     │                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Space:Toggle e:Edit Selected Enter:Edit Current a:Add Selected n:Next p:Previous Escape:Cancel    │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Success Metrics

1. **Adoption**: 90% of team uses TUI vs manual CSV editing
2. **Efficiency**: 75% reduction in metric management time  
3. **Accuracy**: 95% fewer configuration errors
4. **Performance**: Screen transitions under 100ms
5. **Coverage**: 100% of rollup models have metrics defined
6. **Usability**: Zero training needed for basic navigation

## Non-Functional Requirements

### Performance
- Launch under 2 seconds
- Search results instant (<50ms)
- Support projects with 1000+ models
- Handle seed files with 10,000+ metrics
- Memory usage under 100MB

### Usability
- Vim-like navigation for power users
- Context-sensitive help (F1)
- Undo/redo functionality
- Auto-save with recovery
- Keyboard shortcuts discoverable

### Reliability
- Graceful error handling with helpful messages
- Automatic backups before changes
- Data validation with inline feedback
- No data loss on crashes
- Graceful degradation with incomplete data

### Terminal Compatibility
- Works in any ANSI-compatible terminal
- Supports SSH sessions
- Responsive to terminal resizing
- Compatible with tmux/screen
- Works over low-bandwidth connections

## Constraints

1. Must work with existing dbt project structure
2. Cannot modify source dbt files
3. Must preserve seed file format
4. Requires `dbt docs generate` to be run
5. Terminal-only interface (no GUI fallback)
6. Single-user application initially
7. Must work over SSH connections

## Installation & Distribution

### Package Installation
```bash
# Install from PyPI
pip install dbt-metrics-manager

# Run the application
dbt-metrics

# Or run in project directory
cd /path/to/dbt/project
dbt-metrics
```

### Development Installation
```bash
# Clone repository
git clone https://github.com/org/dbt-metrics-manager-tui
cd dbt-metrics-manager-tui

# Install in development mode
pip install -e .

# Run tests
pytest
```

### System Requirements
- Python 3.8+
- Terminal with 256+ color support
- Minimum 80x24 terminal size
- 50MB disk space
- 100MB RAM

## Future Enhancements

### Phase 2 Features
1. **Git Integration**: Track changes with git commits
2. **Plugin System**: Custom metric discovery patterns
3. **Export Formats**: JSON, YAML, Parquet outputs
4. **Metric Testing**: Preview calculations with sample data
5. **Templates**: Reusable metric configuration templates

### Phase 3 Features
1. **Multi-Project**: Manage multiple dbt projects
2. **Collaboration**: Share configurations via git
3. **CI/CD**: Command-line automation scripts
4. **Cloud Sync**: Backup to cloud storage
5. **Advanced Analytics**: Usage tracking and optimization

### Advanced Terminal Features
1. **Mouse Support**: Optional mouse navigation
2. **Custom Themes**: User-defined color schemes
3. **Layout Customization**: Configurable panel sizes
4. **Macro System**: Record and replay key sequences
5. **Terminal Multiplexing**: Integration with tmux/screen

## Competitive Advantages

1. **Workflow Integration**: Seamless terminal-based workflow
2. **Speed**: Instant startup and navigation
3. **Resource Efficiency**: Minimal memory and CPU usage
4. **SSH Friendly**: Works perfectly over remote connections
5. **Keyboard Driven**: Power user optimized
6. **Offline Capable**: No internet connection required
7. **Cross Platform**: Works on Linux, macOS, Windows terminals