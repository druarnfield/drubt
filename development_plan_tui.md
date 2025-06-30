# DEVELOPMENT_PLAN.md

## Project Timeline

### Phase 1: Foundation (Week 1-2)
- TUI app setup with Textual
- Basic screen navigation
- State management foundation
- DBT metadata parsing

### Phase 2: Core Features (Week 3-4)
- Model explorer interface
- Metric discovery engine
- Basic CRUD operations
- Seed file management

### Phase 3: UI Polish (Week 5-6)
- Advanced widgets and forms
- Keyboard shortcuts and navigation
- Real-time validation
- Progress indicators

### Phase 4: Testing & Distribution (Week 7-8)
- Comprehensive testing
- Performance optimization
- Package distribution
- Documentation

## Implementation Order

### Step 1: Project Setup

#### 1.1 Initialize Project
```bash
# Commands to run
mkdir dbt-metrics-manager-tui
cd dbt-metrics-manager-tui
python -m venv venv
source venv/bin/activate
pip install textual rich pandas sqlglot pyyaml
textual --version  # Verify installation
```

#### 1.2 Create Directory Structure
```python
# Create all directories from ARCHITECTURE.md
directories = [
    "dbt_metrics_manager/state",
    "dbt_metrics_manager/screens", 
    "dbt_metrics_manager/widgets",
    "dbt_metrics_manager/services",
    "dbt_metrics_manager/models",
    "dbt_metrics_manager/utils",
    "dbt_metrics_manager/assets",
    "tests/unit",
    "tests/integration", 
    "tests/fixtures"
]
```

#### 1.3 Basic App Structure
```python
# dbt_metrics_manager/app.py - Minimal working app
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class DbtMetricsManagerApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("DBT Metrics Manager TUI")
        yield Footer()

if __name__ == "__main__":
    DbtMetricsManagerApp().run()
```

### Step 2: Data Models Implementation

#### 2.1 Create Base Models
```python
# Priority order for models:
1. models/metric.py - Core metric data structure
2. models/dbt_model.py - DBT model representation
3. models/discovery_result.py - Discovery results
```

#### 2.2 Model Implementation Pattern
```python
# models/metric.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Metric:
    """Core metric data model"""
    
    # Required fields
    metric_category: str
    name: str
    short: str
    type: str  # "direct", "ratio", "custom"
    
    # Type-specific fields
    value: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    expression: Optional[str] = None
    
    # Optional metadata
    multiplier: Optional[int] = None
    description: Optional[str] = None
    source_model: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamps on creation"""
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export"""
        return {
            "metric_category": self.metric_category,
            "name": self.name,
            "short": self.short,
            "type": self.type,
            "value": self.value or "",
            "numerator": self.numerator or "",
            "denominator": self.denominator or "",
            "expression": self.expression or "",
            "multiplier": self.multiplier or "",
            "description": self.description or "",
            "source_model": self.source_model or "",
            "tags": ",".join(self.tags) if self.tags else ""
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create from dictionary"""
        tags = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
        
        return cls(
            metric_category=data["metric_category"],
            name=data["name"],
            short=data["short"],
            type=data["type"],
            value=data.get("value") or None,
            numerator=data.get("numerator") or None,
            denominator=data.get("denominator") or None,
            expression=data.get("expression") or None,
            multiplier=int(data["multiplier"]) if data.get("multiplier") else None,
            description=data.get("description") or None,
            source_model=data.get("source_model") or None,
            tags=tags
        )
    
    def validate(self) -> List[str]:
        """Validate metric configuration"""
        errors = []
        
        if not self.name.strip():
            errors.append("Name is required")
        
        if not self.short.strip():
            errors.append("Short code is required")
        
        if self.type not in ["direct", "ratio", "custom"]:
            errors.append("Type must be direct, ratio, or custom")
        
        if self.type == "direct" and not self.value:
            errors.append("Direct metrics require a value column")
        
        if self.type == "ratio" and (not self.numerator or not self.denominator):
            errors.append("Ratio metrics require numerator and denominator")
        
        if self.type == "custom" and not self.expression:
            errors.append("Custom metrics require an expression")
        
        return errors
```

### Step 3: Services Layer

