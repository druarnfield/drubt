"""Unit tests for Metric Analyzer service."""

import re
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dbt_metrics_manager.services.metric_analyzer import (
    MetricAnalyzer, MetricDiscovery, AnalysisContext, MetricPattern
)
from dbt_metrics_manager.services.sql_parser import SqlParser, SqlParseResult, ColumnInfo
from dbt_metrics_manager.models.metric import Metric, MetricType
from dbt_metrics_manager.models.dbt_model import DbtModel


class TestMetricAnalyzer:
    """Test the Metric Analyzer service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MetricAnalyzer()
    
    def test_find_direct_metrics(self):
        """Test finding direct metrics from columns."""
        columns = [
            ColumnInfo(name="customer_id", expression="customer_id"),
            ColumnInfo(name="revenue_value", expression="revenue_value"),
            ColumnInfo(name="order_count", expression="order_count"),
            ColumnInfo(name="regular_column", expression="regular_column")
        ]
        
        context = AnalysisContext(
            model_name="customer_rollup",
            file_path="/path/to/model.sql",
            columns=columns,
            is_rollup=True,
            source_tables=["orders"],
            raw_sql="SELECT * FROM orders"
        )
        
        direct_metrics = self.analyzer._find_direct_metrics(context)
        
        assert len(direct_metrics) == 2
        metric_names = [m.name for m in direct_metrics]
        assert "Revenue" in metric_names
        assert "Order" in metric_names
    
    def test_find_ratio_metrics(self):
        """Test finding ratio metrics from numerator/denominator pairs."""
        columns = [
            ColumnInfo(name="conversion_numerator", expression="conversion_numerator"),
            ColumnInfo(name="conversion_denominator", expression="conversion_denominator"),
            ColumnInfo(name="retention_numerator", expression="retention_numerator"),
            ColumnInfo(name="single_column", expression="single_column")
        ]
        
        context = AnalysisContext(
            model_name="metrics_rollup",
            file_path="/path/to/model.sql",
            columns=columns,
            is_rollup=True,
            source_tables=["events"],
            raw_sql="SELECT * FROM events"
        )
        
        ratio_metrics = self.analyzer._find_ratio_metrics(context)
        
        assert len(ratio_metrics) == 1
        metric = ratio_metrics[0]
        assert metric.type == MetricType.RATIO
        assert metric.numerator == "conversion_numerator"
        assert metric.denominator == "conversion_denominator"
    
    def test_find_aggregated_metrics(self):
        """Test finding metrics from aggregated columns."""
        columns = [
            ColumnInfo(name="total_revenue", expression="SUM(revenue)", 
                      is_aggregated=True, function_type="SUM"),
            ColumnInfo(name="customer_count", expression="COUNT(DISTINCT customer_id)", 
                      is_aggregated=True, function_type="COUNT"),
            ColumnInfo(name="regular_column", expression="customer_id")
        ]
        
        context = AnalysisContext(
            model_name="customer_rollup",
            file_path="/path/to/model.sql",
            columns=columns,
            is_rollup=True,
            source_tables=["orders"],
            raw_sql="SELECT * FROM orders"
        )
        
        direct_metrics = self.analyzer._find_direct_metrics(context)
        
        # Should find aggregated metrics
        aggregated_metrics = [m for m in direct_metrics if any(
            col.name == m.value for col in columns if col.is_aggregated
        )]
        assert len(aggregated_metrics) >= 2
    
    def test_confidence_calculation(self):
        """Test confidence score calculation for metrics."""
        metric = Metric(
            name="Revenue",
            short="rev",
            type=MetricType.DIRECT,
            value="revenue_value",
            confidence_score=0.5
        )
        
        context = AnalysisContext(
            model_name="customer_revenue_rollup",
            file_path="/path/to/model.sql",
            columns=[],
            is_rollup=True,
            source_tables=[],
            raw_sql=""
        )
        
        confidence = self.analyzer._calculate_metric_confidence(metric, context)
        
        # Should be boosted for business domain (revenue) and rollup model
        assert confidence > 0.5
    
    def test_non_rollup_model_analysis(self):
        """Test analysis of non-rollup models."""
        model = DbtModel(
            name="raw_customers",
            file_path="/path/to/raw_customers.sql",
            is_rollup=False,
            columns=["customer_id", "name", "email"]
        )
        
        discovery = self.analyzer.analyze_model(model)
        
        assert discovery.confidence_score == 0.0
        assert len(discovery.suggested_metrics) == 0
        assert "not appear to be a rollup" in discovery.discovery_notes[0]
    
    def test_metric_name_generation(self):
        """Test metric name generation from column names."""
        test_cases = [
            ("revenue_value", "Revenue"),
            ("order_count", "Order"),
            ("customer_retention_rate", "Customer Retention Rate"),
            ("avg_order_amount", "Avg Order Amount")
        ]
        
        for column_name, expected_name in test_cases:
            generated_name = self.analyzer._generate_metric_name(column_name)
            assert generated_name == expected_name
    
    def test_short_name_generation(self):
        """Test short name generation from column names."""
        test_cases = [
            ("revenue_value", "rev_val"),
            ("customer_count", "cus_cou"),
            ("avg_order_amount", "avg_ord_amo")
        ]
        
        for column_name, expected_short in test_cases:
            generated_short = self.analyzer._generate_short_name(column_name)
            assert generated_short == expected_short
    
    def test_category_inference(self):
        """Test category inference from names."""
        test_cases = [
            ("revenue_value", "customer_model", "Financial"),
            ("conversion_rate", "marketing_model", "Marketing"),
            ("engagement_score", "user_model", "Engagement"),
            ("order_count", "order_rollup", "Order"),
            ("unknown_metric", "unknown_model", "General")
        ]
        
        for metric_name, model_name, expected_category in test_cases:
            category = self.analyzer._infer_category(metric_name, model_name)
            assert category == expected_category
    
    def test_complex_expression_detection(self):
        """Test detection of complex expressions."""
        test_cases = [
            (ColumnInfo(name="calc", expression="revenue * 0.1"), True),
            (ColumnInfo(name="calc", expression="CASE WHEN x > 0 THEN 1 ELSE 0 END"), True),
            (ColumnInfo(name="calc", expression="ROUND(avg_value, 2)"), True),
            (ColumnInfo(name="simple", expression="customer_id"), False),
            (ColumnInfo(name="simple", expression="SUM(revenue)"), False)
        ]
        
        for column, expected_complex in test_cases:
            is_complex = self.analyzer._is_complex_expression(column)
            assert is_complex == expected_complex
    
    def test_base_name_extraction(self):
        """Test extraction of base names from column names."""
        test_cases = [
            ("conversion_numerator", "conversion"),
            ("conversion_denominator", "conversion"),
            ("revenue_value", "revenue"),
            ("order_count", "order"),
            ("simple_name", "simple_name")
        ]
        
        for column_name, expected_base in test_cases:
            base_name = self.analyzer._extract_base_name(column_name)
            assert base_name == expected_base
    
    @patch('dbt_metrics_manager.services.metric_analyzer.Path')
    def test_analyze_model_with_sql_file(self, mock_path):
        """Test analyzing a model with SQL file parsing."""
        # Mock file existence
        mock_path.return_value.exists.return_value = True
        
        # Mock SQL parser
        mock_sql_result = SqlParseResult(
            file_path="/path/to/model.sql",
            model_name="customer_rollup",
            columns=[
                ColumnInfo(name="customer_id", expression="customer_id"),
                ColumnInfo(name="revenue_value", expression="SUM(revenue)", is_aggregated=True)
            ],
            source_tables=["orders"],
            is_rollup_model=True,
            cte_names=[],
            errors=[],
            raw_sql="SELECT customer_id, SUM(revenue) AS revenue_value FROM orders GROUP BY customer_id"
        )
        
        with patch.object(self.analyzer.sql_parser, 'parse_file', return_value=mock_sql_result):
            model = DbtModel(
                name="customer_rollup",
                file_path="/path/to/model.sql",
                is_rollup=True,
                columns=["customer_id", "revenue_value"]
            )
            
            discovery = self.analyzer.analyze_model(model)
            
            assert discovery.model_name == "customer_rollup"
            assert len(discovery.suggested_metrics) > 0
            assert discovery.confidence_score > 0
    
    def test_batch_analyze_models(self):
        """Test batch analysis of multiple models."""
        models = [
            DbtModel(name="model1", is_rollup=True, columns=["revenue_value"]),
            DbtModel(name="model2", is_rollup=False, columns=["customer_id"]),
            DbtModel(name="model3", is_rollup=True, columns=["order_count"])
        ]
        
        results = self.analyzer.batch_analyze_models(models)
        
        assert len(results) == 3
        assert results[0].model_name == "model1"
        assert results[1].model_name == "model2"
        assert results[2].model_name == "model3"
        
        # First and third should have metrics (rollup models)
        assert len(results[0].suggested_metrics) > 0
        assert len(results[1].suggested_metrics) == 0  # Not rollup
        assert len(results[2].suggested_metrics) > 0
    
    def test_cache_functionality(self):
        """Test caching of analysis results."""
        model = DbtModel(
            name="test_model",
            file_path="/path/to/test.sql",
            is_rollup=True,
            columns=["revenue_value"]
        )
        
        # First analysis
        discovery1 = self.analyzer.analyze_model(model)
        
        # Second analysis should use cache
        discovery2 = self.analyzer.analyze_model(model)
        
        assert discovery1 is discovery2  # Should be same object from cache
        
        # Clear cache and analyze again
        self.analyzer.clear_cache()
        discovery3 = self.analyzer.analyze_model(model)
        
        assert discovery1 is not discovery3  # Should be different object
    
    def test_discovery_notes_generation(self):
        """Test generation of discovery notes."""
        context = AnalysisContext(
            model_name="customer_rollup",
            file_path="/path/to/model.sql",
            columns=[
                ColumnInfo(name="customer_id", expression="customer_id"),
                ColumnInfo(name="revenue_value", expression="SUM(revenue)")
            ],
            is_rollup=True,
            source_tables=["orders"],
            raw_sql="SELECT * FROM orders"
        )
        
        metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, value="revenue_value"),
            Metric(name="Conversion", short="conv", type=MetricType.RATIO, 
                  numerator="conv_num", denominator="conv_den")
        ]
        
        notes = self.analyzer._generate_discovery_notes(context, metrics)
        
        assert any("rollup/aggregation model" in note for note in notes)
        assert any("Found 2 potential metrics" in note for note in notes)
        assert any("1 direct metrics" in note for note in notes)
        assert any("1 ratio metrics" in note for note in notes)
    
    def test_column_analysis(self):
        """Test individual column analysis."""
        context = AnalysisContext(
            model_name="customer_rollup",
            file_path="/path/to/model.sql",
            columns=[
                ColumnInfo(name="revenue_value", expression="SUM(revenue)", 
                          is_aggregated=True, function_type="SUM"),
                ColumnInfo(name="conversion_numerator", expression="conversion_numerator"),
                ColumnInfo(name="customer_count", expression="COUNT(customer_id)")
            ],
            is_rollup=True,
            source_tables=["orders"],
            raw_sql="SELECT * FROM orders"
        )
        
        analysis = self.analyzer._analyze_columns(context)
        
        assert "revenue_value" in analysis
        assert "direct value metric" in analysis["revenue_value"].lower()
        assert "conversion_numerator" in analysis
        assert "ratio numerator" in analysis["conversion_numerator"].lower()


class TestMetricAnalyzerIntegration:
    """Integration tests for Metric Analyzer with SQL Parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MetricAnalyzer()
    
    def test_analyze_sql_file_integration(self, tmp_path):
        """Test analyzing a SQL file end-to-end."""
        sql_content = """
        SELECT 
            customer_segment,
            SUM(revenue) AS total_revenue_value,
            COUNT(*) AS order_count,
            SUM(conversions) AS conversion_numerator,
            SUM(visits) AS conversion_denominator
        FROM customer_orders
        GROUP BY customer_segment
        """
        
        sql_file = tmp_path / "customer_rollup.sql"
        sql_file.write_text(sql_content)
        
        discovery = self.analyzer.analyze_sql_file(sql_file)
        
        assert discovery.model_name == "customer_rollup"
        assert discovery.confidence_score > 0
        assert len(discovery.suggested_metrics) >= 3  # Should find direct and ratio metrics
        
        # Check for specific metric types
        metric_types = [m.type for m in discovery.suggested_metrics]
        assert MetricType.DIRECT in metric_types
        assert MetricType.RATIO in metric_types
    
    def test_error_handling_in_batch_analysis(self):
        """Test error handling during batch analysis."""
        # Create a model that will cause an error
        problem_model = DbtModel(
            name="problem_model",
            file_path="/non/existent/path.sql",
            is_rollup=True,
            columns=["revenue_value"]
        )
        
        good_model = DbtModel(
            name="good_model",
            is_rollup=True,
            columns=["order_count"]
        )
        
        models = [problem_model, good_model]
        results = self.analyzer.batch_analyze_models(models)
        
        assert len(results) == 2
        
        # First result should have errors
        assert len(results[0].discovery_notes) > 0
        assert "failed" in results[0].discovery_notes[0].lower()
        
        # Second result should be successful
        assert results[1].model_name == "good_model"


