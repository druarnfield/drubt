"""DBT project reader service."""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from ..models import DbtModel


class DbtReader:
    """Service for reading DBT project artifacts."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.manifest_path = self.project_path / "target" / "manifest.json"
        self.catalog_path = self.project_path / "target" / "catalog.json"
        self.dbt_project_path = self.project_path / "dbt_project.yml"
        
        self._manifest_cache = None
        self._catalog_cache = None
    
    def validate_project(self) -> Tuple[bool, str]:
        """Validate that this is a valid DBT project."""
        if not self.project_path.exists():
            return False, f"Project path does not exist: {self.project_path}"
        
        if not self.dbt_project_path.exists():
            return False, "No dbt_project.yml found. This doesn't appear to be a DBT project."
        
        if not self.manifest_path.exists():
            return False, "manifest.json not found. Run 'dbt docs generate' first."
        
        try:
            self.load_manifest()
            return True, "Project is valid"
        except Exception as e:
            return False, f"Failed to load manifest.json: {e}"
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load and cache manifest.json."""
        if self._manifest_cache is None:
            try:
                with open(self.manifest_path) as f:
                    self._manifest_cache = json.load(f)
            except Exception as e:
                raise Exception(f"Failed to load manifest.json: {e}")
        
        return self._manifest_cache
    
    def load_catalog(self) -> Dict[str, Any]:
        """Load and cache catalog.json."""
        if self._catalog_cache is None:
            try:
                if self.catalog_path.exists():
                    with open(self.catalog_path) as f:
                        self._catalog_cache = json.load(f)
                else:
                    # Catalog is optional
                    self._catalog_cache = {"nodes": {}}
            except Exception as e:
                # If catalog fails to load, use empty dict
                self._catalog_cache = {"nodes": {}}
        
        return self._catalog_cache
    
    def get_project_name(self) -> str:
        """Get project name from manifest."""
        manifest = self.load_manifest()
        metadata = manifest.get("metadata", {})
        return metadata.get("project_name", "Unknown Project")
    
    def get_rollup_models(self) -> List[DbtModel]:
        """Get all rollup models from manifest."""
        manifest = self.load_manifest()
        catalog = self.load_catalog()
        models = []
        
        for node_id, node in manifest.get("nodes", {}).items():
            if (node.get("resource_type") == "model" and 
                node.get("name", "").startswith("rollup_")):
                
                # Enhance with catalog information if available
                catalog_node = catalog.get("nodes", {}).get(node_id, {})
                if catalog_node:
                    # Add column information from catalog
                    columns_info = catalog_node.get("columns", {})
                    for col_name, col_info in columns_info.items():
                        # Find matching column in manifest and enhance it
                        manifest_columns = node.get("columns", {})
                        if col_name in manifest_columns:
                            manifest_columns[col_name]["data_type"] = col_info.get("type")
                        else:
                            # Add column from catalog if not in manifest
                            manifest_columns[col_name] = {
                                "data_type": col_info.get("type"),
                                "description": col_info.get("comment", "")
                            }
                    node["columns"] = manifest_columns
                
                model = DbtModel.from_manifest_node(node_id, node)
                models.append(model)
        
        return sorted(models, key=lambda m: m.name)
    
    def get_model_by_name(self, name: str) -> DbtModel:
        """Get a specific model by name."""
        models = self.get_rollup_models()
        for model in models:
            if model.name == name:
                return model
        raise ValueError(f"Model '{name}' not found")
    
    def get_model_sql(self, model_name: str) -> str:
        """Get the SQL content for a model."""
        try:
            sql_path = self.project_path / "models" / f"{model_name}.sql"
            if sql_path.exists():
                return sql_path.read_text()
            
            # Try finding in subdirectories
            for sql_file in self.project_path.glob(f"models/**/{model_name}.sql"):
                return sql_file.read_text()
            
            return ""
        except Exception:
            return ""