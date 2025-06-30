"""SQL Parser service for analyzing dbt SQL files using sqlglot."""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import sqlglot
from sqlglot import exp


@dataclass
class ColumnInfo:
    """Information about a column in a SQL query."""
    name: str
    expression: str
    alias: Optional[str] = None
    source_table: Optional[str] = None
    is_aggregated: bool = False
    function_type: Optional[str] = None  # SUM, COUNT, AVG, etc.


@dataclass
class SqlParseResult:
    """Result of parsing a SQL file."""
    file_path: str
    model_name: str
    columns: List[ColumnInfo]
    source_tables: List[str]
    is_rollup_model: bool
    cte_names: List[str]
    errors: List[str]
    raw_sql: str


class SqlParser:
    """Service for parsing dbt SQL files and extracting column information."""
    
    # Patterns for identifying rollup models
    ROLLUP_INDICATORS = [
        r'\brollup\b',
        r'\bgroup\s+by\b',
        r'\bsum\s*\(',
        r'\bcount\s*\(',
        r'\bavg\s*\(',
        r'\bmax\s*\(',
        r'\bmin\s*\(',
        r'_rollup',
        r'_agg',
        r'_summary'
    ]
    
    # Patterns for metric columns
    METRIC_PATTERNS = [
        r'_value$',
        r'_count$',
        r'_numerator$',
        r'_denominator$',
        r'_sum$',
        r'_avg$',
        r'_total$'
    ]
    
    def __init__(self):
        """Initialize the SQL parser."""
        self.dialect = "bigquery"  # Default to BigQuery, can be configured
    
    def parse_file(self, file_path: Path) -> SqlParseResult:
        """Parse a SQL file and extract column and table information.
        
        Args:
            file_path: Path to the SQL file to parse
            
        Returns:
            SqlParseResult with parsed information
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_sql = f.read()
        except Exception as e:
            return SqlParseResult(
                file_path=str(file_path),
                model_name=file_path.stem,
                columns=[],
                source_tables=[],
                is_rollup_model=False,
                cte_names=[],
                errors=[f"Failed to read file: {e}"],
                raw_sql=""
            )
        
        return self.parse_sql(raw_sql, str(file_path))
    
    def parse_sql(self, sql: str, source_path: str = "") -> SqlParseResult:
        """Parse SQL content and extract information.
        
        Args:
            sql: SQL content to parse
            source_path: Path to the source file (for error reporting)
            
        Returns:
            SqlParseResult with parsed information
        """
        model_name = Path(source_path).stem if source_path else "unknown"
        errors = []
        
        try:
            # Clean the SQL (remove dbt-specific syntax)
            cleaned_sql = self._clean_dbt_sql(sql)
            
            # Parse with sqlglot
            parsed = sqlglot.parse_one(cleaned_sql, dialect=self.dialect)
            
            if not parsed:
                errors.append("Failed to parse SQL")
                return SqlParseResult(
                    file_path=source_path,
                    model_name=model_name,
                    columns=[],
                    source_tables=[],
                    is_rollup_model=False,
                    cte_names=[],
                    errors=errors,
                    raw_sql=sql
                )
            
            # Extract information from parsed SQL
            columns = self._extract_columns(parsed)
            source_tables = self._extract_source_tables(parsed)
            cte_names = self._extract_cte_names(parsed)
            is_rollup = self._is_rollup_model(sql, columns)
            
        except Exception as e:
            errors.append(f"SQL parsing error: {e}")
            # Fallback to regex-based parsing for basic info
            columns = self._regex_extract_columns(sql)
            source_tables = self._regex_extract_tables(sql)
            cte_names = self._regex_extract_ctes(sql)
            is_rollup = self._is_rollup_model(sql, columns)
        
        return SqlParseResult(
            file_path=source_path,
            model_name=model_name,
            columns=columns,
            source_tables=source_tables,
            is_rollup_model=is_rollup,
            cte_names=cte_names,
            errors=errors,
            raw_sql=sql
        )
    
    def _clean_dbt_sql(self, sql: str) -> str:
        """Remove dbt-specific syntax that sqlglot can't handle.
        
        Args:
            sql: Raw SQL with dbt syntax
            
        Returns:
            Cleaned SQL that sqlglot can parse
        """
        # Remove dbt macros and functions
        sql = re.sub(r'\{\{[^}]+\}\}', 'placeholder_table', sql)
        
        # Remove dbt comments
        sql = re.sub(r'\{#[^#]*#\}', '', sql)
        
        # Remove dbt configurations
        sql = re.sub(r'\{\{[^}]*config[^}]*\}\}', '', sql)
        
        # Replace ref() calls with table names
        sql = re.sub(r'\{\{\s*ref\([\'"]([^\'"]+)[\'"]\)\s*\}\}', r'\1', sql)
        
        # Replace source() calls with table names
        sql = re.sub(r'\{\{\s*source\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"]\)\s*\}\}', r'\1.\2', sql)
        
        return sql
    
    def _extract_columns(self, parsed: exp.Expression) -> List[ColumnInfo]:
        """Extract column information from parsed SQL.
        
        Args:
            parsed: Parsed SQL expression
            
        Returns:
            List of ColumnInfo objects
        """
        columns = []
        
        # Find SELECT statement
        select_stmt = parsed.find(exp.Select)
        if not select_stmt:
            return columns
        
        # Extract columns from SELECT expressions
        for expr in select_stmt.expressions:
            column_info = self._analyze_expression(expr)
            if column_info:
                columns.append(column_info)
        
        return columns
    
    def _analyze_expression(self, expr: exp.Expression) -> Optional[ColumnInfo]:
        """Analyze a SELECT expression to extract column information.
        
        Args:
            expr: SQL expression to analyze
            
        Returns:
            ColumnInfo if column can be extracted, None otherwise
        """
        # Get the alias (column name)
        alias = expr.alias if expr.alias else None
        
        # Determine the column name
        if alias:
            name = alias
        elif isinstance(expr, exp.Column):
            name = expr.name
        else:
            name = str(expr)
        
        # Check if it's an aggregated column
        is_aggregated = bool(expr.find(exp.AggFunc))
        
        # Get function type if it's aggregated
        function_type = None
        if is_aggregated:
            agg_func = expr.find(exp.AggFunc)
            if agg_func:
                function_type = agg_func.__class__.__name__.upper()
        
        # Get source table if it's a simple column reference
        source_table = None
        if isinstance(expr, exp.Column) and expr.table:
            source_table = str(expr.table)
        
        return ColumnInfo(
            name=name,
            expression=str(expr),
            alias=alias,
            source_table=source_table,
            is_aggregated=is_aggregated,
            function_type=function_type
        )
    
    def _extract_source_tables(self, parsed: exp.Expression) -> List[str]:
        """Extract source table names from parsed SQL.
        
        Args:
            parsed: Parsed SQL expression
            
        Returns:
            List of source table names
        """
        tables = set()
        
        # Find all table references
        for table in parsed.find_all(exp.Table):
            tables.add(str(table))
        
        return list(tables)
    
    def _extract_cte_names(self, parsed: exp.Expression) -> List[str]:
        """Extract CTE (Common Table Expression) names from parsed SQL.
        
        Args:
            parsed: Parsed SQL expression
            
        Returns:
            List of CTE names
        """
        cte_names = []
        
        # Find all CTEs
        for cte in parsed.find_all(exp.CTE):
            if cte.alias:
                cte_names.append(cte.alias)
        
        return cte_names
    
    def _is_rollup_model(self, sql: str, columns: List[ColumnInfo]) -> bool:
        """Determine if this is a rollup model based on SQL content and columns.
        
        Args:
            sql: Raw SQL content
            columns: Extracted column information
            
        Returns:
            True if this appears to be a rollup model
        """
        sql_lower = sql.lower()
        
        # Check for rollup indicators in SQL
        for pattern in self.ROLLUP_INDICATORS:
            if re.search(pattern, sql_lower, re.IGNORECASE):
                return True
        
        # Check for aggregated columns
        has_aggregated = any(col.is_aggregated for col in columns)
        if has_aggregated:
            return True
        
        # Check for metric column patterns
        metric_columns = [col for col in columns 
                         if any(re.search(pattern, col.name, re.IGNORECASE) 
                               for pattern in self.METRIC_PATTERNS)]
        
        return len(metric_columns) > 0
    
    def _regex_extract_columns(self, sql: str) -> List[ColumnInfo]:
        """Fallback regex-based column extraction.
        
        Args:
            sql: SQL content
            
        Returns:
            List of ColumnInfo objects
        """
        columns = []
        
        # Simple regex to find SELECT columns
        select_pattern = r'SELECT\s+(.+?)\s+FROM'
        match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            columns_text = match.group(1)
            # Split by comma (simple approach)
            column_parts = [part.strip() for part in columns_text.split(',')]
            
            for part in column_parts:
                # Check for alias
                alias_match = re.search(r'(.+)\s+AS\s+(\w+)', part, re.IGNORECASE)
                if alias_match:
                    expression = alias_match.group(1).strip()
                    name = alias_match.group(2).strip()
                else:
                    expression = part
                    name = part.strip()
                
                # Check if aggregated
                is_aggregated = bool(re.search(r'\b(SUM|COUNT|AVG|MAX|MIN)\s*\(', expression, re.IGNORECASE))
                
                columns.append(ColumnInfo(
                    name=name,
                    expression=expression,
                    is_aggregated=is_aggregated
                ))
        
        return columns
    
    def _regex_extract_tables(self, sql: str) -> List[str]:
        """Fallback regex-based table extraction.
        
        Args:
            sql: SQL content
            
        Returns:
            List of table names
        """
        tables = set()
        
        # Find FROM clauses
        from_pattern = r'FROM\s+(\w+)'
        for match in re.finditer(from_pattern, sql, re.IGNORECASE):
            tables.add(match.group(1))
        
        # Find JOIN clauses
        join_pattern = r'JOIN\s+(\w+)'
        for match in re.finditer(join_pattern, sql, re.IGNORECASE):
            tables.add(match.group(1))
        
        return list(tables)
    
    def _regex_extract_ctes(self, sql: str) -> List[str]:
        """Fallback regex-based CTE extraction.
        
        Args:
            sql: SQL content
            
        Returns:
            List of CTE names
        """
        cte_names = []
        
        # Find WITH clauses
        with_pattern = r'WITH\s+(\w+)\s+AS\s*\('
        for match in re.finditer(with_pattern, sql, re.IGNORECASE):
            cte_names.append(match.group(1))
        
        return cte_names
    
    def get_metric_columns(self, parse_result: SqlParseResult) -> List[ColumnInfo]:
        """Get columns that appear to be metrics based on naming patterns.
        
        Args:
            parse_result: Result from parsing SQL
            
        Returns:
            List of columns that appear to be metrics
        """
        metric_columns = []
        
        for column in parse_result.columns:
            # Check naming patterns
            for pattern in self.METRIC_PATTERNS:
                if re.search(pattern, column.name, re.IGNORECASE):
                    metric_columns.append(column)
                    break
            # Also include aggregated columns
                elif column.is_aggregated:
                    metric_columns.append(column)
        
        return metric_columns
    
    def analyze_model_directory(self, models_dir: Path) -> Dict[str, SqlParseResult]:
        """Analyze all SQL files in a models directory.
        
        Args:
            models_dir: Path to the models directory
            
        Returns:
            Dictionary mapping file paths to parse results
        """
        results = {}
        
        # Find all SQL files
        sql_files = list(models_dir.rglob("*.sql"))
        
        for sql_file in sql_files:
            try:
                result = self.parse_file(sql_file)
                results[str(sql_file)] = result
            except Exception as e:
                # Create error result
                results[str(sql_file)] = SqlParseResult(
                    file_path=str(sql_file),
                    model_name=sql_file.stem,
                    columns=[],
                    source_tables=[],
                    is_rollup_model=False,
                    cte_names=[],
                    errors=[f"Failed to parse file: {e}"],
                    raw_sql=""
                )
        
        return results