"""Unit tests for Model Explorer screen."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from textual.widgets import Input, Switch

from dbt_metrics_manager.screens.models import ModelExplorerScreen, ModelDetailsPanel
from dbt_metrics_manager.models.dbt_model import DbtModel
from dbt_metrics_manager.widgets.model_tree import ModelSelectedMessage
from dbt_metrics_manager.state import AppState


class TestModelExplorerScreen:
    """Unit tests for ModelExplorerScreen functionality."""
    
    @pytest.fixture
    def sample_models(self):
        """Create sample models for testing."""
        return [
            DbtModel(
                name="customer_rollup",
                file_path="models/marts/customer_rollup.sql", 
                is_rollup=True,
                columns=["customer_id", "total_revenue_value", "order_count"],
                description="Customer metrics rollup"
            ),
            DbtModel(
                name="product_rollup",
                file_path="models/marts/product_rollup.sql",
                is_rollup=True, 
                columns=["product_id", "sales_value"],
                description="Product metrics rollup"
            ),
            DbtModel(
                name="raw_customers",
                file_path="models/staging/raw_customers.sql",
                is_rollup=False,
                columns=["customer_id", "name", "email"],
                description="Raw customer data"
            )
        ]
    
    @pytest.fixture
    def mock_app_state(self, sample_models):
        """Create mock app state."""
        app_state = Mock(spec=AppState)
        app_state.project_loaded = True
        app_state.models = sample_models
        app_state.project_path = "/test/project"
        return app_state
    
    @pytest.fixture
    def screen(self, mock_app_state):
        """Create ModelExplorerScreen instance."""
        screen = ModelExplorerScreen()
        screen.app_state = mock_app_state
        return screen
    
    def test_screen_initialization(self, screen):
        """Test screen initialization."""
        assert screen.TITLE == "Model Explorer"
        assert len(screen.BINDINGS) > 0
        
        # Check that required bindings exist
        binding_keys = [binding.key for binding in screen.BINDINGS]
        assert "f2" in binding_keys
        assert "a" in binding_keys
        assert "d" in binding_keys
        assert "r" in binding_keys
    
    def test_compose_method(self, screen):
        """Test that compose method creates required widgets."""
        # Mock the compose method to avoid Textual dependencies
        with patch.object(screen, 'query_one') as mock_query:
            mock_model_tree = Mock()
            mock_details_panel = Mock()
            mock_search_input = Mock()
            mock_rollup_filter = Mock()
            
            mock_query.side_effect = [
                mock_model_tree,
                mock_details_panel, 
                mock_search_input,
                mock_rollup_filter
            ]
            
            screen.on_mount()
            
            # Should query for widgets
            assert mock_query.call_count >= 4
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.query_one')
    def test_on_mount_loads_models(self, mock_query, screen, sample_models):
        """Test that on_mount loads models into tree."""
        mock_model_tree = Mock()
        mock_query.return_value = mock_model_tree
        
        screen.on_mount()
        
        # Should update model tree with models
        mock_model_tree.update_models.assert_called_once_with(sample_models)
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.query_one')
    def test_search_input_handler(self, mock_query, screen):
        """Test search input change handler."""
        mock_model_tree = Mock()
        mock_search_input = Mock()
        mock_search_input.value = "customer"
        
        mock_query.side_effect = [mock_model_tree, mock_search_input]
        
        # Create input changed event
        input_event = Mock()
        input_event.input = mock_search_input
        
        screen.on_input_changed(input_event)
        
        # Should update search query on model tree
        mock_model_tree.set_search_query.assert_called_once_with("customer")
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.query_one')
    def test_rollup_filter_handler(self, mock_query, screen):
        """Test rollup filter toggle handler."""
        mock_model_tree = Mock()
        mock_rollup_filter = Mock()
        mock_rollup_filter.value = True
        
        mock_query.side_effect = [mock_model_tree, mock_rollup_filter]
        
        # Create switch changed event
        switch_event = Mock()
        switch_event.switch = mock_rollup_filter
        
        screen.on_switch_changed(switch_event)
        
        # Should set rollup filter on model tree
        mock_model_tree.set_rollup_only.assert_called_once_with(True)
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.query_one')
    def test_model_selection_handler(self, mock_query, screen, sample_models):
        """Test model selection message handler."""
        mock_details_panel = Mock()
        mock_query.return_value = mock_details_panel
        
        # Create model selected message
        selected_model = sample_models[0]
        message = ModelSelectedMessage(selected_model)
        
        screen.on_model_selected(message)
        
        # Should update details panel and store selected model
        mock_details_panel.update_model.assert_called_once_with(selected_model)
        assert screen.selected_model == selected_model
    
    def test_refresh_action(self, screen):
        """Test refresh action."""
        with patch.object(screen, 'load_models') as mock_load:
            screen.action_refresh()
            mock_load.assert_called_once()
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.app')
    def test_analyze_action_with_model(self, mock_app, screen, sample_models):
        """Test analyze action with model selected."""
        screen.selected_model = sample_models[0]  # Rollup model
        
        # Mock services
        mock_sql_parser = Mock()
        mock_metric_analyzer = Mock()
        mock_app.sql_parser = mock_sql_parser
        mock_app.metric_analyzer = mock_metric_analyzer
        
        # Mock parse result
        mock_parse_result = Mock()
        mock_parse_result.success = True
        mock_parse_result.columns = [
            Mock(name="customer_id", type="string"),
            Mock(name="total_revenue_value", type="numeric")
        ]
        mock_sql_parser.parse_file.return_value = mock_parse_result
        
        # Mock analysis result
        mock_analysis_result = Mock()
        mock_analysis_result.discovered_metrics = []
        mock_metric_analyzer.analyze_model.return_value = mock_analysis_result
        
        with patch.object(screen, 'notify') as mock_notify:
            screen.action_analyze()
            
            # Should parse SQL and analyze metrics
            mock_sql_parser.parse_file.assert_called_once()
            mock_metric_analyzer.analyze_model.assert_called_once()
            mock_notify.assert_called()
    
    def test_analyze_action_without_model(self, screen):
        """Test analyze action without model selected."""
        screen.selected_model = None
        
        with patch.object(screen, 'notify') as mock_notify:
            screen.action_analyze()
            
            # Should notify user to select model
            mock_notify.assert_called_once()
            assert "select a model" in mock_notify.call_args[0][0].lower()
    
    def test_analyze_action_non_rollup_model(self, screen, sample_models):
        """Test analyze action with non-rollup model."""
        screen.selected_model = sample_models[2]  # Non-rollup model
        
        with patch.object(screen, 'notify') as mock_notify:
            screen.action_analyze()
            
            # Should notify that only rollup models can be analyzed
            mock_notify.assert_called_once()
            assert "rollup" in mock_notify.call_args[0][0].lower()
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.app')
    def test_discover_action(self, mock_app, screen, sample_models):
        """Test discover metrics action."""
        screen.selected_model = sample_models[0]  # Rollup model
        
        # Mock push_screen method
        mock_app.push_screen = Mock()
        
        screen.action_discover()
        
        # Should navigate to discovery wizard
        mock_app.push_screen.assert_called_once()
        call_args = mock_app.push_screen.call_args[0][0]
        assert "DiscoveryWizardScreen" in str(type(call_args))
    
    def test_keyboard_shortcuts(self, screen):
        """Test keyboard shortcut actions."""
        # Test that action methods exist for all bindings
        assert hasattr(screen, 'action_show_models')
        assert hasattr(screen, 'action_analyze')
        assert hasattr(screen, 'action_discover') 
        assert hasattr(screen, 'action_refresh')
        assert hasattr(screen, 'action_focus_search')
    
    @patch('dbt_metrics_manager.screens.models.ModelExplorerScreen.query_one')
    def test_focus_search_action(self, mock_query, screen):
        """Test focus search action."""
        mock_search_input = Mock()
        mock_query.return_value = mock_search_input
        
        screen.action_focus_search()
        
        # Should focus search input
        mock_search_input.focus.assert_called_once()


class TestModelDetailsPanel:
    """Unit tests for ModelDetailsPanel widget."""
    
    @pytest.fixture
    def sample_model(self):
        """Create sample model for testing."""
        return DbtModel(
            name="customer_rollup",
            file_path="models/marts/customer_rollup.sql",
            is_rollup=True,
            columns=["customer_id", "total_revenue_value", "order_count"],
            description="Customer metrics rollup"
        )
    
    @pytest.fixture
    def details_panel(self):
        """Create ModelDetailsPanel instance."""
        return ModelDetailsPanel(id="test-details")
    
    def test_panel_initialization(self, details_panel):
        """Test panel initialization."""
        assert details_panel.id == "test-details"
        assert details_panel.current_model is None
    
    def test_update_model(self, details_panel, sample_model):
        """Test updating model in details panel."""
        details_panel.update_model(sample_model)
        
        assert details_panel.current_model == sample_model
        # Should trigger UI update (implementation specific)
    
    def test_clear_model(self, details_panel, sample_model):
        """Test clearing model from details panel."""
        details_panel.update_model(sample_model)
        assert details_panel.current_model == sample_model
        
        details_panel.clear()
        assert details_panel.current_model is None
    
    def test_model_info_formatting(self, details_panel, sample_model):
        """Test model information formatting."""
        model_info = details_panel._format_model_info(sample_model)
        
        assert sample_model.name in model_info
        assert sample_model.file_path in model_info
        assert sample_model.description in model_info
        assert "3 columns" in model_info  # Column count
    
    def test_column_info_formatting(self, details_panel, sample_model):
        """Test column information formatting."""
        column_info = details_panel._format_column_info(sample_model)
        
        for column in sample_model.columns:
            assert column in column_info
    
    def test_rollup_indicator(self, details_panel, sample_model):
        """Test rollup model indicator."""
        model_info = details_panel._format_model_info(sample_model)
        
        # Should indicate it's a rollup model
        assert "rollup" in model_info.lower() or "📊" in model_info
    
    def test_empty_state(self, details_panel):
        """Test empty state display."""
        empty_content = details_panel._get_empty_state_content()
        
        assert "Select a model" in empty_content or "No model selected" in empty_content