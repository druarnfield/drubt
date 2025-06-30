"""Metric Analyzer service for discovering metrics in dbt models."""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

from ..models.metric import Metric, MetricType
from ..models.dbt_model import DbtModel
from .sql_parser import SqlParser, SqlParseResult, ColumnInfo


@dataclass
class MetricDiscovery:
    """Result of metric discovery analysis."""
    model_name: str
    file_path: str
    suggested_metrics: List[Metric]
    confidence_score: float
    discovery_notes: List[str]
    column_analysis: Dict[str, str]  # column_name -> analysis notes


@dataclass
class AnalysisContext:
    """Context for metric analysis."""
    model_name: str
    file_path: str
    columns: List[ColumnInfo]
    is_rollup: bool
    source_tables: List[str]
    raw_sql: str


@dataclass
class MetricPattern:
    """Pattern for identifying metrics."""
    pattern: str
    metric_type: MetricType
    confidence_boost: float
    description: str


class MetricAnalyzer:
    """Service for analyzing dbt models and discovering potential metrics."""
    
    # Core metric patterns with confidence scores
    METRIC_PATTERNS = [
        MetricPattern(r'_value$', MetricType.DIRECT, 0.9, "Direct value metric"),
        MetricPattern(r'_count$', MetricType.DIRECT, 0.8, "Count metric"),
        MetricPattern(r'_total$', MetricType.DIRECT, 0.8, "Total metric"),
        MetricPattern(r'_sum$', MetricType.DIRECT, 0.7, "Sum metric"),
        MetricPattern(r'_amount$', MetricType.DIRECT, 0.7, "Amount metric"),
        MetricPattern(r'_avg$', MetricType.DIRECT, 0.6, "Average metric"),
        MetricPattern(r'_mean$', MetricType.DIRECT, 0.6, "Mean metric"),
        MetricPattern(r'_numerator$', MetricType.RATIO, 0.9, "Ratio numerator"),
        MetricPattern(r'_denominator$', MetricType.RATIO, 0.9, "Ratio denominator"),
        MetricPattern(r'_rate$', MetricType.RATIO, 0.7, "Rate metric"),
        MetricPattern(r'_ratio$', MetricType.RATIO, 0.7, "Ratio metric"),
        MetricPattern(r'_percentage$', MetricType.RATIO, 0.6, "Percentage metric"),
        MetricPattern(r'_pct$', MetricType.RATIO, 0.6, "Percentage metric"),
    ]
    
    # Business domain patterns
    BUSINESS_PATTERNS = [
        r'revenue', r'sales', r'income', r'profit', r'cost', r'expense',
        r'conversion', r'retention', r'churn', r'acquisition',
        r'engagement', r'usage', r'activity', r'frequency',
        r'growth', r'performance', r'efficiency', r'productivity'
    ]
    
    # Common aggregation function patterns
    AGGREGATION_PATTERNS = {
        'SUM': 0.8,
        'COUNT': 0.9,
        'AVG': 0.7,
        'AVERAGE': 0.7,
        'MAX': 0.6,
        'MIN': 0.6,
        'MEDIAN': 0.6,
    }
    
    def __init__(self, sql_parser: Optional[SqlParser] = None):
        """Initialize the metric analyzer.
        
        Args:
            sql_parser: SQL parser service (creates one if not provided)
        """
        self.sql_parser = sql_parser or SqlParser()
        self._metric_cache: Dict[str, MetricDiscovery] = {}
    
    def analyze_model(self, model: DbtModel) -> MetricDiscovery:
        """Analyze a dbt model for potential metrics.
        
        Args:
            model: DbtModel to analyze
            
        Returns:
            MetricDiscovery with suggested metrics and analysis
        """
        # Check cache first
        cache_key = f"{model.name}:{model.file_path}"
        if cache_key in self._metric_cache:
            return self._metric_cache[cache_key]
        
        # Parse SQL if available
        sql_result = None
        if model.file_path and Path(model.file_path).exists():
            sql_result = self.sql_parser.parse_file(Path(model.file_path))
        
        # Create analysis context
        context = AnalysisContext(
            model_name=model.name,
            file_path=model.file_path or "",
            columns=sql_result.columns if sql_result else [],
            is_rollup=sql_result.is_rollup_model if sql_result else model.is_rollup,
            source_tables=sql_result.source_tables if sql_result else [],
            raw_sql=sql_result.raw_sql if sql_result else ""
        )
        
        # Perform analysis
        discovery = self._analyze_context(context)
        
        # Cache result
        self._metric_cache[cache_key] = discovery
        
        return discovery
    
    def analyze_sql_file(self, file_path: Path) -> MetricDiscovery:
        """Analyze a SQL file for potential metrics.
        
        Args:
            file_path: Path to SQL file
            
        Returns:
            MetricDiscovery with suggested metrics and analysis
        """
        # Parse SQL
        sql_result = self.sql_parser.parse_file(file_path)
        
        # Create analysis context
        context = AnalysisContext(
            model_name=sql_result.model_name,
            file_path=str(file_path),
            columns=sql_result.columns,
            is_rollup=sql_result.is_rollup_model,
            source_tables=sql_result.source_tables,
            raw_sql=sql_result.raw_sql
        )
        
        return self._analyze_context(context)
    
    def _analyze_context(self, context: AnalysisContext) -> MetricDiscovery:
        """Analyze context and discover metrics.
        
        Args:
            context: Analysis context
            
        Returns:
            MetricDiscovery with results
        """
        suggested_metrics = []
        discovery_notes = []
        column_analysis = {}
        
        # Skip analysis if not a rollup model
        if not context.is_rollup:
            discovery_notes.append("Model does not appear to be a rollup/aggregation model")
            return MetricDiscovery(
                model_name=context.model_name,
                file_path=context.file_path,
                suggested_metrics=[],
                confidence_score=0.0,
                discovery_notes=discovery_notes,
                column_analysis={}
            )
        
        # Analyze columns for metrics
        direct_metrics = self._find_direct_metrics(context)
        ratio_metrics = self._find_ratio_metrics(context)
        custom_metrics = self._find_custom_metrics(context)
        
        # Combine all metrics
        all_metrics = direct_metrics + ratio_metrics + custom_metrics
        
        # Calculate confidence scores
        for metric in all_metrics:
            confidence = self._calculate_metric_confidence(metric, context)
            metric.confidence_score = confidence
        
        # Filter by minimum confidence
        min_confidence = 0.3
        suggested_metrics = [m for m in all_metrics if m.confidence_score >= min_confidence]
        
        # Sort by confidence score
        suggested_metrics.sort(key=lambda m: m.confidence_score, reverse=True)
        
        # Generate analysis notes
        discovery_notes = self._generate_discovery_notes(context, suggested_metrics)
        
        # Generate column analysis
        column_analysis = self._analyze_columns(context)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(suggested_metrics, context)
        
        return MetricDiscovery(
            model_name=context.model_name,
            file_path=context.file_path,
            suggested_metrics=suggested_metrics,
            confidence_score=overall_confidence,
            discovery_notes=discovery_notes,
            column_analysis=column_analysis
        )
    
    def _find_direct_metrics(self, context: AnalysisContext) -> List[Metric]:
        """Find direct metrics (single column metrics).
        
        Args:
            context: Analysis context
            
        Returns:
            List of direct metrics
        """
        metrics = []
        
        for column in context.columns:
            # Check naming patterns
            for pattern in self.METRIC_PATTERNS:
                if pattern.metric_type == MetricType.DIRECT:
                    if re.search(pattern.pattern, column.name, re.IGNORECASE):
                        metric = self._create_direct_metric(column, context, pattern)
                        if metric:
                            metrics.append(metric)
                        break
            
            # Check aggregated columns
            if column.is_aggregated and column.function_type in self.AGGREGATION_PATTERNS:
                # Only create if not already created by naming pattern
                if not any(m.name == self._generate_metric_name(column.name) for m in metrics):
                    metric = self._create_aggregated_metric(column, context)
                    if metric:
                        metrics.append(metric)
        
        return metrics
    
    def _find_ratio_metrics(self, context: AnalysisContext) -> List[Metric]:
        """Find ratio metrics (numerator/denominator pairs).
        
        Args:
            context: Analysis context
            
        Returns:
            List of ratio metrics
        """
        metrics = []
        
        # Group columns by base name
        column_groups = defaultdict(list)
        for column in context.columns:
            base_name = self._extract_base_name(column.name)
            column_groups[base_name].append(column)
        
        # Look for numerator/denominator pairs
        for base_name, columns in column_groups.items():
            numerator_col = None
            denominator_col = None
            
            for column in columns:
                if re.search(r'_numerator$', column.name, re.IGNORECASE):
                    numerator_col = column
                elif re.search(r'_denominator$', column.name, re.IGNORECASE):
                    denominator_col = column
            
            # Create ratio metric if both found
            if numerator_col and denominator_col:
                metric = self._create_ratio_metric(
                    numerator_col, denominator_col, base_name, context
                )
                if metric:
                    metrics.append(metric)
        
        return metrics
    
    def _find_custom_metrics(self, context: AnalysisContext) -> List[Metric]:
        """Find custom metrics (complex calculations).
        
        Args:
            context: Analysis context
            
        Returns:
            List of custom metrics
        """
        metrics = []
        
        # Look for complex expressions in columns
        for column in context.columns:
            if self._is_complex_expression(column):
                metric = self._create_custom_metric(column, context)
                if metric:
                    metrics.append(metric)
        
        return metrics
    
    def _create_direct_metric(self, column: ColumnInfo, context: AnalysisContext, 
                            pattern: MetricPattern) -> Optional[Metric]:
        """Create a direct metric from a column.
        
        Args:
            column: Column information
            context: Analysis context
            pattern: Matching pattern
            
        Returns:
            Metric if created successfully, None otherwise
        """
        name = self._generate_metric_name(column.name)
        short_name = self._generate_short_name(column.name)
        category = self._infer_category(column.name, context.model_name)
        
        return Metric(
            name=name,
            short=short_name,
            type=MetricType.DIRECT,
            category=category,
            value=column.name,
            model_name=context.model_name,
            description=f"Direct metric from {column.name}",
            confidence_score=pattern.confidence_boost
        )
    
    def _create_aggregated_metric(self, column: ColumnInfo, context: AnalysisContext) -> Optional[Metric]:
        """Create a metric from an aggregated column.
        
        Args:
            column: Aggregated column information
            context: Analysis context
            
        Returns:
            Metric if created successfully, None otherwise
        """
        name = self._generate_metric_name(column.name)
        short_name = self._generate_short_name(column.name)
        category = self._infer_category(column.name, context.model_name)
        
        return Metric(
            name=name,
            short=short_name,
            type=MetricType.DIRECT,
            category=category,
            value=column.name,
            model_name=context.model_name,
            description=f"Aggregated metric ({column.function_type}) from {column.name}",
            confidence_score=self.AGGREGATION_PATTERNS.get(column.function_type, 0.5)
        )
    
    def _create_ratio_metric(self, numerator_col: ColumnInfo, denominator_col: ColumnInfo,
                           base_name: str, context: AnalysisContext) -> Optional[Metric]:
        """Create a ratio metric from numerator/denominator columns.
        
        Args:
            numerator_col: Numerator column
            denominator_col: Denominator column
            base_name: Base name for the metric
            context: Analysis context
            
        Returns:
            Ratio metric if created successfully, None otherwise
        """
        name = self._generate_metric_name(base_name)
        short_name = self._generate_short_name(base_name)
        category = self._infer_category(base_name, context.model_name)
        
        return Metric(
            name=name,
            short=short_name,
            type=MetricType.RATIO,
            category=category,
            numerator=numerator_col.name,
            denominator=denominator_col.name,
            model_name=context.model_name,
            description=f"Ratio metric: {numerator_col.name} / {denominator_col.name}",
            confidence_score=0.8
        )
    
    def _create_custom_metric(self, column: ColumnInfo, context: AnalysisContext) -> Optional[Metric]:
        """Create a custom metric from a complex column.
        
        Args:
            column: Column with complex expression
            context: Analysis context
            
        Returns:
            Custom metric if created successfully, None otherwise
        """
        name = self._generate_metric_name(column.name)
        short_name = self._generate_short_name(column.name)
        category = self._infer_category(column.name, context.model_name)
        
        return Metric(
            name=name,
            short=short_name,
            type=MetricType.CUSTOM,
            category=category,
            sql=column.expression,
            model_name=context.model_name,
            description=f"Custom metric with expression: {column.expression}",
            confidence_score=0.4
        )
    
    def _calculate_metric_confidence(self, metric: Metric, context: AnalysisContext) -> float:
        """Calculate confidence score for a metric.
        
        Args:
            metric: Metric to score
            context: Analysis context
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = metric.confidence_score or 0.5
        
        # Boost confidence for business domain terms
        for pattern in self.BUSINESS_PATTERNS:
            if re.search(pattern, metric.name, re.IGNORECASE):
                confidence += 0.1
                break
        
        # Boost confidence for rollup models
        if context.is_rollup:
            confidence += 0.1
        
        # Boost confidence for models with "rollup", "agg", or "summary" in name
        if re.search(r'(rollup|agg|summary)', context.model_name, re.IGNORECASE):
            confidence += 0.15
        
        # Reduce confidence for very generic names
        if metric.name.lower() in ['value', 'count', 'total', 'amount']:
            confidence -= 0.2
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_overall_confidence(self, metrics: List[Metric], context: AnalysisContext) -> float:
        """Calculate overall confidence for the discovery.
        
        Args:
            metrics: List of discovered metrics
            context: Analysis context
            
        Returns:
            Overall confidence score
        """
        if not metrics:
            return 0.0
        
        # Average of metric confidences
        avg_confidence = sum(m.confidence_score for m in metrics) / len(metrics)
        
        # Boost for multiple metrics
        metric_count_boost = min(0.2, len(metrics) * 0.05)
        
        # Boost for rollup models
        rollup_boost = 0.1 if context.is_rollup else 0.0
        
        return min(1.0, avg_confidence + metric_count_boost + rollup_boost)
    
    def _generate_discovery_notes(self, context: AnalysisContext, metrics: List[Metric]) -> List[str]:
        """Generate discovery notes for the analysis.
        
        Args:
            context: Analysis context
            metrics: Discovered metrics
            
        Returns:
            List of discovery notes
        """
        notes = []
        
        if context.is_rollup:
            notes.append("✓ Model identified as rollup/aggregation model")
        
        if metrics:
            notes.append(f"✓ Found {len(metrics)} potential metrics")
            
            # Categorize metrics
            direct_count = sum(1 for m in metrics if m.type == MetricType.DIRECT)
            ratio_count = sum(1 for m in metrics if m.type == MetricType.RATIO)
            custom_count = sum(1 for m in metrics if m.type == MetricType.CUSTOM)
            
            if direct_count > 0:
                notes.append(f"  - {direct_count} direct metrics")
            if ratio_count > 0:
                notes.append(f"  - {ratio_count} ratio metrics")
            if custom_count > 0:
                notes.append(f"  - {custom_count} custom metrics")
        else:
            notes.append("✗ No metrics found meeting confidence threshold")
        
        # Add SQL parsing notes
        if context.columns:
            notes.append(f"✓ Analyzed {len(context.columns)} columns")
        
        return notes
    
    def _analyze_columns(self, context: AnalysisContext) -> Dict[str, str]:
        """Analyze individual columns and provide notes.
        
        Args:
            context: Analysis context
            
        Returns:
            Dictionary mapping column names to analysis notes
        """
        analysis = {}
        
        for column in context.columns:
            notes = []
            
            # Check for metric patterns
            for pattern in self.METRIC_PATTERNS:
                if re.search(pattern.pattern, column.name, re.IGNORECASE):
                    notes.append(f"Matches {pattern.description.lower()}")
                    break
            
            # Check if aggregated
            if column.is_aggregated:
                notes.append(f"Aggregated ({column.function_type})")
            
            # Check for business domain
            for pattern in self.BUSINESS_PATTERNS:
                if re.search(pattern, column.name, re.IGNORECASE):
                    notes.append(f"Business domain: {pattern}")
                    break
            
            if notes:
                analysis[column.name] = "; ".join(notes)
        
        return analysis
    
    def _generate_metric_name(self, column_name: str) -> str:
        """Generate a metric name from a column name.
        
        Args:
            column_name: Original column name
            
        Returns:
            Generated metric name
        """
        # Remove common suffixes
        name = re.sub(r'_(value|count|total|sum|avg|amount)$', '', column_name, flags=re.IGNORECASE)
        
        # Convert to title case
        return name.replace('_', ' ').title()
    
    def _generate_short_name(self, column_name: str) -> str:
        """Generate a short name from a column name.
        
        Args:
            column_name: Original column name
            
        Returns:
            Generated short name
        """
        # Take first 3 letters of each word
        words = column_name.split('_')
        short_parts = [word[:3] for word in words if word]
        return '_'.join(short_parts).lower()
    
    def _infer_category(self, name: str, model_name: str) -> str:
        """Infer category from name and model name.
        
        Args:
            name: Metric or column name
            model_name: Model name
            
        Returns:
            Inferred category
        """
        # Check for specific business categories
        if re.search(r'(revenue|sales|income|profit)', name, re.IGNORECASE):
            return "Financial"
        elif re.search(r'(conversion|retention|churn)', name, re.IGNORECASE):
            return "Marketing"
        elif re.search(r'(engagement|usage|activity)', name, re.IGNORECASE):
            return "Engagement"
        elif re.search(r'(growth|performance)', name, re.IGNORECASE):
            return "Performance"
        
        # Fallback to model name
        if re.search(r'customer', model_name, re.IGNORECASE):
            return "Customer"
        elif re.search(r'order', model_name, re.IGNORECASE):
            return "Order"
        elif re.search(r'product', model_name, re.IGNORECASE):
            return "Product"
        
        return "General"
    
    def _extract_base_name(self, column_name: str) -> str:
        """Extract base name from column name (remove suffix).
        
        Args:
            column_name: Column name
            
        Returns:
            Base name without suffix
        """
        # Remove common metric suffixes
        return re.sub(r'_(numerator|denominator|value|count|total|sum|avg|amount)$', 
                     '', column_name, flags=re.IGNORECASE)
    
    def _is_complex_expression(self, column: ColumnInfo) -> bool:
        """Check if column has a complex expression.
        
        Args:
            column: Column information
            
        Returns:
            True if expression is complex
        """
        expression = column.expression.lower()
        
        # Check for mathematical operations
        if re.search(r'[+\-*/]', expression):
            return True
        
        # Check for CASE statements
        if 'case' in expression:
            return True
        
        # Check for function calls beyond simple aggregation
        if re.search(r'\b(round|ceil|floor|abs|coalesce|least|greatest)\b', expression):
            return True
        
        return False
    
    def batch_analyze_models(self, models: List[DbtModel]) -> List[MetricDiscovery]:
        """Analyze multiple models in batch.
        
        Args:
            models: List of DbtModel objects
            
        Returns:
            List of MetricDiscovery results
        """
        results = []
        
        for model in models:
            try:
                discovery = self.analyze_model(model)
                results.append(discovery)
            except Exception as e:
                # Create error result
                error_discovery = MetricDiscovery(
                    model_name=model.name,
                    file_path=model.file_path or "",
                    suggested_metrics=[],
                    confidence_score=0.0,
                    discovery_notes=[f"Analysis failed: {e}"],
                    column_analysis={}
                )
                results.append(error_discovery)
        
        return results
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self._metric_cache.clear()