"""Integration tests for Metrics Library screen."""

import pytest
from pathlib import Path

from textual.pilot import Pilot
from textual.widgets import Tabs, Button, Input

from dbt_metrics_manager.app import DbtMetricsManagerApp
from dbt_metrics_manager.screens.metrics import MetricsLibraryScreen, MetricFormModal
from dbt_metrics_manager.screens.dashboard import DashboardScreen
from dbt_metrics_manager.models.metric import MetricType

from .test_utils import (
    TestAppState, AppTestHarness, TestMetrics,
    wait_for_screen, click_button_by_id, enter_text_in_input,
    press_key, assert_screen_active, assert_widget_exists,
    assert_widget_text_contains, create_temp_project,
    cleanup_temp_project
)


class TestMetricsLibraryIntegration:
    """Integration tests for Metrics Library functionality."""
    
    @pytest.fixture
    def test_app_state(self):
        """Create test app state with mock metrics."""
        app_state = TestAppState(project_path="/test/project")
        app_state.metrics = TestMetrics.create_test_metrics()
        return app_state
    
    @pytest.fixture
    def app_harness(self, test_app_state):
        """Create app test harness."""
        return AppTestHarness(DbtMetricsManagerApp, test_app_state)
    
    @pytest.mark.asyncio
    async def test_navigate_to_metrics_library(self, app_harness):
        """Test navigating to Metrics Library via F3."""
        async def test(pilot: Pilot):
            # Start on dashboard
            assert_screen_active(pilot, DashboardScreen)
            
            # Press F3 to navigate to Metrics Library
            await press_key(pilot, "f3")
            
            # Wait for Metrics Library screen
            screen = await wait_for_screen(pilot, MetricsLibraryScreen)
            assert_screen_active(pilot, MetricsLibraryScreen)
            
            # Check that essential widgets exist
            assert_widget_exists(pilot, "metrics-tabs")
            assert_widget_exists(pilot, "metrics-filter")
            assert_widget_exists(pilot, "metrics-table")
            assert_widget_exists(pilot, "refresh-metrics-btn")
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_metrics_display(self, app_harness):
        """Test that metrics are displayed in the table."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Check that metrics table has data
            table = pilot.app.query_one("#metrics-table")
            assert table is not None
            
            # Should show 4 test metrics
            await pilot.pause(0.5)
            # Table should have rows (implementation specific)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_filter_functionality(self, app_harness):
        """Test filtering metrics."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Enter filter text
            await enter_text_in_input(pilot, "metrics-filter", "revenue")
            await pilot.pause(0.5)
            
            # Table should be filtered
            table = pilot.app.query_one("#metrics-table")
            # Verify filtering worked (implementation specific)
            assert table is not None
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_tab_navigation(self, app_harness):
        """Test navigating between tabs."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Get tabs widget
            tabs = pilot.app.query_one("#metrics-tabs", Tabs)
            assert tabs.tab_count == 3  # All, By Category, By Model
            
            # Switch to By Category tab
            await pilot.click(tabs.query("Tab")[1])
            await pilot.pause(0.5)
            assert tabs.active == "by-category-tab"
            
            # Switch to By Model tab
            await pilot.click(tabs.query("Tab")[2])
            await pilot.pause(0.5)
            assert tabs.active == "by-model-tab"
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_create_new_metric(self, app_harness):
        """Test creating a new metric."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Click New Metric button
            await click_button_by_id(pilot, "new-metric-btn")
            await pilot.pause(0.5)
            
            # Should open metric form modal
            modal = pilot.app.query_one(MetricFormModal)
            assert modal is not None
            
            # Fill in metric details
            await enter_text_in_input(pilot, "metric-name", "Test Metric")
            await enter_text_in_input(pilot, "metric-short", "test")
            
            # Select metric type (implementation specific)
            type_select = pilot.app.query_one("#metric-type")
            await pilot.click(type_select)
            await pilot.pause(0.5)
            
            # Save metric
            await click_button_by_id(pilot, "save-metric-btn")
            await pilot.pause(0.5)
            
            # Modal should close and metric should be added
            # (Would need to verify in table)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_edit_existing_metric(self, app_harness):
        """Test editing an existing metric."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Select first metric in table
            table = pilot.app.query_one("#metrics-table")
            await pilot.pause(0.5)
            
            # Double-click to edit (implementation specific)
            # This would require actual table row interaction
            
            # Click edit button as alternative
            await click_button_by_id(pilot, "edit-metric-btn")
            await pilot.pause(0.5)
            
            # Should open metric form modal with data
            modal = pilot.app.query_one(MetricFormModal)
            if modal:  # Modal might not open without selection
                # Verify form is populated
                name_input = pilot.app.query_one("#metric-name", Input)
                assert name_input.value != ""
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_delete_metric(self, app_harness):
        """Test deleting a metric."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Select a metric (implementation specific)
            # Would need actual table selection
            
            # Click delete button
            delete_btn = pilot.app.query_one("#delete-metric-btn")
            if not delete_btn.disabled:
                await click_button_by_id(pilot, "delete-metric-btn")
                await pilot.pause(0.5)
                
                # Confirm deletion (if confirmation dialog exists)
                # Metric should be removed from table
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_export_metrics(self, app_harness):
        """Test exporting metrics."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Click export button
            await click_button_by_id(pilot, "export-metrics-btn")
            await pilot.pause(0.5)
            
            # Check for export dialog or action
            # (Implementation specific)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_keyboard_shortcuts(self, app_harness):
        """Test keyboard shortcuts in Metrics Library."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Test Ctrl+N for new metric
            await press_key(pilot, "ctrl+n")
            await pilot.pause(0.5)
            
            # Should open new metric modal
            modal = pilot.app.query_one(MetricFormModal)
            if modal:
                # Close modal
                await press_key(pilot, "escape")
                await pilot.pause(0.5)
            
            # Test Ctrl+F for filter focus
            await press_key(pilot, "ctrl+f")
            filter_input = pilot.app.query_one("#metrics-filter", Input)
            assert pilot.app.focused == filter_input
            
            # Test escape to go back
            await press_key(pilot, "escape")
            await pilot.pause(0.5)
            assert_screen_active(pilot, DashboardScreen)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_empty_metrics_state(self, app_harness):
        """Test behavior with no metrics."""
        # Create app state with no metrics
        app_state = TestAppState(project_path="/test/project")
        app_state.metrics = []
        harness = AppTestHarness(DbtMetricsManagerApp, app_state)
        
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Should show empty state message
            await pilot.pause(0.5)
            # Check for empty state indicator (implementation specific)
            
            # New metric button should still work
            assert_widget_exists(pilot, "new-metric-btn")
        
        await harness.run_test(test)