#### 3.1 DBT Reader Service (Priority 1)
```python
# services/dbt_reader.py - Core functionality first
class DbtReader:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.manifest_path = self.project_path / "target" / "manifest.json"
        self.catalog_path = self.project_path / "target" / "catalog.json"
    
    def validate_project(self) -> tuple[bool, str]:
        """Essential validation logic"""
        if not self.project_path.exists():
            return False, "Project path does not exist"
        
        if not self.manifest_path.exists():
            return False, "manifest.json not found. Run 'dbt docs generate' first."
        
        return True, "Project is valid"
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load manifest with error handling"""
        try:
            with open(self.manifest_path) as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load manifest.json: {e}")
    
    def get_rollup_models(self) -> List[DbtModel]:
        """Get rollup models from manifest"""
        manifest = self.load_manifest()
        models = []
        
        for node_id, node in manifest.get("nodes", {}).items():
            if (node.get("resource_type") == "model" and 
                node.get("name", "").startswith("rollup_")):
                
                model = DbtModel(
                    unique_id=node_id,
                    name=node["name"],
                    database=node.get("database", ""),
                    schema=node.get("schema", ""),
                    alias=node.get("alias"),
                    description=node.get("description"),
                    tags=node.get("tags", []),
                    original_file_path=node.get("original_file_path")
                )
                models.append(model)
        
        return models
```

#### 3.2 Metric Analyzer Service (Priority 2)
```python
# services/metric_analyzer.py - Pattern matching logic
class MetricAnalyzer:
    def __init__(self, patterns: Optional[Dict] = None):
        self.patterns = patterns or {
            "direct_value": r".*_value$",
            "direct_count": r".*_count$",
            "ratio_numerator": r".*_numerator$",
            "ratio_denominator": r".*_denominator$",
        }
    
    def analyze_model(self, model: DbtModel) -> DiscoveryResult:
        """Main analysis method"""
        columns = self._get_model_columns(model)
        metrics = self.analyze_columns(columns, model.name)
        
        return DiscoveryResult(
            model_name=model.name,
            model_id=model.unique_id,
            discovered_metrics=metrics,
            total_columns=len(columns),
            analyzed_columns=len([c for c in columns if self._is_metric_column(c)]),
            confidence_scores={m.short: self._calculate_confidence(m) for m in metrics}
        )
    
    def analyze_columns(self, columns: List[str], model_name: str) -> List[Metric]:
        """Analyze columns for metric patterns"""
        metrics = []
        
        # Find direct metrics
        for column in columns:
            if re.match(self.patterns["direct_value"], column):
                metric = self._create_direct_metric(column, model_name, "value")
                metrics.append(metric)
            elif re.match(self.patterns["direct_count"], column):
                metric = self._create_direct_metric(column, model_name, "count")
                metrics.append(metric)
        
        # Find ratio pairs
        ratio_pairs = self._find_ratio_pairs(columns)
        for numerator, denominator in ratio_pairs:
            metric = self._create_ratio_metric(numerator, denominator, model_name)
            metrics.append(metric)
        
        return metrics
```

#### 3.3 Seed Manager Service (Priority 3)
```python
# services/seed_manager.py - File operations
class SeedManager:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.seed_path = self.project_path / "data" / "metric_definitions.csv"
        self.backup_dir = self.project_path / "data" / ".backups"
    
    def read_metrics(self) -> List[Metric]:
        """Read metrics from CSV with pandas"""
        if not self.seed_path.exists():
            return []
        
        try:
            df = pd.read_csv(self.seed_path)
            return [Metric.from_dict(row.to_dict()) for _, row in df.iterrows()]
        except Exception as e:
            raise Exception(f"Failed to read metrics CSV: {e}")
    
    def write_metrics(self, metrics: List[Metric]) -> None:
        """Write metrics to CSV with backup"""
        # Create backup first
        if self.seed_path.exists():
            self.create_backup()
        
        # Convert to DataFrame
        data = [metric.to_dict() for metric in metrics]
        df = pd.DataFrame(data)
        
        # Ensure data directory exists
        self.seed_path.parent.mkdir(exist_ok=True)
        
        # Write CSV
        df.to_csv(self.seed_path, index=False)
```

### Step 4: State Management

