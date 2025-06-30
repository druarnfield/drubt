"""Unit tests for Seed Manager service."""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime

from dbt_metrics_manager.services.seed_manager import (
    SeedManager, SeedValidationResult, SeedBackup
)
from dbt_metrics_manager.models.metric import Metric, MetricType


class TestSeedManager:
    """Test the Seed Manager service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.seed_manager = SeedManager()
    
    def test_create_seed_template(self, tmp_path):
        """Test creating a seed file template."""
        seed_file = tmp_path / "metric_definitions.csv"
        
        # Create template with sample data
        self.seed_manager.create_seed_template(seed_file, sample_data=True)
        
        assert seed_file.exists()
        
        # Read back and verify
        metrics = self.seed_manager.read_seed_file(seed_file)
        assert len(metrics) == 3
        assert any(m.name == "Total Revenue" for m in metrics)
        assert any(m.type == MetricType.RATIO for m in metrics)
    
    def test_create_empty_template(self, tmp_path):
        """Test creating an empty seed file template."""
        seed_file = tmp_path / "empty_metrics.csv"
        
        # Create template without sample data
        self.seed_manager.create_seed_template(seed_file, sample_data=False)
        
        assert seed_file.exists()
        
        # Should have headers but no data
        metrics = self.seed_manager.read_seed_file(seed_file)
        assert len(metrics) == 0
    
    def test_write_and_read_metrics(self, tmp_path):
        """Test writing and reading metrics."""
        seed_file = tmp_path / "test_metrics.csv"
        
        # Create test metrics
        test_metrics = [
            Metric(
                name="Revenue",
                short="rev",
                type=MetricType.DIRECT,
                category="Financial",
                value="revenue_value",
                model_name="revenue_rollup"
            ),
            Metric(
                name="Conversion Rate",
                short="conv",
                type=MetricType.RATIO,
                category="Marketing",
                numerator="conversions_numerator",
                denominator="conversions_denominator"
            )
        ]
        
        # Write metrics
        self.seed_manager.write_seed_file(seed_file, test_metrics, backup=False)
        
        # Read back
        read_metrics = self.seed_manager.read_seed_file(seed_file)
        
        assert len(read_metrics) == 2
        assert read_metrics[0].name == "Revenue"
        assert read_metrics[0].type == MetricType.DIRECT
        assert read_metrics[1].name == "Conversion Rate"
        assert read_metrics[1].type == MetricType.RATIO
    
    def test_validate_valid_seed_file(self, tmp_path):
        """Test validation of a valid seed file."""
        seed_file = tmp_path / "valid_metrics.csv"
        
        # Create valid CSV
        df = pd.DataFrame({
            'name': ['Revenue', 'Orders'],
            'short': ['rev', 'ord'],
            'type': ['direct', 'direct'],
            'category': ['Financial', 'Sales'],
            'value': ['revenue_value', 'order_count']
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert validation.is_valid
        assert len(validation.errors) == 0
        assert validation.row_count == 2
    
    def test_validate_invalid_seed_file(self, tmp_path):
        """Test validation of an invalid seed file."""
        seed_file = tmp_path / "invalid_metrics.csv"
        
        # Create invalid CSV (missing required columns, duplicates)
        df = pd.DataFrame({
            'name': ['Revenue', 'Revenue'],  # Duplicate
            'short': ['rev', 'rev2'],
            'type': ['invalid_type', 'direct'],  # Invalid type
            # Missing 'category' column
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert not validation.is_valid
        assert len(validation.errors) > 0
        assert 'Revenue' in validation.duplicate_names
        assert 'category' in validation.missing_required_fields
    
    def test_validate_metrics_list(self):
        """Test validation of a metrics list."""
        # Valid metrics
        valid_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial"),
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales")
        ]
        
        validation = self.seed_manager.validate_metrics(valid_metrics)
        assert validation.is_valid
        
        # Invalid metrics (duplicates)
        invalid_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial"),
            Metric(name="Revenue", short="rev2", type=MetricType.DIRECT, category="Sales")
        ]
        
        validation = self.seed_manager.validate_metrics(invalid_metrics)
        assert not validation.is_valid
        assert "Revenue" in validation.duplicate_names
    
    def test_merge_metrics(self):
        """Test merging existing and new metrics."""
        existing_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial"),
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales")
        ]
        
        new_metrics = [
            Metric(name="Revenue", short="rev_new", type=MetricType.DIRECT, category="Financial"),  # Update
            Metric(name="Conversion", short="conv", type=MetricType.RATIO, category="Marketing")  # Add
        ]
        
        merged = self.seed_manager.merge_metrics(existing_metrics, new_metrics)
        
        assert len(merged) == 3
        
        # Revenue should be updated
        revenue_metric = next(m for m in merged if m.name == "Revenue")
        assert revenue_metric.short == "rev_new"
        
        # Orders should remain unchanged
        orders_metric = next(m for m in merged if m.name == "Orders")
        assert orders_metric.short == "ord"
        
        # Conversion should be added
        conversion_metric = next(m for m in merged if m.name == "Conversion")
        assert conversion_metric.category == "Marketing"
    
    def test_add_metrics_to_file(self, tmp_path):
        """Test adding metrics to an existing file."""
        seed_file = tmp_path / "existing_metrics.csv"
        
        # Create initial metrics
        initial_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial")
        ]
        self.seed_manager.write_seed_file(seed_file, initial_metrics, backup=False)
        
        # Add new metrics
        new_metrics = [
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales"),
            Metric(name="Conversion", short="conv", type=MetricType.RATIO, category="Marketing")
        ]
        self.seed_manager.add_metrics(seed_file, new_metrics)
        
        # Verify all metrics are present
        all_metrics = self.seed_manager.read_seed_file(seed_file)
        assert len(all_metrics) == 3
        
        metric_names = [m.name for m in all_metrics]
        assert "Revenue" in metric_names
        assert "Orders" in metric_names
        assert "Conversion" in metric_names
    
    def test_remove_metrics_from_file(self, tmp_path):
        """Test removing metrics from a file."""
        seed_file = tmp_path / "metrics_to_remove.csv"
        
        # Create initial metrics
        initial_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial"),
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales"),
            Metric(name="Conversion", short="conv", type=MetricType.RATIO, category="Marketing")
        ]
        self.seed_manager.write_seed_file(seed_file, initial_metrics, backup=False)
        
        # Remove some metrics
        removed_count = self.seed_manager.remove_metrics(seed_file, ["Orders", "Conversion"])
        
        assert removed_count == 2
        
        # Verify only Revenue remains
        remaining_metrics = self.seed_manager.read_seed_file(seed_file)
        assert len(remaining_metrics) == 1
        assert remaining_metrics[0].name == "Revenue"
    
    def test_update_metric_in_file(self, tmp_path):
        """Test updating a single metric in a file."""
        seed_file = tmp_path / "metrics_to_update.csv"
        
        # Create initial metrics
        initial_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial"),
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales")
        ]
        self.seed_manager.write_seed_file(seed_file, initial_metrics, backup=False)
        
        # Update Revenue metric
        updated_metric = Metric(
            name="Revenue",
            short="rev_updated",
            type=MetricType.DIRECT,
            category="Financial",
            description="Updated description"
        )
        
        success = self.seed_manager.update_metric(seed_file, updated_metric)
        assert success
        
        # Verify update
        metrics = self.seed_manager.read_seed_file(seed_file)
        revenue_metric = next(m for m in metrics if m.name == "Revenue")
        assert revenue_metric.short == "rev_updated"
        assert revenue_metric.description == "Updated description"
    
    def test_find_seed_files(self, tmp_path):
        """Test finding seed files in a project directory."""
        # Create project structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        seeds_dir = tmp_path / "seeds"
        seeds_dir.mkdir()
        metrics_dir = tmp_path / "data" / "metrics"
        metrics_dir.mkdir()
        
        # Create seed files in different locations
        (data_dir / "metric_definitions.csv").touch()
        (seeds_dir / "metric_definitions.csv").touch()
        (metrics_dir / "metric_definitions.csv").touch()
        
        found_files = self.seed_manager.find_seed_files(tmp_path)
        
        assert len(found_files) == 3
        found_paths = [str(f) for f in found_files]
        assert str(data_dir / "metric_definitions.csv") in found_paths
        assert str(seeds_dir / "metric_definitions.csv") in found_paths
        assert str(metrics_dir / "metric_definitions.csv") in found_paths
    
    def test_metrics_summary(self):
        """Test getting metrics summary statistics."""
        metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial", model_name="model1"),
            Metric(name="Orders", short="ord", type=MetricType.DIRECT, category="Sales", model_name="model1"),
            Metric(name="Conversion", short="conv", type=MetricType.RATIO, category="Marketing", model_name="model2"),
            Metric(name="LTV", short="ltv", type=MetricType.CUSTOM, category="Financial", model_name="model2")
        ]
        
        summary = self.seed_manager.get_metrics_summary(metrics)
        
        assert summary['total'] == 4
        assert summary['by_type']['direct'] == 2
        assert summary['by_type']['ratio'] == 1
        assert summary['by_type']['custom'] == 1
        assert summary['by_category']['Financial'] == 2
        assert summary['by_category']['Sales'] == 1
        assert summary['by_category']['Marketing'] == 1
        assert summary['by_model']['model1'] == 2
        assert summary['by_model']['model2'] == 2
    
    def test_row_to_metric_conversion(self):
        """Test converting CSV row to Metric object."""
        # Valid row
        valid_row = {
            'name': 'Revenue',
            'short': 'rev',
            'type': 'direct',
            'category': 'Financial',
            'value': 'revenue_value',
            'model_name': 'revenue_model',
            'description': 'Total revenue',
            'tags': 'financial, important'
        }
        
        metric = self.seed_manager._row_to_metric(valid_row)
        
        assert metric is not None
        assert metric.name == 'Revenue'
        assert metric.type == MetricType.DIRECT
        assert metric.tags == ['financial', 'important']
    
    def test_row_to_metric_invalid(self):
        """Test converting invalid CSV row."""
        # Missing required fields
        invalid_row = {
            'name': 'Revenue',
            # Missing 'short' and 'type'
            'category': 'Financial'
        }
        
        metric = self.seed_manager._row_to_metric(invalid_row)
        assert metric is None
    
    def test_metric_to_row_conversion(self):
        """Test converting Metric object to CSV row."""
        metric = Metric(
            name="Revenue",
            short="rev",
            type=MetricType.DIRECT,
            category="Financial",
            value="revenue_value",
            description="Total revenue",
            tags=["financial", "important"]
        )
        
        row = self.seed_manager._metric_to_row(metric)
        
        assert row['name'] == 'Revenue'
        assert row['short'] == 'rev'
        assert row['type'] == 'direct'
        assert row['category'] == 'Financial'
        assert row['value'] == 'revenue_value'
        assert row['description'] == 'Total revenue'
        assert row['tags'] == 'financial, important'
    
    def test_file_not_found_error(self):
        """Test handling of missing files."""
        non_existent_file = Path("/path/that/does/not/exist.csv")
        
        with pytest.raises(FileNotFoundError):
            self.seed_manager.read_seed_file(non_existent_file)
        
        # Validation should handle missing files gracefully
        validation = self.seed_manager.validate_seed_file(non_existent_file)
        assert not validation.is_valid
        assert "does not exist" in validation.errors[0]


class TestSeedBackup:
    """Test seed file backup functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.seed_manager = SeedManager()
    
    def test_backup_creation(self, tmp_path):
        """Test creating backups of seed files."""
        seed_file = tmp_path / "test_metrics.csv"
        
        # Create initial file
        metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial")
        ]
        self.seed_manager.write_seed_file(seed_file, metrics, backup=False)
        
        # Create backup manually
        backup = self.seed_manager._create_backup(seed_file, "Test backup")
        
        assert Path(backup.backup_path).exists()
        assert backup.original_path == str(seed_file)
        assert backup.reason == "Test backup"
        assert isinstance(backup.timestamp, datetime)
    
    def test_automatic_backup_on_write(self, tmp_path):
        """Test automatic backup creation when writing to existing file."""
        seed_file = tmp_path / "auto_backup_test.csv"
        
        # Create initial file
        initial_metrics = [
            Metric(name="Revenue", short="rev", type=MetricType.DIRECT, category="Financial")
        ]
        self.seed_manager.write_seed_file(seed_file, initial_metrics, backup=False)
        
        # Update file (should create backup)
        updated_metrics = [
            Metric(name="Revenue Updated", short="rev_up", type=MetricType.DIRECT, category="Financial")
        ]
        self.seed_manager.write_seed_file(seed_file, updated_metrics, backup=True)
        
        # Check that backup was created
        backups = self.seed_manager.list_backups(seed_file)
        assert len(backups) == 1
        assert "Pre-write backup" in backups[0].reason
    
    def test_list_backups(self, tmp_path):
        """Test listing backups."""
        seed_file1 = tmp_path / "file1.csv"
        seed_file2 = tmp_path / "file2.csv"
        
        # Create files and backups
        for file_path in [seed_file1, seed_file2]:
            metrics = [Metric(name="Test", short="test", type=MetricType.DIRECT, category="Test")]
            self.seed_manager.write_seed_file(file_path, metrics, backup=False)
            self.seed_manager._create_backup(file_path, "Test backup")
        
        # List all backups
        all_backups = self.seed_manager.list_backups()
        assert len(all_backups) == 2
        
        # List backups for specific file
        file1_backups = self.seed_manager.list_backups(seed_file1)
        assert len(file1_backups) == 1
        assert file1_backups[0].original_path == str(seed_file1)
    
    def test_restore_backup(self, tmp_path):
        """Test restoring from backup."""
        seed_file = tmp_path / "restore_test.csv"
        
        # Create initial file
        initial_metrics = [
            Metric(name="Original", short="orig", type=MetricType.DIRECT, category="Test")
        ]
        self.seed_manager.write_seed_file(seed_file, initial_metrics, backup=False)
        
        # Create backup
        backup = self.seed_manager._create_backup(seed_file, "Before changes")
        
        # Modify file
        modified_metrics = [
            Metric(name="Modified", short="mod", type=MetricType.DIRECT, category="Test")
        ]
        self.seed_manager.write_seed_file(seed_file, modified_metrics, backup=False)
        
        # Restore from backup
        self.seed_manager.restore_backup(backup)
        
        # Verify restoration
        restored_metrics = self.seed_manager.read_seed_file(seed_file)
        assert len(restored_metrics) == 1
        assert restored_metrics[0].name == "Original"


