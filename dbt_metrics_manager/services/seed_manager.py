"""Seed Manager service for reading and writing metric_definitions.csv files."""

import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, asdict
import shutil
from datetime import datetime

from ..models.metric import Metric, MetricType


@dataclass
class SeedValidationResult:
    """Result of validating a seed file."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    row_count: int
    duplicate_names: List[str]
    missing_required_fields: List[str]


@dataclass
class SeedBackup:
    """Information about a seed file backup."""
    backup_path: str
    original_path: str
    timestamp: datetime
    reason: str


class SeedManager:
    """Service for managing metric_definitions.csv seed files."""
    
    # Standard CSV column names for metric definitions
    REQUIRED_COLUMNS = [
        'name',
        'short',
        'type',
        'category'
    ]
    
    OPTIONAL_COLUMNS = [
        'value',
        'numerator', 
        'denominator',
        'sql',
        'model_name',
        'description',
        'owner',
        'tags',
        'created_date',
        'updated_date'
    ]
    
    ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    
    # Valid metric types
    VALID_TYPES = {t.value for t in MetricType}
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize the seed manager.
        
        Args:
            backup_dir: Directory for storing backups (defaults to ~/.dbt_metrics/backups)
        """
        self.backup_dir = backup_dir or Path.home() / '.dbt_metrics' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._backups: List[SeedBackup] = []
    
    def read_seed_file(self, file_path: Path) -> List[Metric]:
        """Read metrics from a CSV seed file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of Metric objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Seed file not found: {file_path}")
        
        try:
            # Read CSV with pandas for better handling
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            
            # Convert to metrics
            metrics = []
            for _, row in df.iterrows():
                metric = self._row_to_metric(row.to_dict())
                if metric:
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            raise ValueError(f"Failed to read seed file: {e}")
    
    def write_seed_file(self, file_path: Path, metrics: List[Metric], 
                       backup: bool = True) -> None:
        """Write metrics to a CSV seed file.
        
        Args:
            file_path: Path to write the CSV file
            metrics: List of Metric objects to write
            backup: Whether to create a backup of existing file
            
        Raises:
            ValueError: If metrics data is invalid
        """
        # Validate metrics
        validation = self.validate_metrics(metrics)
        if not validation.is_valid:
            raise ValueError(f"Invalid metrics data: {'; '.join(validation.errors)}")
        
        # Create backup if file exists and backup is requested
        if backup and file_path.exists():
            self._create_backup(file_path, "Pre-write backup")
        
        # Prepare data for CSV
        rows = []
        for metric in metrics:
            row = self._metric_to_row(metric)
            rows.append(row)
        
        # Create DataFrame and write to CSV
        df = pd.DataFrame(rows, columns=self.ALL_COLUMNS)
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            df.to_csv(file_path, index=False, na_rep='')
        except Exception as e:
            raise ValueError(f"Failed to write seed file: {e}")
    
    def validate_seed_file(self, file_path: Path) -> SeedValidationResult:
        """Validate a seed file without loading all data.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            SeedValidationResult with validation details
        """
        if not file_path.exists():
            return SeedValidationResult(
                is_valid=False,
                errors=[f"File does not exist: {file_path}"],
                warnings=[],
                row_count=0,
                duplicate_names=[],
                missing_required_fields=[]
            )
        
        errors = []
        warnings = []
        duplicate_names = []
        missing_required_fields = []
        row_count = 0
        
        try:
            # Read CSV headers
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            row_count = len(df)
            
            # Check required columns
            missing_columns = [col for col in self.REQUIRED_COLUMNS 
                             if col not in df.columns]
            if missing_columns:
                missing_required_fields = missing_columns
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Check for unknown columns
            unknown_columns = [col for col in df.columns 
                             if col not in self.ALL_COLUMNS]
            if unknown_columns:
                warnings.append(f"Unknown columns will be ignored: {', '.join(unknown_columns)}")
            
            # Check for duplicate names
            if 'name' in df.columns:
                name_counts = df['name'].value_counts()
                duplicates = name_counts[name_counts > 1].index.tolist()
                if duplicates:
                    duplicate_names = duplicates
                    errors.append(f"Duplicate metric names: {', '.join(duplicates)}")
            
            # Validate metric types
            if 'type' in df.columns:
                invalid_types = df[~df['type'].isin(self.VALID_TYPES)]['type'].unique()
                if len(invalid_types) > 0:
                    errors.append(f"Invalid metric types: {', '.join(invalid_types)}")
            
            # Check for empty required fields
            for col in self.REQUIRED_COLUMNS:
                if col in df.columns:
                    empty_count = df[col].isna().sum() + (df[col] == '').sum()
                    if empty_count > 0:
                        warnings.append(f"Column '{col}' has {empty_count} empty values")
            
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
        
        return SeedValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=row_count,
            duplicate_names=duplicate_names,
            missing_required_fields=missing_required_fields
        )
    
    def validate_metrics(self, metrics: List[Metric]) -> SeedValidationResult:
        """Validate a list of metrics.
        
        Args:
            metrics: List of metrics to validate
            
        Returns:
            SeedValidationResult with validation details
        """
        errors = []
        warnings = []
        duplicate_names = []
        
        # Check for duplicates
        names = [metric.name for metric in metrics]
        seen_names = set()
        for name in names:
            if name in seen_names:
                duplicate_names.append(name)
            seen_names.add(name)
        
        if duplicate_names:
            errors.append(f"Duplicate metric names: {', '.join(set(duplicate_names))}")
        
        # Validate individual metrics
        for i, metric in enumerate(metrics):
            metric_errors = metric.validate()
            if metric_errors:
                errors.extend([f"Row {i+1}: {error}" for error in metric_errors])
        
        return SeedValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=len(metrics),
            duplicate_names=list(set(duplicate_names)),
            missing_required_fields=[]
        )
    
    def merge_metrics(self, existing_metrics: List[Metric], 
                     new_metrics: List[Metric]) -> List[Metric]:
        """Merge new metrics with existing metrics.
        
        Args:
            existing_metrics: Current metrics from seed file
            new_metrics: New metrics to merge
            
        Returns:
            Combined list of metrics with duplicates resolved
        """
        # Create lookup of existing metrics by name
        existing_by_name = {metric.name: metric for metric in existing_metrics}
        
        # Start with existing metrics
        merged = existing_metrics.copy()
        
        # Add or update with new metrics
        for new_metric in new_metrics:
            if new_metric.name in existing_by_name:
                # Update existing metric
                existing_idx = next(i for i, m in enumerate(merged) 
                                  if m.name == new_metric.name)
                merged[existing_idx] = new_metric
            else:
                # Add new metric
                merged.append(new_metric)
        
        return merged
    
    def add_metrics(self, file_path: Path, new_metrics: List[Metric]) -> None:
        """Add new metrics to an existing seed file.
        
        Args:
            file_path: Path to the seed file
            new_metrics: List of new metrics to add
        """
        # Read existing metrics
        existing_metrics = []
        if file_path.exists():
            existing_metrics = self.read_seed_file(file_path)
        
        # Merge with new metrics
        merged_metrics = self.merge_metrics(existing_metrics, new_metrics)
        
        # Write back to file
        self.write_seed_file(file_path, merged_metrics)
    
    def remove_metrics(self, file_path: Path, metric_names: List[str]) -> int:
        """Remove metrics from a seed file by name.
        
        Args:
            file_path: Path to the seed file
            metric_names: List of metric names to remove
            
        Returns:
            Number of metrics removed
        """
        if not file_path.exists():
            return 0
        
        # Read existing metrics
        existing_metrics = self.read_seed_file(file_path)
        
        # Filter out metrics to remove
        names_to_remove = set(metric_names)
        filtered_metrics = [m for m in existing_metrics 
                          if m.name not in names_to_remove]
        
        removed_count = len(existing_metrics) - len(filtered_metrics)
        
        # Write back to file
        if removed_count > 0:
            self.write_seed_file(file_path, filtered_metrics)
        
        return removed_count
    
    def update_metric(self, file_path: Path, updated_metric: Metric) -> bool:
        """Update a single metric in a seed file.
        
        Args:
            file_path: Path to the seed file
            updated_metric: Updated metric data
            
        Returns:
            True if metric was found and updated, False otherwise
        """
        if not file_path.exists():
            return False
        
        # Read existing metrics
        existing_metrics = self.read_seed_file(file_path)
        
        # Find and update the metric
        updated = False
        for i, metric in enumerate(existing_metrics):
            if metric.name == updated_metric.name:
                existing_metrics[i] = updated_metric
                updated = True
                break
        
        # Write back to file if updated
        if updated:
            self.write_seed_file(file_path, existing_metrics)
        
        return updated
    
    def find_seed_files(self, project_dir: Path) -> List[Path]:
        """Find metric_definitions.csv files in a dbt project.
        
        Args:
            project_dir: Root directory of dbt project
            
        Returns:
            List of paths to seed files
        """
        seed_files = []
        
        # Common locations for seed files
        common_paths = [
            project_dir / "data" / "metric_definitions.csv",
            project_dir / "seeds" / "metric_definitions.csv",
            project_dir / "data" / "metrics" / "metric_definitions.csv",
            project_dir / "seeds" / "metrics" / "metric_definitions.csv",
        ]
        
        # Check common paths
        for path in common_paths:
            if path.exists():
                seed_files.append(path)
        
        # Search for any metric_definitions.csv files
        for seed_file in project_dir.rglob("metric_definitions.csv"):
            if seed_file not in seed_files:
                seed_files.append(seed_file)
        
        return seed_files
    
    def create_seed_template(self, file_path: Path, sample_data: bool = True) -> None:
        """Create a new seed file template.
        
        Args:
            file_path: Path where to create the template
            sample_data: Whether to include sample data
        """
        metrics = []
        
        if sample_data:
            # Add sample metrics
            metrics = [
                Metric(
                    name="Total Revenue",
                    short="total_rev",
                    type=MetricType.DIRECT,
                    category="Financial",
                    value="revenue_value",
                    model_name="customer_rollup",
                    description="Total revenue from all customers",
                    owner="data-team"
                ),
                Metric(
                    name="Conversion Rate",
                    short="conv_rate",
                    type=MetricType.RATIO,
                    category="Marketing",
                    numerator="conversions_numerator",
                    denominator="conversions_denominator",
                    model_name="conversion_rollup",
                    description="Customer conversion rate",
                    owner="marketing-team"
                ),
                Metric(
                    name="Customer LTV",
                    short="cust_ltv",
                    type=MetricType.CUSTOM,
                    category="Financial",
                    sql="SUM(revenue) / COUNT(DISTINCT customer_id) * 24",
                    model_name="customer_rollup",
                    description="Customer lifetime value (24 month estimate)",
                    owner="analytics-team"
                )
            ]
        
        self.write_seed_file(file_path, metrics, backup=False)
    
    def _row_to_metric(self, row: Dict[str, str]) -> Optional[Metric]:
        """Convert a CSV row to a Metric object.
        
        Args:
            row: Dictionary representing a CSV row
            
        Returns:
            Metric object or None if conversion fails
        """
        try:
            # Handle empty/null values
            cleaned_row = {k: v if v and v.strip() else None for k, v in row.items()}
            
            # Required fields
            name = cleaned_row.get('name')
            short = cleaned_row.get('short')
            type_str = cleaned_row.get('type')
            category = cleaned_row.get('category', 'General')
            
            if not all([name, short, type_str]):
                return None
            
            # Convert type string to MetricType
            try:
                metric_type = MetricType(type_str)
            except ValueError:
                return None
            
            # Optional fields
            value = cleaned_row.get('value')
            numerator = cleaned_row.get('numerator')
            denominator = cleaned_row.get('denominator')
            sql = cleaned_row.get('sql')
            model_name = cleaned_row.get('model_name')
            description = cleaned_row.get('description')
            owner = cleaned_row.get('owner')
            tags = cleaned_row.get('tags')
            
            # Parse tags if present
            tags_list = []
            if tags:
                tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            return Metric(
                name=name,
                short=short,
                type=metric_type,
                category=category,
                value=value,
                numerator=numerator,
                denominator=denominator,
                sql=sql,
                model_name=model_name,
                description=description,
                owner=owner,
                tags=tags_list if tags_list else None
            )
            
        except Exception:
            return None
    
    def _metric_to_row(self, metric: Metric) -> Dict[str, str]:
        """Convert a Metric object to a CSV row.
        
        Args:
            metric: Metric object to convert
            
        Returns:
            Dictionary representing a CSV row
        """
        # Start with empty row
        row = {col: '' for col in self.ALL_COLUMNS}
        
        # Fill in metric data
        row['name'] = metric.name or ''
        row['short'] = metric.short or ''
        row['type'] = metric.type.value if metric.type else ''
        row['category'] = metric.category or ''
        row['value'] = metric.value or ''
        row['numerator'] = metric.numerator or ''
        row['denominator'] = metric.denominator or ''
        row['sql'] = metric.sql or ''
        row['model_name'] = metric.model_name or ''
        row['description'] = metric.description or ''
        row['owner'] = metric.owner or ''
        
        # Handle tags as comma-separated string
        if metric.tags:
            row['tags'] = ', '.join(metric.tags)
        
        # Add timestamps if available
        if hasattr(metric, 'created_date') and metric.created_date:
            row['created_date'] = metric.created_date.isoformat()
        if hasattr(metric, 'updated_date') and metric.updated_date:
            row['updated_date'] = metric.updated_date.isoformat()
        
        return row
    
    def _create_backup(self, file_path: Path, reason: str) -> SeedBackup:
        """Create a backup of a seed file.
        
        Args:
            file_path: Path to the file to backup
            reason: Reason for the backup
            
        Returns:
            SeedBackup information
        """
        timestamp = datetime.now()
        backup_filename = f"{file_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
        backup_path = self.backup_dir / backup_filename
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        # Create backup record
        backup = SeedBackup(
            backup_path=str(backup_path),
            original_path=str(file_path),
            timestamp=timestamp,
            reason=reason
        )
        
        self._backups.append(backup)
        
        return backup
    
    def list_backups(self, original_path: Optional[Path] = None) -> List[SeedBackup]:
        """List available backups.
        
        Args:
            original_path: Filter by original file path (optional)
            
        Returns:
            List of available backups
        """
        if original_path:
            return [b for b in self._backups if b.original_path == str(original_path)]
        return self._backups.copy()
    
    def restore_backup(self, backup: SeedBackup) -> None:
        """Restore a file from backup.
        
        Args:
            backup: Backup to restore
        """
        backup_path = Path(backup.backup_path)
        original_path = Path(backup.original_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Create backup of current file before restore
        if original_path.exists():
            self._create_backup(original_path, "Pre-restore backup")
        
        # Copy backup to original location
        shutil.copy2(backup_path, original_path)
    
    def get_metrics_summary(self, metrics: List[Metric]) -> Dict[str, int]:
        """Get summary statistics for a list of metrics.
        
        Args:
            metrics: List of metrics to summarize
            
        Returns:
            Dictionary with summary statistics
        """
        total = len(metrics)
        
        type_counts = {}
        for metric_type in MetricType:
            count = sum(1 for m in metrics if m.type == metric_type)
            type_counts[metric_type.value] = count
        
        category_counts = {}
        for metric in metrics:
            category = metric.category or 'Unknown'
            category_counts[category] = category_counts.get(category, 0) + 1
        
        model_counts = {}
        for metric in metrics:
            model = metric.model_name or 'Unknown'
            model_counts[model] = model_counts.get(model, 0) + 1
        
        return {
            'total': total,
            'by_type': type_counts,
            'by_category': category_counts,
            'by_model': model_counts
        }