#### 4.1 App State (Priority 1)
```python
# state/app_state.py - Central state management
class AppState:
    """Global application state"""
    
    def __init__(self):
        self.config = get_config()
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
        self.success_message: str = ""
        
        # Services (lazy loaded)
        self._dbt_reader: Optional[DbtReader] = None
        self._analyzer: Optional[MetricAnalyzer] = None
        self._seed_manager: Optional[SeedManager] = None
    
    def load_project(self, path: str) -> bool:
        """Load project with progress tracking"""
        try:
            self.loading = True
            self.error_message = ""
            
            # Step 1: Validate
            self.loading_message = "Validating project..."
            self._dbt_reader = DbtReader(path)
            valid, message = self._dbt_reader.validate_project()
            
            if not valid:
                self.error_message = message
                return False
            
            # Step 2: Load models
            self.loading_message = "Loading models..."
            self.models = self._dbt_reader.get_rollup_models()
            
            # Step 3: Load existing metrics
            self.loading_message = "Loading existing metrics..."
            self._seed_manager = SeedManager(path)
            self.metrics = self._seed_manager.read_metrics()
            
            # Step 4: Initialize services
            self.loading_message = "Initializing services..."
            self._analyzer = MetricAnalyzer()
            
            # Update state
            self.project_path = path
            self.project_name = self._dbt_reader.get_project_name()
            self.project_loaded = True
            
            self.success_message = f"Loaded project: {self.project_name}"
            return True
            
        except Exception as e:
            self.error_message = str(e)
            return False
        finally:
            self.loading = False
            self.loading_message = ""
    
    # Properties for computed values
    @property
    def total_metrics(self) -> int:
        return len(self.metrics)
    
    @property
    def total_models(self) -> int:
        return len(self.models)
    
    @property
    def coverage_percentage(self) -> float:
        if not self.models:
            return 0.0
        models_with_metrics = len({m.source_model for m in self.metrics if m.source_model})
        return (models_with_metrics / len(self.models)) * 100
```

### Step 5: Textual Screens

#### 5.1 Dashboard Screen (Priority 1)
```python
# screens/dashboard.py - Main entry screen
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding

class DashboardScreen(Screen):
    """Main dashboard screen"""
    
    BINDINGS = [
        Binding("d", "discover", "Discover"),
        Binding("e", "export", "Export"),
        Binding("r", "refresh", "Refresh"),
        Binding("f2", "models", "Models"),
        Binding("f3", "metrics", "Metrics"),
        Binding("f4", "discovery", "Discovery"),
        Binding("f5", "settings", "Settings"),
    ]
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
    
    def compose(self) -> ComposeResult:
        """Create dashboard layout"""
        yield Header()
        
        if self.app_state.project_loaded:
            yield Container(
                self._create_stats_section(),
                self._create_content_section(),
                self._create_actions_section(),
                classes="dashboard-container"
            )
        else:
            yield Container(
                Static("Welcome to DBT Metrics Manager", classes="welcome-title"),
                Static("Press F5 to configure a project", classes="welcome-subtitle"),
                Button("Select Project", id="select-project"),
                classes="welcome-container"
            )
        
        yield Footer()
    
    def _create_stats_section(self) -> Container:
        """Create statistics cards section"""
        return Container(
            Horizontal(
                Static(f"{self.app_state.total_metrics}\nMetrics", classes="stat-card"),
                Static(f"{self.app_state.total_models}\nModels", classes="stat-card"),
                Static(f"{self.app_state.coverage_percentage:.1f}%\nCoverage", classes="stat-card"),
                Static(f"{len(self.app_state.discovered_metrics)}\nDiscovered", classes="stat-card"),
                classes="stats-row"
            ),
            classes="stats-section"
        )
    
    def _create_content_section(self) -> Container:
        """Create main content section"""
        return Container(
            Horizontal(
                self._create_activity_panel(),
                self._create_actions_panel(),
                classes="content-row"
            ),
            classes="content-section"
        )
    
    def _create_activity_panel(self) -> Container:
        """Create recent activity panel"""
        return Container(
            Static("Recent Activity", classes="panel-title"),
            Static("• Project loaded successfully\n• Found 12 new metrics\n• 42 models analyzed", 
                   classes="activity-list"),
            classes="activity-panel"
        )
    
    def _create_actions_panel(self) -> Container:
        """Create quick actions panel"""
        return Container(
            Static("Quick Actions", classes="panel-title"),
            Button("Discover New Metrics [d]", id="discover-btn"),
            Button("Export Seed File [e]", id="export-btn"),
            Button("Open Metrics Library [F3]", id="metrics-btn"),
            classes="actions-panel"
        )
    
    # Action handlers
    def action_discover(self) -> None:
        """Start metric discovery"""
        self.app.push_screen("discovery")
    
    def action_export(self) -> None:
        """Export seed file"""
        if self.app_state._seed_manager:
            self.app_state._seed_manager.write_metrics(self.app_state.metrics)
            self.notify("Seed file exported successfully")
    
    def action_refresh(self) -> None:
        """Refresh project data"""
        if self.app_state.project_loaded:
            self.app_state.load_project(self.app_state.project_path)
            self.refresh()
    
    def action_models(self) -> None:
        """Open models screen"""
        self.app.push_screen("models")
    
    def action_metrics(self) -> None:
        """Open metrics screen"""
        self.app.push_screen("metrics")
    
    def action_discovery(self) -> None:
        """Open discovery screen"""
        self.app.push_screen("discovery")
    
    def action_settings(self) -> None:
        """Open settings screen"""
        self.app.push_screen("settings")
```

