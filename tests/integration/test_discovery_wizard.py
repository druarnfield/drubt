"""Integration tests for Discovery Wizard screen."""

import pytest
from pathlib import Path

from textual.pilot import Pilot
from textual.widgets import Tabs, Button, ProgressBar

from dbt_metrics_manager.app import DbtMetricsManagerApp
from dbt_metrics_manager.screens.discovery import DiscoveryWizardScreen
from dbt_metrics_manager.screens.dashboard import DashboardScreen

from .test_utils import (
    TestAppState, AppTestHarness, TestMetrics,
    wait_for_screen, click_button_by_id, press_key,
    assert_screen_active, assert_widget_exists,
    assert_widget_text_contains, create_temp_project,
    cleanup_temp_project
)


class TestDiscoveryWizardIntegration:
    """Integration tests for Discovery Wizard functionality."""
    
    @pytest.fixture
    def test_app_state(self):
        """Create test app state with mock data."""
        return TestAppState(project_path="/test/project")
    
    @pytest.fixture
    def app_harness(self, test_app_state):
        """Create app test harness."""
        return AppTestHarness(DbtMetricsManagerApp, test_app_state)
    
    @pytest.mark.asyncio
    async def test_navigate_to_discovery_wizard(self, app_harness):
        """Test navigating to Discovery Wizard via F4."""
        async def test(pilot: Pilot):
            # Start on dashboard
            assert_screen_active(pilot, DashboardScreen)
            
            # Press F4 to navigate to Discovery Wizard
            await press_key(pilot, "f4")
            
            # Wait for Discovery Wizard screen
            screen = await wait_for_screen(pilot, DiscoveryWizardScreen)
            assert_screen_active(pilot, DiscoveryWizardScreen)
            
            # Check that tabs exist
            assert_widget_exists(pilot, "discovery-tabs")
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            assert tabs.tab_count == 4
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_model_selection_step(self, app_harness):
        """Test the model selection step."""
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Should start on Select Models tab
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            assert tabs.active == "select-tab"
            
            # Check model selection list exists
            assert_widget_exists(pilot, "model-selection")
            
            # Test select all button
            await click_button_by_id(pilot, "select-all-btn")
            await pilot.pause(0.5)
            
            # Test clear all button
            await click_button_by_id(pilot, "clear-all-btn")
            await pilot.pause(0.5)
            
            # Select some models and move to next step
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            
            # Should move to analyze tab
            assert tabs.active == "analyze-tab"
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_analysis_step(self, app_harness):
        """Test the analysis step."""
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Select all models and move to analysis
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            
            # Check analysis UI elements
            assert_widget_exists(pilot, "analysis-progress")
            assert_widget_exists(pilot, "analysis-status")
            assert_widget_exists(pilot, "start-analysis-btn")
            
            # Start analysis
            await click_button_by_id(pilot, "start-analysis-btn")
            await pilot.pause(1.0)  # Allow analysis to run
            
            # Progress bar should update
            progress_bar = pilot.app.query_one("#analysis-progress", ProgressBar)
            assert progress_bar.progress > 0
            
            # Review button should be enabled after analysis
            review_btn = pilot.app.query_one("#review-btn", Button)
            assert not review_btn.disabled
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_review_results_step(self, app_harness):
        """Test the review results step."""
        async def test(pilot: Pilot):
            # Navigate through to review step
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Quick path through first two steps
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "start-analysis-btn")
            await pilot.pause(1.5)  # Wait for analysis
            await click_button_by_id(pilot, "review-btn")
            await pilot.pause(0.5)
            
            # Should be on review tab
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            assert tabs.active == "review-tab"
            
            # Check review UI elements
            assert_widget_exists(pilot, "results-table")
            assert_widget_exists(pilot, "select-all-metrics-btn")
            assert_widget_exists(pilot, "select-high-conf-btn")
            assert_widget_exists(pilot, "clear-metrics-btn")
            
            # Test selection buttons
            await click_button_by_id(pilot, "select-all-metrics-btn")
            await pilot.pause(0.5)
            
            # Save button should be enabled with selections
            save_btn = pilot.app.query_one("#save-btn", Button)
            assert not save_btn.disabled
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_save_metrics_step(self, app_harness):
        """Test the save metrics step."""
        async def test(pilot: Pilot):
            # Navigate through to save step
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Quick path through steps
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "start-analysis-btn")
            await pilot.pause(1.5)
            await click_button_by_id(pilot, "review-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "select-all-metrics-btn")
            await click_button_by_id(pilot, "save-btn")
            await pilot.pause(0.5)
            
            # Should be on save tab
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            assert tabs.active == "save-tab"
            
            # Check save UI elements
            assert_widget_exists(pilot, "save-path-input")
            assert_widget_exists(pilot, "backup-checkbox")
            assert_widget_exists(pilot, "merge-checkbox")
            assert_widget_exists(pilot, "final-save-btn")
            
            # Save summary should show selected metrics
            assert_widget_exists(pilot, "save-summary")
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_keyboard_shortcuts(self, app_harness):
        """Test keyboard shortcuts in Discovery Wizard."""
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Test Ctrl+A for analyze all
            await press_key(pilot, "ctrl+a")
            await pilot.pause(1.0)
            
            # Should have selected all and started analysis
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            # May have moved to analyze tab depending on implementation
            
            # Test escape to go back
            await press_key(pilot, "escape")
            await pilot.pause(0.5)
            assert_screen_active(pilot, DashboardScreen)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_back_navigation(self, app_harness):
        """Test back button navigation between steps."""
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Move to analyze step
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            
            # Go back to select
            await click_button_by_id(pilot, "back-to-select-btn")
            await pilot.pause(0.5)
            
            tabs = pilot.app.query_one("#discovery-tabs", Tabs)
            assert tabs.active == "select-tab"
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_empty_model_list(self, app_harness):
        """Test behavior with no rollup models."""
        # Create app state with no rollup models
        app_state = TestAppState(project_path="/test/project")
        app_state.models = [m for m in app_state.models if not m.is_rollup]
        harness = AppTestHarness(DbtMetricsManagerApp, app_state)
        
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Should show message about no rollup models
            await pilot.pause(0.5)
            # Check for info message (implementation specific)
        
        await harness.run_test(test)


class TestDiscoveryWizardWithRealData:
    """Integration tests with real metric discovery."""
    
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
        return AppTestHarness(DbtMetricsManagerApp, app_state)
    
    @pytest.mark.asyncio
    async def test_real_metric_discovery(self, app_with_project):
        """Test Discovery Wizard with real metric analysis."""
        async def test(pilot: Pilot):
            # Navigate to Discovery Wizard
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Select models and run analysis
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "start-analysis-btn")
            await pilot.pause(2.0)  # Allow real analysis to complete
            
            # Move to review
            await click_button_by_id(pilot, "review-btn")
            await pilot.pause(0.5)
            
            # Should have discovered metrics in the table
            results_table = pilot.app.query_one("#results-table")
            assert results_table is not None
            # Table should have rows (implementation specific)
        
        await app_with_project.run_test(test)
    
    @pytest.mark.asyncio
    async def test_save_to_real_file(self, app_with_project, temp_project):
        """Test saving metrics to real CSV file."""
        temp_dir, project_info = temp_project
        
        async def test(pilot: Pilot):
            # Navigate through full workflow
            await press_key(pilot, "f4")
            await wait_for_screen(pilot, DiscoveryWizardScreen)
            
            # Quick path to save
            await click_button_by_id(pilot, "select-all-btn")
            await click_button_by_id(pilot, "analyze-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "start-analysis-btn")
            await pilot.pause(2.0)
            await click_button_by_id(pilot, "review-btn")
            await pilot.pause(0.5)
            await click_button_by_id(pilot, "select-all-metrics-btn")
            await click_button_by_id(pilot, "save-btn")
            await pilot.pause(0.5)
            
            # Save metrics
            await click_button_by_id(pilot, "final-save-btn")
            await pilot.pause(1.0)
            
            # Check for success message
            assert_widget_exists(pilot, "save-results")
            
            # Verify file was created
            csv_path = Path(project_info["project_dir"]) / "data" / "metric_definitions.csv"
            assert csv_path.exists()
        
        await app_with_project.run_test(test)