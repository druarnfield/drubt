"""Unit tests for ModelTree widget."""

import pytest
from unittest.mock import Mock, patch

from textual.app import App
from textual.message import Message

from dbt_metrics_manager.widgets.model_tree import ModelTree
from dbt_metrics_manager.models.dbt_model import DbtModel


class TestModelTreeWidget:
    """Unit tests for ModelTree widget functionality."""
    
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
            ),
            DbtModel(
                name="daily_summary",
                file_path="models/reports/daily_summary.sql",
                is_rollup=True,
                columns=["date", "revenue_total"],
                description="Daily business summary"
            )
        ]
    
    @pytest.fixture 
    def model_tree(self):
        """Create ModelTree widget instance."""
        return ModelTree(models=[], id="test-tree")
    
    def test_model_tree_initialization(self, model_tree):
        """Test ModelTree widget initialization."""
        assert model_tree.id == "test-tree"
        assert model_tree.show_rollup_only == False
        assert len(model_tree.models) == 0
    
    def test_update_models(self, model_tree, sample_models):
        """Test updating models in the tree."""
        model_tree.update_models(sample_models)
        
        assert len(model_tree.models) == 4
        assert model_tree.models[0].name == "customer_rollup"
        assert model_tree.models[1].name == "product_rollup"
    
    def test_filter_rollup_only(self, model_tree, sample_models):
        """Test filtering to show only rollup models."""
        model_tree.update_models(sample_models)
        model_tree.set_rollup_only(True)
        
        # Should filter to only rollup models
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 3  # 3 rollup models
        assert all(model.is_rollup for model in filtered_models)
    
    def test_search_filtering(self, model_tree, sample_models):
        """Test search functionality."""
        model_tree.update_models(sample_models)
        model_tree.set_search_query("customer")
        
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 2  # customer_rollup and raw_customers
        assert all("customer" in model.name.lower() for model in filtered_models)
    
    def test_combined_filtering(self, model_tree, sample_models):
        """Test combined rollup and search filtering."""
        model_tree.update_models(sample_models)
        model_tree.set_rollup_only(True)
        model_tree.set_search_query("rollup")
        
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 2  # customer_rollup and product_rollup
        assert all(model.is_rollup for model in filtered_models)
        assert all("rollup" in model.name.lower() for model in filtered_models)
    
    def test_directory_grouping(self, model_tree, sample_models):
        """Test that models are grouped by directory."""
        model_tree.update_models(sample_models)
        
        # Check directory structure
        directory_groups = model_tree._group_models_by_directory(sample_models)
        
        assert "models/marts" in directory_groups
        assert "models/staging" in directory_groups  
        assert "models/reports" in directory_groups
        
        assert len(directory_groups["models/marts"]) == 2
        assert len(directory_groups["models/staging"]) == 1
        assert len(directory_groups["models/reports"]) == 1
    
    def test_model_selection_message(self, model_tree, sample_models):
        """Test that selecting a model posts correct message."""
        model_tree.update_models(sample_models)
        
        # Mock the post_message method
        with patch.object(model_tree, 'post_message') as mock_post:
            model_tree._select_model(sample_models[0])
            
            # Should post ModelSelected message
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert isinstance(call_args, ModelTree.ModelSelected)
            assert call_args.model == sample_models[0]
    
    def test_model_icons(self, model_tree, sample_models):
        """Test that correct icons are used for model types."""
        rollup_icon = model_tree._get_model_icon(sample_models[0])  # rollup
        regular_icon = model_tree._get_model_icon(sample_models[2])  # regular
        
        assert rollup_icon != regular_icon
        assert "📊" in rollup_icon or "🎯" in rollup_icon  # Rollup icon
        assert "📄" in regular_icon or "📝" in regular_icon  # Regular icon
    
    def test_empty_models_list(self, model_tree):
        """Test behavior with empty models list."""
        model_tree.update_models([])
        
        assert len(model_tree.models) == 0
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 0
    
    def test_case_insensitive_search(self, model_tree, sample_models):
        """Test that search is case insensitive."""
        model_tree.update_models(sample_models)
        
        # Test uppercase search
        model_tree.set_search_query("CUSTOMER")
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 2
        
        # Test mixed case search
        model_tree.set_search_query("Customer")
        filtered_models = model_tree._get_filtered_models()
        assert len(filtered_models) == 2
    
    def test_refresh_functionality(self, model_tree, sample_models):
        """Test refreshing the model tree."""
        model_tree.update_models(sample_models[:2])  # Add first 2 models
        assert len(model_tree.models) == 2
        
        # Add more models and refresh
        model_tree.update_models(sample_models)  # All 4 models
        assert len(model_tree.models) == 4
    
    def test_model_path_display(self, model_tree, sample_models):
        """Test that model paths are displayed correctly."""
        model_tree.update_models(sample_models)
        
        # Check that file paths are preserved correctly
        customer_model = next(m for m in model_tree.models if m.name == "customer_rollup")
        assert customer_model.file_path == "models/marts/customer_rollup.sql"
        
        # Check directory extraction
        directory = model_tree._get_model_directory(customer_model)
        assert directory == "models/marts"
    
    def test_column_count_display(self, model_tree, sample_models):
        """Test that column counts are displayed."""
        model_tree.update_models(sample_models)
        
        customer_model = sample_models[0]
        column_info = model_tree._get_model_column_info(customer_model)
        
        assert "3 columns" in column_info  # customer_rollup has 3 columns
        assert any(col in column_info for col in customer_model.columns)


class TestModelSelectedMessage:
    """Unit tests for ModelSelected message."""
    
    def test_message_creation(self):
        """Test creating ModelSelected message."""
        model = DbtModel(
            name="test_model",
            file_path="models/test.sql",
            is_rollup=True,
            columns=["id", "value"],
            description="Test model"
        )
        
        message = ModelTree.ModelSelected(model)
        assert message.model == model
        assert isinstance(message, Message)
    
    def test_message_bubbles(self):
        """Test that message bubbles up correctly."""
        model = DbtModel(
            name="test_model", 
            file_path="models/test.sql",
            is_rollup=True,
            columns=["id"],
            description="Test"
        )
        
        message = ModelTree.ModelSelected(model)
        # Message should bubble by default in Textual
        assert message.can_bubble