#### 5.2 Model Explorer Screen (Priority 2)
```python
# screens/models.py - File browser interface
from textual.widgets import Input, Tree, DataTable
from textual.containers import Horizontal, Vertical

class ModelsScreen(Screen):
    """Model explorer with tree and details"""
    
    BINDINGS = [
        Binding("ctrl+f", "focus_search", "Search"),
        Binding("tab", "switch_focus", "Switch Panel"),
        Binding("escape", "back", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        yield Horizontal(
            # Left panel - Tree view
            Vertical(
                Input(placeholder="Search models...", id="model-search"),
                Tree("Models", id="model-tree"),
                classes="sidebar"
            ),
            
            # Right panel - Details
            Vertical(
                Static("Model Details", classes="panel-title"),
                DataTable(id="columns-table"),
                Static("SQL Preview", classes="panel-title"),
                Static("", id="sql-preview", classes="sql-preview"),
                classes="details-panel"
            ),
            classes="main-layout"
        )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize tree on mount"""
        self._populate_tree()
    
    def _populate_tree(self) -> None:
        """Populate model tree"""
        tree = self.query_one("#model-tree", Tree)
        
        # Group models by folder
        folders = {}
        for model in self.app_state.models:
            if model.original_file_path:
                folder = "/".join(model.original_file_path.split("/")[:-1])
            else:
                folder = "unknown"
            
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(model)
        
        # Add folders and models to tree
        for folder, models in folders.items():
            folder_node = tree.root.add(folder, expand=True)
            
            for model in models:
                # Visual indicator for metrics
                has_metrics = any(m.source_model == model.name for m in self.app_state.metrics)
                icon = "●" if has_metrics else "○"
                folder_node.add_leaf(f"{icon} {model.name}", data=model)
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle model selection"""
        if hasattr(event.node, 'data') and event.node.data:
            self._show_model_details(event.node.data)
    
    def _show_model_details(self, model: DbtModel) -> None:
        """Show model details in right panel"""
        # Update columns table
        table = self.query_one("#columns-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Column", "Type", "Description")
        
        for column in model.columns or []:
            table.add_row(
                column.name,
                column.data_type or "unknown",
                column.description or ""
            )
        
        # Update SQL preview
        sql_preview = self.query_one("#sql-preview")
        if model.raw_sql:
            sql_preview.update(model.raw_sql[:500] + "..." if len(model.raw_sql) > 500 else model.raw_sql)
```

### Step 6: Textual Widgets

#### 6.1 Data Table Widget (Priority 1)
```python
# widgets/data_table.py - Enhanced table component
from textual.widgets import DataTable
from textual.coordinate import Coordinate

class InteractiveDataTable(DataTable):
    """Enhanced data table with selection and actions"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_rows = set()
        self.selectable = kwargs.get('selectable', False)
    
    def add_data(self, data: List[Dict[str, Any]], columns: List[str]):
        """Add data to table"""
        # Clear existing data
        self.clear(columns=True)
        
        # Add selection column if selectable
        if self.selectable:
            self.add_column("☐", key="select", width=3)
        
        # Add data columns
        for col in columns:
            self.add_column(col, key=col)
        
        # Add rows
        for i, row in enumerate(data):
            row_data = []
            
            if self.selectable:
                checkbox = "☑" if str(i) in self.selected_rows else "☐"
                row_data.append(checkbox)
            
            for col in columns:
                row_data.append(str(row.get(col, "")))
            
            self.add_row(*row_data, key=str(i))
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection"""
        if self.selectable and event.coordinate.column == 0:
            # Toggle selection
            row_key = event.row_key.value
            if row_key in self.selected_rows:
                self.selected_rows.remove(row_key)
                self.update_cell(event.coordinate, "☐")
            else:
                self.selected_rows.add(row_key)
                self.update_cell(event.coordinate, "☑")
```