class TestMetricPatterns:
    """Test metric patterns and pattern matching."""
    
    def test_metric_pattern_creation(self):
        """Test MetricPattern dataclass creation."""
        pattern = MetricPattern(
            pattern=r'_value$',
            metric_type=MetricType.DIRECT,
            confidence_boost=0.9,
            description="Direct value metric"
        )
        
        assert pattern.pattern == r'_value$'
        assert pattern.metric_type == MetricType.DIRECT
        assert pattern.confidence_boost == 0.9
        assert pattern.description == "Direct value metric"
    
    def test_pattern_matching(self):
        """Test pattern matching against column names."""
        analyzer = MetricAnalyzer()
        
        # Test direct patterns
        direct_patterns = [p for p in analyzer.METRIC_PATTERNS if p.metric_type == MetricType.DIRECT]
        test_columns = [
            "revenue_value", "order_count", "total_sum", "avg_amount"
        ]
        
        for column in test_columns:
            matches = [p for p in direct_patterns if re.search(p.pattern, column, re.IGNORECASE)]
            assert len(matches) > 0, f"No pattern matched column: {column}"
        
        # Test ratio patterns
        ratio_patterns = [p for p in analyzer.METRIC_PATTERNS if p.metric_type == MetricType.RATIO]
        ratio_columns = [
            "conversion_numerator", "retention_denominator", "click_rate"
        ]
        
        for column in ratio_columns:
            matches = [p for p in ratio_patterns if re.search(p.pattern, column, re.IGNORECASE)]
            assert len(matches) > 0, f"No pattern matched column: {column}"