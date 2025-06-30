"""Test utilities for integration testing."""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import tempfile
import shutil

from textual.app import App
from textual.pilot import Pilot
from textual.screen import Screen
from textual.widgets import Button, Input

from dbt_metrics_manager.models.dbt_model import DbtModel
from dbt_metrics_manager.models.metric import Metric, MetricType
from dbt_metrics_manager.state import AppState


class TestAppState(AppState):
    """Test application state with mock data."""
    
    def __init__(self, project_path: Optional[str] = None):
        """Initialize test app state with optional project path."""
        super().__init__()
        if project_path:
            self.project_path = project_path
            self.project_loaded = True
            self.project_name = "test_project"
            self.models = self._create_test_models()
    
    def _create_test_models(self) -> List[DbtModel]:
        """Create test models for testing."""
        return [
            DbtModel(
                name="customer_rollup",
                file_path="models/marts/customer_rollup.sql",
                is_rollup=True,
                columns=[
                    "customer_id",
                    "total_revenue_value",
                    "order_count",
                    "conversion_numerator",
                    "conversion_denominator",
                    "avg_order_value"
                ],
                description="Customer metrics rollup"
            ),
            DbtModel(
                name="product_rollup",
                file_path="models/marts/product_rollup.sql",
                is_rollup=True,
                columns=[
                    "product_id",
                    "sales_value",
                    "units_sold_count",
                    "return_rate_numerator",
                    "return_rate_denominator"
                ],
                description="Product metrics rollup"
            ),
            DbtModel(
                name="raw_customers",
                file_path="models/staging/raw_customers.sql",
                is_rollup=False,
                columns=["customer_id", "name", "email", "created_at"],
                description="Raw customer data"
            ),
            DbtModel(
                name="daily_summary",
                file_path="models/marts/daily_summary.sql",
                is_rollup=True,
                columns=[
                    "date",
                    "revenue_total",
                    "new_customers_count",
                    "churn_rate"
                ],
                description="Daily business summary"
            )
        ]


class MockProjectHelper:
    """Helper for creating mock dbt projects."""
    
    @staticmethod
    def create_mock_project(base_dir: Path) -> Dict[str, Any]:
        """Create a mock dbt project structure.
        
        Args:
            base_dir: Base directory for the project
            
        Returns:
            Dictionary with project information
        """
        # Create directory structure
        project_dir = base_dir / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        models_dir = project_dir / "models"
        models_dir.mkdir(exist_ok=True)
        
        target_dir = project_dir / "target"
        target_dir.mkdir(exist_ok=True)
        
        data_dir = project_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create dbt_project.yml
        project_yml = project_dir / "dbt_project.yml"
        project_yml.write_text("""
name: 'test_project'
version: '1.0.0'
profile: 'test'

model-paths: ["models"]
seed-paths: ["data"]
test-paths: ["tests"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  test_project:
    materialized: table
""")
        
        # Create manifest.json
        manifest = {
            "nodes": {
                "model.test_project.customer_rollup": {
                    "name": "customer_rollup",
                    "resource_type": "model",
                    "path": "marts/customer_rollup.sql",
                    "description": "Customer metrics rollup",
                    "columns": {
                        "customer_id": {"name": "customer_id", "data_type": "string"},
                        "total_revenue_value": {"name": "total_revenue_value", "data_type": "numeric"},
                        "order_count": {"name": "order_count", "data_type": "integer"},
                        "conversion_numerator": {"name": "conversion_numerator", "data_type": "integer"},
                        "conversion_denominator": {"name": "conversion_denominator", "data_type": "integer"}
                    }
                },
                "model.test_project.product_rollup": {
                    "name": "product_rollup",
                    "resource_type": "model",
                    "path": "marts/product_rollup.sql",
                    "description": "Product metrics rollup",
                    "columns": {
                        "product_id": {"name": "product_id", "data_type": "string"},
                        "sales_value": {"name": "sales_value", "data_type": "numeric"},
                        "units_sold_count": {"name": "units_sold_count", "data_type": "integer"}
                    }
                }
            }
        }
        
        manifest_path = target_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        # Create catalog.json
        catalog = {
            "nodes": {
                "model.test_project.customer_rollup": {
                    "columns": {
                        "customer_id": {"type": "VARCHAR", "index": 1},
                        "total_revenue_value": {"type": "NUMERIC", "index": 2},
                        "order_count": {"type": "INTEGER", "index": 3},
                        "conversion_numerator": {"type": "INTEGER", "index": 4},
                        "conversion_denominator": {"type": "INTEGER", "index": 5}
                    }
                }
            }
        }
        
        catalog_path = target_dir / "catalog.json"
        catalog_path.write_text(json.dumps(catalog, indent=2))
        
        # Create sample SQL files
        marts_dir = models_dir / "marts"
        marts_dir.mkdir(exist_ok=True)
        
        customer_sql = marts_dir / "customer_rollup.sql"
        customer_sql.write_text("""
SELECT 
    customer_id,
    SUM(revenue) AS total_revenue_value,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) AS conversion_numerator,
    COUNT(*) AS conversion_denominator,
    AVG(order_amount) AS avg_order_value
FROM {{ ref('customer_orders') }}
GROUP BY customer_id
""")
        
        # Create sample metric_definitions.csv
        metrics_csv = data_dir / "metric_definitions.csv"
        metrics_csv.write_text("""name,short,type,category,value,numerator,denominator,sql,model_name,description,owner
Total Revenue,rev,direct,Financial,total_revenue_value,,,,customer_rollup,Total customer revenue,analytics
Order Count,ord,direct,Operations,order_count,,,,customer_rollup,Number of orders,analytics
Conversion Rate,conv,ratio,Marketing,,conversion_numerator,conversion_denominator,,customer_rollup,Customer conversion rate,marketing
""")
        
        return {
            "project_dir": str(project_dir),
            "manifest_path": str(manifest_path),
            "catalog_path": str(catalog_path),
            "metrics_csv": str(metrics_csv)
        }