#### 6.2 Form Widgets (Priority 2)
```python
# widgets/forms.py - Form components
from textual.widgets import Input, Select, TextArea
from textual.containers import Container, Horizontal, Vertical
from textual.validation import Function

class MetricForm(Container):
    """Form for editing metrics"""
    
    def __init__(self, metric: Optional[Metric] = None, **kwargs):
        super().__init__(**kwargs)
        self.metric = metric
        self.errors = {}
    
    def compose(self) -> ComposeResult:
        yield Vertical(
            Horizontal(
                Input(
                    placeholder="Metric Name",
                    value=self.metric.name if self.metric else "",
                    id="name-input",
                    validators=[Function(self._validate_name, "Name is required")]
                ),
                Input(
                    placeholder="Short Code",
                    value=self.metric.short if self.metric else "",
                    id="short-input",
                    validators=[Function(self._validate_short, "Short code is required")]
                ),
                classes="form-row"
            ),
            
            Select([
                ("Direct", "direct"),
                ("Ratio", "ratio"),
                ("Custom", "custom")
            ], 
            value=self.metric.type if self.metric else "direct",
            id="type-select"),
            
            # Conditional fields based on type
            self._create_conditional_fields(),
            
            Horizontal(
                Button("Save", id="save-btn", variant="primary"),
                Button("Cancel", id="cancel-btn"),
                classes="form-actions"
            ),
            
            classes="metric-form"
        )
    
    def _validate_name(self, value: str) -> bool:
        """Validate metric name"""
        return bool(value.strip())
    
    def _validate_short(self, value: str) -> bool:
        """Validate short code"""
        return bool(value.strip()) and len(value) <= 20
    
    def get_form_data(self) -> Dict[str, str]:
        """Extract form data"""
        return {
            "name": self.query_one("#name-input", Input).value,
            "short": self.query_one("#short-input", Input).value,
            "type": self.query_one("#type-select", Select).value,
            # ... other fields
        }
```

### Step 7: CSS Styling

#### 7.1 Main CSS File (assets/app.css)
```css
/* Terminal-optimized color scheme */
Screen {
    background: $background;
}

.dashboard-container {
    margin: 1;
    height: 100%;
}

.stats-row {
    height: 5;
    margin: 1 0;
}

.stat-card {
    background: $surface;
    border: solid $primary;
    border-title-color: $primary;
    padding: 1;
    margin: 0 1;
    text-align: center;
    content-align: center middle;
}

.sidebar {
    width: 30%;
    border: solid $secondary;
    margin: 0 1 0 0;
}

.details-panel {
    width: 70%;
    border: solid $secondary;
}

.panel-title {
    background: $primary;
    color: $text-primary;
    padding: 0 1;
    text-style: bold;
}

.welcome-container {
    align: center middle;
    text-align: center;
}

.welcome-title {
    text-style: bold;
    color: $primary;
    margin: 1;
}

.activity-panel, .actions-panel {
    border: solid $secondary;
    margin: 0 1;
    padding: 1;
}

.sql-preview {
    background: $surface;
    color: $text-secondary;
    padding: 1;
    border: solid $accent;
}

/* Data table styling */
DataTable {
    background: $background;
}

DataTable > .datatable--header {
    background: $primary;
    color: $text-primary;
    text-style: bold;
}

DataTable > .datatable--odd-row {
    background: $surface;
}

DataTable > .datatable--cursor {
    background: $accent;
    color: $text-primary;
}

/* Form styling */
.metric-form {
    background: $surface;
    border: solid $primary;
    padding: 1;
    margin: 1;
}

.form-row {
    height: 3;
    margin: 0 0 1 0;
}

.form-actions {
    justify: center;
    margin: 1 0 0 0;
}

Input {
    margin: 0 1 0 0;
}

Button {
    margin: 0 1;
}

/* Loading and status */
.loading-spinner {
    align: center middle;
}

.error-message {
    background: $error;
    color: $text-primary;
    padding: 1;
    margin: 1;
}

.success-message {
    background: $success;
    color: $text-primary;
    padding: 1;
    margin: 1;
}
```