class TestSeedValidation:
    """Test comprehensive seed file validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.seed_manager = SeedManager()
    
    def test_required_columns_validation(self, tmp_path):
        """Test validation of required columns."""
        seed_file = tmp_path / "missing_columns.csv"
        
        # Create CSV missing required columns
        df = pd.DataFrame({
            'name': ['Revenue'],
            'type': ['direct'],
            # Missing 'short' and 'category'
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert not validation.is_valid
        assert 'short' in validation.missing_required_fields
        assert 'category' in validation.missing_required_fields
    
    def test_unknown_columns_warning(self, tmp_path):
        """Test warning for unknown columns."""
        seed_file = tmp_path / "unknown_columns.csv"
        
        # Create CSV with unknown columns
        df = pd.DataFrame({
            'name': ['Revenue'],
            'short': ['rev'],
            'type': ['direct'],
            'category': ['Financial'],
            'unknown_column': ['some_value'],
            'another_unknown': ['another_value']
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert validation.is_valid  # Should still be valid
        assert len(validation.warnings) > 0
        assert any("unknown_column" in warning for warning in validation.warnings)
    
    def test_duplicate_names_validation(self, tmp_path):
        """Test validation of duplicate metric names."""
        seed_file = tmp_path / "duplicates.csv"
        
        # Create CSV with duplicate names
        df = pd.DataFrame({
            'name': ['Revenue', 'Orders', 'Revenue'],
            'short': ['rev1', 'ord', 'rev2'],
            'type': ['direct', 'direct', 'direct'],
            'category': ['Financial', 'Sales', 'Financial']
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert not validation.is_valid
        assert 'Revenue' in validation.duplicate_names
        assert len(validation.duplicate_names) == 1
    
    def test_invalid_metric_types(self, tmp_path):
        """Test validation of metric types."""
        seed_file = tmp_path / "invalid_types.csv"
        
        # Create CSV with invalid metric types
        df = pd.DataFrame({
            'name': ['Revenue', 'Orders'],
            'short': ['rev', 'ord'],
            'type': ['invalid_type', 'direct'],
            'category': ['Financial', 'Sales']
        })
        df.to_csv(seed_file, index=False)
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        assert not validation.is_valid
        assert any("invalid_type" in error for error in validation.errors)
    
    def test_empty_required_fields_warning(self, tmp_path):
        """Test warning for empty required fields."""
        seed_file = tmp_path / "empty_fields.csv"
        
        # Create CSV with empty required fields
        df = pd.DataFrame({
            'name': ['Revenue', ''],  # Empty name
            'short': ['rev', 'ord'],
            'type': ['direct', ''],   # Empty type
            'category': ['Financial', 'Sales']
        })
        df.to_csv(seed_file, index=False, na_rep='')
        
        validation = self.seed_manager.validate_seed_file(seed_file)
        
        # Should have warnings about empty values
        assert len(validation.warnings) > 0
        assert any("empty values" in warning for warning in validation.warnings)