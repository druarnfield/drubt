"""Unit tests for DbtReader service."""

import pytest
import json
import tempfile
from pathlib import Path

from dbt_metrics_manager.services import DbtReader


@pytest.fixture
def temp_dbt_project():
    """Create temporary dbt project for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create basic dbt project structure
        target_dir = project_dir / "target"
        target_dir.mkdir()
        
        # Create dbt_project.yml
        dbt_project = {
            "name": "test_project",
            "version": "1.0.0",
            "profile": "test"
        }
        with open(project_dir / "dbt_project.yml", "w") as f:
            json.dump(dbt_project, f)
        
        # Create minimal manifest.json
        manifest = {
            "metadata": {"project_name": "test_project"},
            "nodes": {
                "model.test_project.rollup_emergency": {
                    "name": "rollup_emergency",
                    "resource_type": "model",
                    "database": "analytics",
                    "schema": "marts",
                    "description": "Emergency rollup model",
                    "columns": {
                        "presentations_value": {
                            "name": "presentations_value",
                            "description": "Total presentations",
                            "data_type": "INTEGER"
                        },
                        "los_4hr_numerator": {
                            "name": "los_4hr_numerator", 
                            "description": "LOS under 4 hours count",
                            "data_type": "INTEGER"
                        }
                    },
                    "original_file_path": "models/rollup/rollup_emergency.sql"
                },
                "model.test_project.regular_model": {
                    "name": "regular_model",
                    "resource_type": "model",
                    "database": "analytics", 
                    "schema": "staging"
                }
            }
        }
        
        with open(target_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        yield project_dir


def test_validate_project_valid(temp_dbt_project):
    """Test validation of valid dbt project."""
    reader = DbtReader(str(temp_dbt_project))
    valid, message = reader.validate_project()
    
    assert valid
    assert message == "Project is valid"


def test_validate_project_invalid_path():
    """Test validation with invalid project path."""
    reader = DbtReader("/invalid/path")
    valid, message = reader.validate_project()
    
    assert not valid
    assert "Project path does not exist" in message


def test_validate_project_no_manifest(temp_dbt_project):
    """Test validation when manifest.json is missing."""
    # Remove manifest.json
    manifest_path = temp_dbt_project / "target" / "manifest.json"
    manifest_path.unlink()
    
    reader = DbtReader(str(temp_dbt_project))
    valid, message = reader.validate_project()
    
    assert not valid
    assert "manifest.json not found" in message


def test_get_project_name(temp_dbt_project):
    """Test getting project name from manifest."""
    reader = DbtReader(str(temp_dbt_project))
    name = reader.get_project_name()
    
    assert name == "test_project"


def test_get_rollup_models(temp_dbt_project):
    """Test getting rollup models from manifest."""
    reader = DbtReader(str(temp_dbt_project))
    models = reader.get_rollup_models()
    
    assert len(models) == 1
    model = models[0]
    assert model.name == "rollup_emergency"
    assert model.database == "analytics"
    assert model.schema == "marts"
    assert len(model.columns) == 2
    
    # Check columns
    column_names = [col.name for col in model.columns]
    assert "presentations_value" in column_names
    assert "los_4hr_numerator" in column_names


def test_get_model_by_name(temp_dbt_project):
    """Test getting specific model by name."""
    reader = DbtReader(str(temp_dbt_project))
    model = reader.get_model_by_name("rollup_emergency")
    
    assert model.name == "rollup_emergency"
    assert model.is_rollup_model


def test_get_model_by_name_not_found(temp_dbt_project):
    """Test getting non-existent model."""
    reader = DbtReader(str(temp_dbt_project))
    
    with pytest.raises(ValueError, match="Model 'nonexistent' not found"):
        reader.get_model_by_name("nonexistent")