### Step 8: Testing Strategy

#### 8.1 Unit Tests
```python
# tests/unit/test_metric_analyzer.py
import pytest
from dbt_metrics_manager.services import MetricAnalyzer
from dbt_metrics_manager.models import DbtModel

@pytest.fixture
def analyzer():
    return MetricAnalyzer()

@pytest.fixture
def sample_columns():
    return [
        "id",
        "presentations_value", 
        "los_4hr_numerator",
        "los_4hr_denominator",
        "created_at"
    ]

def test_identify_direct_metrics(analyzer, sample_columns):
    """Test direct metric identification"""
    metrics = analyzer.analyze_columns(sample_columns, "test_model")
    
    direct_metrics = [m for m in metrics if m.type == "direct"]
    assert len(direct_metrics) == 1
    assert direct_metrics[0].value == "presentations_value"

def test_find_ratio_pairs(analyzer, sample_columns):
    """Test ratio pair detection"""
    metrics = analyzer.analyze_columns(sample_columns, "test_model")
    
    ratio_metrics = [m for m in metrics if m.type == "ratio"]
    assert len(ratio_metrics) == 1
    assert ratio_metrics[0].numerator == "los_4hr_numerator"
    assert ratio_metrics[0].denominator == "los_4hr_denominator"

def test_ignore_system_columns(analyzer):
    """Test that system columns are ignored"""
    system_columns = ["id", "created_at", "updated_at", "_fivetran_synced"]
    metrics = analyzer.analyze_columns(system_columns, "test_model")
    assert len(metrics) == 0
```

#### 8.2 Integration Tests with Textual
```python
# tests/integration/test_app_navigation.py
import pytest
from textual.pilot import Pilot
from dbt_metrics_manager.app import DbtMetricsManagerApp

@pytest.mark.asyncio
async def test_screen_navigation():
    """Test navigating between screens"""
    app = DbtMetricsManagerApp()
    
    async with app.run_test() as pilot:
        # Start on dashboard
        assert app.screen.__class__.__name__ == "DashboardScreen"
        
        # Navigate to models
        await pilot.press("f2")
        assert app.screen.__class__.__name__ == "ModelsScreen"
        
        # Navigate to metrics
        await pilot.press("f3")
        assert app.screen.__class__.__name__ == "MetricsScreen"
        
        # Go back to dashboard
        await pilot.press("f1")
        assert app.screen.__class__.__name__ == "DashboardScreen"

@pytest.mark.asyncio
async def test_project_loading():
    """Test project loading workflow"""
    app = DbtMetricsManagerApp()
    
    async with app.run_test() as pilot:
        # Open settings
        await pilot.press("f5")
        
        # Enter project path (would need test fixtures)
        # Test loading process
        # Verify data is loaded
        pass

@pytest.mark.asyncio
async def test_metric_discovery():
    """Test metric discovery workflow"""
    app = DbtMetricsManagerApp()
    
    async with app.run_test() as pilot:
        # Assuming project is loaded
        
        # Press 'd' to start discovery
        await pilot.press("d")
        
        # Should navigate to discovery screen
        assert app.screen.__class__.__name__ == "DiscoveryScreen"
        
        # Test discovery process
        # Test metric selection
        # Test adding metrics
        pass
```

#### 8.3 Performance Tests
```python
# tests/performance/test_large_datasets.py
import pytest
import time
from dbt_metrics_manager.services import MetricAnalyzer

def test_analyze_large_model_set():
    """Test performance with large number of models"""
    analyzer = MetricAnalyzer()
    
    # Create 1000 mock models
    large_column_set = [f"metric_{i}_value" for i in range(1000)]
    
    start_time = time.time()
    metrics = analyzer.analyze_columns(large_column_set, "large_model")
    end_time = time.time()
    
    # Should complete in under 1 second
    assert end_time - start_time < 1.0
    assert len(metrics) == 1000

def test_app_startup_time():
    """Test app startup performance"""
    start_time = time.time()
    
    app = DbtMetricsManagerApp()
    # Don't actually run the app, just test initialization
    
    end_time = time.time()
    
    # Should initialize in under 100ms
    assert end_time - start_time < 0.1
```

### Step 9: Packaging and Distribution

