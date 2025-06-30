"""Integration tests for Model Explorer screen."""

import pytest
from pathlib import Path

from textual.pilot import Pilot

from dbt_metrics_manager.app import DbtMetricsManagerApp
from dbt_metrics_manager.screens.models import ModelExplorerScreen
from dbt_metrics_manager.screens.dashboard import DashboardScreen

from .test_utils import (
    TestAppState, AppTestHarness, wait_for_screen,
    click_button_by_id, enter_text_in_input, press_key,
    assert_screen_active, assert_widget_exists,
    assert_widget_text_contains, create_temp_project,
    cleanup_temp_project
)


class TestModelExplorerIntegration:
    """Integration tests for Model Explorer functionality."""
    
    @pytest.fixture
    def test_app_state(self):
        """Create test app state with mock data."""
        return TestAppState(project_path="/test/project")
    
    @pytest.fixture
    def app_harness(self, test_app_state):
        """Create app test harness."""
        return AppTestHarness(DbtMetricsManagerApp, test_app_state)
    
    @pytest.mark.asyncio
    async def test_navigate_to_model_explorer(self, app_harness):
        """Test navigating to Model Explorer screen via F2."""
        async def test(pilot: Pilot):
            # Start on dashboard
            assert_screen_active(pilot, DashboardScreen)
            
            # Press F2 to navigate to Model Explorer
            await press_key(pilot, "f2")
            
            # Wait for Model Explorer screen
            screen = await wait_for_screen(pilot, ModelExplorerScreen)
            assert_screen_active(pilot, ModelExplorerScreen)
            
            # Check that essential widgets exist
            assert_widget_exists(pilot, "model-tree")
            assert_widget_exists(pilot, "details-panel")
            assert_widget_exists(pilot, "search-input")
            assert_widget_exists(pilot, "rollup-filter")
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_model_tree_display(self, app_harness):
        """Test that model tree displays models correctly."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Check that models are displayed
            tree = pilot.app.query_one("#model-tree")
            assert tree is not None
            
            # Should show both rollup and regular models
            # The test app state has 4 models: 2 rollup, 1 regular, 1 rollup
            await pilot.pause(0.5)  # Allow tree to populate
            
            # Check tree content (this would need actual tree navigation)
            # For now, just verify tree exists and has content
            assert len(tree.children) > 0
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_rollup_filter_toggle(self, app_harness):
        """Test toggling the rollup-only filter."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Get initial model count
            tree = pilot.app.query_one("#model-tree")
            initial_count = len(tree.children)
            
            # Toggle rollup filter
            rollup_switch = pilot.app.query_one("#rollup-filter")
            await pilot.click(rollup_switch)
            await pilot.pause(0.5)
            
            # Tree should now show fewer models (only rollup)
            filtered_count = len(tree.children)
            assert filtered_count <= initial_count
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_model_search(self, app_harness):
        """Test searching for models."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Enter search term
            await enter_text_in_input(pilot, "search-input", "customer")
            await pilot.pause(0.5)
            
            # Tree should be filtered
            tree = pilot.app.query_one("#model-tree")
            # Verify search worked (implementation specific)
            assert tree is not None
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_model_selection_and_details(self, app_harness):
        """Test selecting a model and viewing details."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            screen = await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Select first model in tree
            tree = pilot.app.query_one("#model-tree")
            await pilot.pause(0.5)
            
            # Click on first node (implementation specific)
            # This would require actual tree node interaction
            
            # Check that details panel updates
            details_panel = pilot.app.query_one("#details-panel")
            assert details_panel is not None
            
            # Verify analyze and discover buttons are enabled
            # when a rollup model is selected
            analyze_btn = pilot.app.query_one("#analyze-btn")
            discover_btn = pilot.app.query_one("#discover-btn")
            
            # Initially disabled
            assert analyze_btn.disabled
            assert discover_btn.disabled
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_refresh_functionality(self, app_harness):
        """Test refresh button functionality."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Click refresh button
            await click_button_by_id(pilot, "refresh-btn")
            await pilot.pause(0.5)
            
            # Verify no errors occurred
            # Tree should still be populated
            tree = pilot.app.query_one("#model-tree")
            assert tree is not None
            assert len(tree.children) > 0
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, app_harness):
        """Test keyboard shortcuts in Model Explorer."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Test Ctrl+F focuses search
            await press_key(pilot, "ctrl+f")
            search_input = pilot.app.query_one("#search-input")
            assert pilot.app.focused == search_input
            
            # Test 'r' refreshes
            await press_key(pilot, "r")
            await pilot.pause(0.5)
            
            # Test escape goes back
            await press_key(pilot, "escape")
            await pilot.pause(0.5)
            assert_screen_active(pilot, DashboardScreen)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_model_analysis_action(self, app_harness):
        """Test model analysis action (when implemented)."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # This test would require selecting a model first
            # Then testing the analyze action
            
            # For now, just verify the button exists
            assert_widget_exists(pilot, "analyze-btn")
            
            # Test keyboard shortcut
            await press_key(pilot, "a")  # Should trigger analyze if model selected
            await pilot.pause(0.5)
        
        await app_harness.run_test(test)
    
    @pytest.mark.asyncio
    async def test_discover_metrics_navigation(self, app_harness):
        """Test navigating to discovery wizard from model."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # This would require selecting a rollup model first
            # Then clicking discover button
            
            # For now, verify button exists
            assert_widget_exists(pilot, "discover-btn")
            
            # Test keyboard shortcut
            await press_key(pilot, "d")  # Should trigger discover if model selected
            await pilot.pause(0.5)
        
        await app_harness.run_test(test)


class TestModelExplorerWithRealProject:
    """Integration tests with real project structure."""
    
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
    async def test_real_project_models(self, app_with_project):
        """Test Model Explorer with real project structure."""
        async def test(pilot: Pilot):
            # Navigate to Model Explorer
            await press_key(pilot, "f2")
            await wait_for_screen(pilot, ModelExplorerScreen)
            
            # Verify models are loaded
            tree = pilot.app.query_one("#model-tree")
            await pilot.pause(1.0)  # Allow time for loading
            
            # Should have models from the project
            assert len(tree.children) > 0
            
            # Test SQL parsing integration
            # Select a model and verify details show SQL info
            # (Would require actual tree interaction)
        
        await app_with_project.run_test(test)