class TestMetrics:
    """Helper for creating test metrics."""
    
    @staticmethod
    def create_test_metrics() -> List[Metric]:
        """Create a set of test metrics."""
        return [
            Metric(
                name="Total Revenue",
                short="rev",
                type=MetricType.DIRECT,
                category="Financial",
                value="total_revenue_value",
                model_name="customer_rollup",
                description="Total customer revenue",
                owner="analytics"
            ),
            Metric(
                name="Order Count",
                short="ord",
                type=MetricType.DIRECT,
                category="Operations",
                value="order_count",
                model_name="customer_rollup",
                description="Number of orders",
                owner="analytics"
            ),
            Metric(
                name="Conversion Rate",
                short="conv",
                type=MetricType.RATIO,
                category="Marketing",
                numerator="conversion_numerator",
                denominator="conversion_denominator",
                model_name="customer_rollup",
                description="Customer conversion rate",
                owner="marketing"
            ),
            Metric(
                name="Sales Revenue",
                short="sales",
                type=MetricType.DIRECT,
                category="Financial",
                value="sales_value",
                model_name="product_rollup",
                description="Product sales revenue",
                owner="sales"
            )
        ]


async def wait_for_screen(pilot: Pilot, screen_type: type, timeout: float = 5.0) -> Screen:
    """Wait for a specific screen type to appear.
    
    Args:
        pilot: Textual pilot
        screen_type: Type of screen to wait for
        timeout: Maximum time to wait
        
    Returns:
        The screen instance
        
    Raises:
        TimeoutError: If screen doesn't appear in time
    """
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        current_screen = pilot.app.screen
        if isinstance(current_screen, screen_type):
            return current_screen
        await pilot.pause(0.1)
    
    raise TimeoutError(f"Screen {screen_type.__name__} did not appear within {timeout} seconds")


async def click_button_by_id(pilot: Pilot, button_id: str) -> None:
    """Click a button by its ID.
    
    Args:
        pilot: Textual pilot
        button_id: ID of the button to click
    """
    button = pilot.app.query_one(f"#{button_id}", Button)
    await pilot.click(button)
    await pilot.pause(0.1)


async def enter_text_in_input(pilot: Pilot, input_id: str, text: str) -> None:
    """Enter text in an input field.
    
    Args:
        pilot: Textual pilot
        input_id: ID of the input field
        text: Text to enter
    """
    input_widget = pilot.app.query_one(f"#{input_id}", Input)
    input_widget.focus()
    await pilot.pause(0.1)
    input_widget.value = text
    await pilot.pause(0.1)


async def press_key(pilot: Pilot, key: str) -> None:
    """Press a keyboard key.
    
    Args:
        pilot: Textual pilot
        key: Key to press (e.g., "f1", "enter", "escape")
    """
    await pilot.press(key)
    await pilot.pause(0.1)


def create_temp_project() -> tuple[Path, Dict[str, Any]]:
    """Create a temporary project for testing.
    
    Returns:
        Tuple of (temp_dir, project_info)
    """
    temp_dir = Path(tempfile.mkdtemp())
    project_info = MockProjectHelper.create_mock_project(temp_dir)
    return temp_dir, project_info


def cleanup_temp_project(temp_dir: Path) -> None:
    """Clean up temporary project directory.
    
    Args:
        temp_dir: Directory to clean up
    """
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


class AppTestHarness:
    """Test harness for running app tests."""
    
    def __init__(self, app_class: type[App], app_state: Optional[AppState] = None):
        """Initialize test harness.
        
        Args:
            app_class: Application class to test
            app_state: Optional app state to use
        """
        self.app_class = app_class
        self.app_state = app_state or TestAppState()
    
    async def run_test(self, test_func) -> Any:
        """Run a test function with the app.
        
        Args:
            test_func: Async function that takes a Pilot
            
        Returns:
            Result from test function
        """
        app = self.app_class()
        if hasattr(app, 'app_state'):
            app.app_state = self.app_state
        
        async with app.run_test() as pilot:
            return await test_func(pilot)


def assert_screen_active(pilot: Pilot, screen_type: type) -> None:
    """Assert that a specific screen type is active.
    
    Args:
        pilot: Textual pilot
        screen_type: Expected screen type
        
    Raises:
        AssertionError: If wrong screen is active
    """
    current_screen = pilot.app.screen
    assert isinstance(current_screen, screen_type), \
        f"Expected {screen_type.__name__}, got {type(current_screen).__name__}"


def assert_widget_exists(pilot: Pilot, widget_id: str) -> None:
    """Assert that a widget with given ID exists.
    
    Args:
        pilot: Textual pilot
        widget_id: ID of widget to check
        
    Raises:
        AssertionError: If widget doesn't exist
    """
    try:
        pilot.app.query_one(f"#{widget_id}")
    except:
        raise AssertionError(f"Widget with ID '{widget_id}' not found")


def assert_widget_text_contains(pilot: Pilot, widget_id: str, text: str) -> None:
    """Assert that a widget contains specific text.
    
    Args:
        pilot: Textual pilot
        widget_id: ID of widget to check
        text: Text that should be contained
        
    Raises:
        AssertionError: If text not found
    """
    widget = pilot.app.query_one(f"#{widget_id}")
    widget_text = str(widget.renderable)
    assert text in widget_text, \
        f"Expected text '{text}' not found in widget '{widget_id}'. Found: {widget_text}"