#### 9.1 Setup Configuration
```python
# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dbt-metrics-manager",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Terminal UI for managing DBT metrics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dbt-metrics-manager-tui",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
        "Topic :: Software Development :: User Interfaces",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dbt-metrics=dbt_metrics_manager.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "dbt_metrics_manager": ["assets/*.css", "assets/*.toml"],
    },
)
```

#### 9.2 CI/CD Pipeline (.github/workflows/test-and-release.yml)
```yaml
name: Test and Release

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=dbt_metrics_manager
    
    - name: Run linting
      run: |
        black --check dbt_metrics_manager/
        flake8 dbt_metrics_manager/
    
    - name: Test CLI installation
      run: |
        pip install -e .
        dbt-metrics --help

  release:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.9
    
    - name: Build package
      run: |
        python -m pip install --upgrade pip build
        python -m build
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

### Step 10: Documentation

#### 10.1 User Guide (README.md)
```markdown
# DBT Metrics Manager TUI

A terminal user interface for discovering and managing metrics from dbt rollup models.

## Installation

```bash
pip install dbt-metrics-manager
```

## Quick Start

```bash
# Navigate to your dbt project
cd /path/to/your/dbt/project

# Ensure dbt artifacts are generated
dbt docs generate

# Launch the TUI
dbt-metrics
```

## Navigation

- **F1**: Dashboard
- **F2**: Model Explorer  
- **F3**: Metrics Library
- **F4**: Discovery Wizard
- **F5**: Settings
- **q**: Quit
- **Ctrl+D**: Toggle dark mode

## Features

- 🔍 **Auto-discovery** of metrics from rollup models
- 📊 **Visual coverage** tracking
- ⌨️ **Keyboard-driven** interface
- 🔄 **Real-time validation**
- 💾 **Automatic backups**
- 🎨 **Terminal themes**

## Metric Types

### Direct Metrics
Columns ending in `_value` or `_count`:
```
presentations_value → "ED Presentations"
```

### Ratio Metrics  
Paired `_numerator` and `_denominator` columns:
```
los_4hr_numerator + los_4hr_denominator → "ED LOS ≤ 4 Hours Rate"
```

### Custom Metrics
Complex calculations with SQL expressions.
```

#### 10.2 Developer Guide
```markdown
# Developer Guide

## Development Setup

```bash
git clone https://github.com/yourusername/dbt-metrics-manager-tui
cd dbt-metrics-manager-tui
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

## Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=dbt_metrics_manager
```

## Code Style

```bash
# Format code
black dbt_metrics_manager/

# Check linting  
flake8 dbt_metrics_manager/

# Type checking
mypy dbt_metrics_manager/
```

## Architecture

The app uses Textual for the TUI framework with the following structure:

- **Screens**: Top-level UI containers
- **Widgets**: Reusable UI components  
- **State**: Application state management
- **Services**: Business logic and data access
- **Models**: Data structures

## Adding New Features

1. Create models in `models/`
2. Implement services in `services/`
3. Create widgets in `widgets/`
4. Build screens in `screens/`
5. Add tests in `tests/`
6. Update documentation
```

## Performance Optimization

### Memory Management
```python
# Use __slots__ for data classes
@dataclass
class Metric:
    __slots__ = ['name', 'short', 'type', 'value']
    
# Clear unused data
def cleanup_state(self):
    self.discovered_metrics.clear()
    self._cache.clear()
```

### Lazy Loading
```python
# Load data only when needed
@property
def expensive_data(self):
    if not hasattr(self, '_expensive_data'):
        self._expensive_data = self._compute_expensive_data()
    return self._expensive_data
```

### Efficient Rendering
```python
# Use reactive updates
def watch_models(self, models: List[DbtModel]) -> None:
    """React to model changes"""
    self.query_one("#model-tree").update_tree(models)
```

## Deployment Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Version bumped
- [ ] Changelog updated
- [ ] Performance tested
- [ ] Cross-platform tested
- [ ] Security review completed
- [ ] PyPI credentials configured
- [ ] Release notes prepared

## Common Issues

### Terminal Compatibility
- Ensure terminal supports 256+ colors
- Test with various terminal emulators
- Handle terminal resizing gracefully

### Performance
- Profile with large datasets
- Optimize database queries
- Cache expensive operations

### User Experience
- Test keyboard navigation
- Verify accessibility
- Validate error messages