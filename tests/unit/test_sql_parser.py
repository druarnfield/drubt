"""Unit tests for SQL Parser service."""

import pytest
from pathlib import Path
from dbt_metrics_manager.services.sql_parser import SqlParser, ColumnInfo, SqlParseResult


class TestSqlParser:
    """Test the SQL Parser service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SqlParser()
    
    def test_parse_simple_select(self):
        """Test parsing a simple SELECT statement."""
        sql = """
        SELECT 
            customer_id,
            total_orders,
            revenue_value
        FROM customers
        """
        
        result = self.parser.parse_sql(sql)
        
        assert result.model_name == "unknown"
        assert len(result.columns) == 3
        assert result.columns[0].name == "customer_id"
        assert result.columns[1].name == "total_orders"
        assert result.columns[2].name == "revenue_value"
        assert "customers" in result.source_tables
    
    def test_parse_aggregated_columns(self):
        """Test parsing aggregated columns."""
        sql = """
        SELECT 
            customer_id,
            SUM(order_amount) AS total_revenue,
            COUNT(*) AS order_count,
            AVG(order_amount) AS avg_order_value
        FROM orders
        GROUP BY customer_id
        """
        
        result = self.parser.parse_sql(sql)
        
        # Check aggregated columns
        agg_columns = [col for col in result.columns if col.is_aggregated]
        assert len(agg_columns) == 3
        
        # Check function types
        total_revenue = next(col for col in result.columns if col.name == "total_revenue")
        assert total_revenue.is_aggregated
        assert total_revenue.function_type == "SUM"
        
        order_count = next(col for col in result.columns if col.name == "order_count")
        assert order_count.is_aggregated
        assert order_count.function_type == "COUNT"
    
    def test_identify_rollup_model(self):
        """Test identification of rollup models."""
        rollup_sql = """
        SELECT 
            customer_segment,
            SUM(revenue) AS total_revenue_value,
            COUNT(*) AS order_count,
            AVG(order_amount) AS avg_order_numerator
        FROM customer_orders
        GROUP BY customer_segment
        """
        
        result = self.parser.parse_sql(rollup_sql)
        assert result.is_rollup_model
    
    def test_identify_non_rollup_model(self):
        """Test identification of non-rollup models."""
        simple_sql = """
        SELECT 
            customer_id,
            name,
            email
        FROM raw_customers
        """
        
        result = self.parser.parse_sql(simple_sql)
        assert not result.is_rollup_model
    
    def test_get_metric_columns(self):
        """Test extraction of metric columns."""
        sql = """
        SELECT 
            customer_id,
            revenue_value,
            order_count,
            conversion_numerator,
            conversion_denominator,
            regular_column
        FROM customer_metrics
        """
        
        result = self.parser.parse_sql(sql)
        metric_columns = self.parser.get_metric_columns(result)
        
        metric_names = [col.name for col in metric_columns]
        assert "revenue_value" in metric_names
        assert "order_count" in metric_names
        assert "conversion_numerator" in metric_names
        assert "conversion_denominator" in metric_names
        assert "regular_column" not in metric_names
    
    def test_clean_dbt_sql(self):
        """Test cleaning of dbt-specific syntax."""
        dbt_sql = """
        SELECT 
            customer_id,
            revenue
        FROM {{ ref('customers') }}
        WHERE created_at >= '{{ var("start_date") }}'
        """
        
        cleaned = self.parser._clean_dbt_sql(dbt_sql)
        
        assert "{{ ref('customers') }}" not in cleaned
        assert "customers" in cleaned or "placeholder_table" in cleaned
    
    def test_extract_cte_names(self):
        """Test extraction of CTE names."""
        sql = """
        WITH customer_orders AS (
            SELECT customer_id, SUM(amount) as total
            FROM orders
            GROUP BY customer_id
        ),
        customer_segments AS (
            SELECT customer_id, segment
            FROM segments
        )
        SELECT co.customer_id, co.total, cs.segment
        FROM customer_orders co
        JOIN customer_segments cs ON co.customer_id = cs.customer_id
        """
        
        result = self.parser.parse_sql(sql)
        
        assert "customer_orders" in result.cte_names
        assert "customer_segments" in result.cte_names
    
    def test_error_handling_invalid_sql(self):
        """Test error handling with invalid SQL."""
        invalid_sql = """
        SELECT invalid syntax here
        FROM WHERE GROUP BY
        """
        
        result = self.parser.parse_sql(invalid_sql)
        
        # Should still return a result with errors
        assert len(result.errors) > 0
        assert result.raw_sql == invalid_sql
    
    def test_regex_fallback_parsing(self):
        """Test regex fallback when sqlglot fails."""
        # Complex SQL that might cause sqlglot to fail
        complex_sql = """
        SELECT 
            customer_id,
            SUM(revenue) AS total_revenue_value
        FROM customer_data
        """
        
        result = self.parser.parse_sql(complex_sql)
        
        # Should have extracted some columns even if parsing partially failed
        assert len(result.columns) > 0
        assert result.raw_sql == complex_sql
    
    def test_column_info_creation(self):
        """Test ColumnInfo dataclass creation."""
        column = ColumnInfo(
            name="revenue_value",
            expression="SUM(revenue)",
            alias="revenue_value",
            source_table="orders",
            is_aggregated=True,
            function_type="SUM"
        )
        
        assert column.name == "revenue_value"
        assert column.is_aggregated
        assert column.function_type == "SUM"
    
    def test_sql_parse_result_creation(self):
        """Test SqlParseResult dataclass creation."""
        columns = [
            ColumnInfo(name="customer_id", expression="customer_id"),
            ColumnInfo(name="total_value", expression="SUM(amount)", is_aggregated=True)
        ]
        
        result = SqlParseResult(
            file_path="/path/to/model.sql",
            model_name="customer_rollup",
            columns=columns,
            source_tables=["orders"],
            is_rollup_model=True,
            cte_names=["customer_cte"],
            errors=[],
            raw_sql="SELECT * FROM orders"
        )
        
        assert result.model_name == "customer_rollup"
        assert len(result.columns) == 2
        assert result.is_rollup_model
        assert "orders" in result.source_tables
    
    def test_metric_patterns_detection(self):
        """Test detection of metric patterns in column names."""
        test_cases = [
            ("revenue_value", True),
            ("order_count", True),
            ("conversion_numerator", True),
            ("conversion_denominator", True),
            ("total_sum", True),
            ("average_avg", True),
            ("customer_name", False),
            ("created_date", False),
        ]
        
        for column_name, should_be_metric in test_cases:
            sql = f"SELECT {column_name} FROM test_table"
            result = self.parser.parse_sql(sql)
            metric_columns = self.parser.get_metric_columns(result)
            
            is_metric = len(metric_columns) > 0
            assert is_metric == should_be_metric, f"Failed for column: {column_name}"
    
    def test_rollup_indicators_detection(self):
        """Test detection of rollup indicators in SQL."""
        test_cases = [
            ("SELECT SUM(amount) FROM orders GROUP BY customer", True),
            ("SELECT COUNT(*) FROM orders WHERE status = 'completed'", True),
            ("SELECT customer_id FROM raw_customers", False),
            ("SELECT * FROM orders_rollup", True),
            ("SELECT avg_value FROM summary_agg", True),
        ]
        
        for sql, should_be_rollup in test_cases:
            result = self.parser.parse_sql(sql)
            assert result.is_rollup_model == should_be_rollup, f"Failed for SQL: {sql}"


class TestSqlParserFileOperations:
    """Test SQL Parser file operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SqlParser()
    
    def test_parse_file_not_found(self):
        """Test parsing a file that doesn't exist."""
        non_existent_file = Path("/path/that/does/not/exist.sql")
        
        result = self.parser.parse_file(non_existent_file)
        
        assert len(result.errors) > 0
        assert "Failed to read file" in result.errors[0]
        assert result.model_name == "exist"  # From file stem
    
    @pytest.fixture
    def temp_sql_file(self, tmp_path):
        """Create a temporary SQL file for testing."""
        sql_content = """
        SELECT 
            customer_id,
            SUM(revenue) AS total_revenue_value,
            COUNT(*) AS order_count
        FROM customer_orders
        GROUP BY customer_id
        """
        
        sql_file = tmp_path / "test_model.sql"
        sql_file.write_text(sql_content)
        return sql_file
    
    def test_parse_file_success(self, temp_sql_file):
        """Test successful file parsing."""
        result = self.parser.parse_file(temp_sql_file)
        
        assert result.model_name == "test_model"
        assert len(result.columns) == 3
        assert result.is_rollup_model
        assert len(result.errors) == 0
        assert "customer_orders" in result.source_tables
    
    def test_analyze_model_directory(self, tmp_path):
        """Test analyzing a directory of SQL files."""
        # Create test SQL files
        model1 = tmp_path / "model1.sql"
        model1.write_text("SELECT customer_id, revenue_value FROM orders")
        
        model2 = tmp_path / "model2.sql"
        model2.write_text("SELECT SUM(amount) AS total_value FROM payments GROUP BY customer_id")
        
        subdir = tmp_path / "marts"
        subdir.mkdir()
        model3 = subdir / "model3.sql"
        model3.write_text("SELECT customer_name FROM customers")
        
        results = self.parser.analyze_model_directory(tmp_path)
        
        assert len(results) == 3
        assert str(model1) in results
        assert str(model2) in results
        assert str(model3) in results
        
        # Check that model2 is identified as rollup
        model2_result = results[str(model2)]
        assert model2_result.is_rollup_model