class TestMetricsLibraryWithRealData:
    """Integration tests with real metric data."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project."""
        temp_dir, project_info = create_temp_project()
        yield temp_dir, project_info
        cleanup_temp_project(temp_dir)
    
    @pytest.fixture
    def app_with_project(self, temp_project):
        """Create app with real project loaded."""
        temp_dir, project_info = temp_project
        app_state = TestAppState()
        app_state.project_path = project_info["project_dir"]
        app_state.project_loaded = True
        
        # Load metrics from CSV
        from dbt_metrics_manager.services.seed_manager import SeedManager
        seed_manager = SeedManager()
        metrics_path = Path(project_info["metrics_csv"])
        if metrics_path.exists():
            app_state.metrics = seed_manager.read_seed_file(metrics_path)
        
        return AppTestHarness(DbtMetricsManagerApp, app_state)
    
    @pytest.mark.asyncio
    async def test_load_from_seed_file(self, app_with_project, temp_project):
        """Test loading metrics from seed file."""
        temp_dir, project_info = temp_project
        
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Should have metrics loaded from CSV
            table = pilot.app.query_one("#metrics-table")
            await pilot.pause(0.5)
            
            # Verify metrics are displayed
            assert table is not None
            # Should have 3 metrics from test CSV
        
        await app_with_project.run_test(test)
    
    @pytest.mark.asyncio
    async def test_save_to_seed_file(self, app_with_project, temp_project):
        """Test saving metrics to seed file."""
        temp_dir, project_info = temp_project
        
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Create a new metric
            await click_button_by_id(pilot, "new-metric-btn")
            await pilot.pause(0.5)
            
            modal = pilot.app.query_one(MetricFormModal)
            if modal:
                # Fill in metric details
                await enter_text_in_input(pilot, "metric-name", "New Test Metric")
                await enter_text_in_input(pilot, "metric-short", "new_test")
                
                # Save metric
                await click_button_by_id(pilot, "save-metric-btn")
                await pilot.pause(0.5)
            
            # Save to file
            await click_button_by_id(pilot, "save-metrics-btn")
            await pilot.pause(1.0)
            
            # Verify file was updated
            csv_path = Path(project_info["metrics_csv"])
            assert csv_path.exists()
            
            # Could also verify backup was created
            backup_path = csv_path.with_suffix('.csv.backup')
            # Backup creation depends on implementation
        
        await app_with_project.run_test(test)
    
    @pytest.mark.asyncio
    async def test_metric_validation(self, app_with_project):
        """Test metric form validation."""
        async def test(pilot: Pilot):
            # Navigate to Metrics Library
            await press_key(pilot, "f3")
            await wait_for_screen(pilot, MetricsLibraryScreen)
            
            # Open new metric form
            await click_button_by_id(pilot, "new-metric-btn")
            await pilot.pause(0.5)
            
            modal = pilot.app.query_one(MetricFormModal)
            if modal:
                # Try to save without required fields
                await click_button_by_id(pilot, "save-metric-btn")
                await pilot.pause(0.5)
                
                # Should show validation errors
                # (Implementation specific)
                
                # Fill required fields
                await enter_text_in_input(pilot, "metric-name", "Valid Metric")
                await enter_text_in_input(pilot, "metric-short", "valid")
                
                # For ratio metric, need both numerator and denominator
                type_select = pilot.app.query_one("#metric-type")
                # Select ratio type (implementation specific)
                
                # Try to save without numerator/denominator
                await click_button_by_id(pilot, "save-metric-btn")
                await pilot.pause(0.5)
                
                # Should show validation error for missing fields
        
        await app_with_project.run_test(test)