"""DBT model data model."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class DbtColumn:
    """DBT model column information."""
    name: str
    data_type: Optional[str] = None
    description: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DbtModel:
    """DBT model representation."""
    
    # Identity
    unique_id: str
    name: str
    
    # Location
    database: Optional[str] = None
    schema: Optional[str] = None
    alias: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    
    # File information
    original_file_path: Optional[str] = None
    raw_sql: Optional[str] = None
    
    # Columns
    columns: List[DbtColumn] = field(default_factory=list)
    
    # Relationships
    depends_on: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        """Get full qualified name."""
        parts = []
        if self.database:
            parts.append(self.database)
        if self.schema:
            parts.append(self.schema)
        parts.append(self.alias or self.name)
        return ".".join(parts)
    
    @property
    def is_rollup_model(self) -> bool:
        """Check if this is a rollup model."""
        return self.name.startswith("rollup_")
    
    def get_column_names(self) -> List[str]:
        """Get list of column names."""
        return [col.name for col in self.columns]
    
    def get_metric_columns(self) -> List[str]:
        """Get columns that might be metrics."""
        metric_patterns = [
            "_value", "_count", "_numerator", "_denominator"
        ]
        
        metric_cols = []
        for col in self.columns:
            if any(col.name.endswith(pattern) for pattern in metric_patterns):
                metric_cols.append(col.name)
        
        return metric_cols
    
    @classmethod
    def from_manifest_node(cls, node_id: str, node: Dict[str, Any]) -> "DbtModel":
        """Create DbtModel from manifest node."""
        columns = []
        for col_name, col_data in node.get("columns", {}).items():
            columns.append(DbtColumn(
                name=col_name,
                data_type=col_data.get("data_type"),
                description=col_data.get("description"),
                meta=col_data.get("meta", {})
            ))
        
        return cls(
            unique_id=node_id,
            name=node["name"],
            database=node.get("database"),
            schema=node.get("schema"),
            alias=node.get("alias"),
            description=node.get("description"),
            tags=node.get("tags", []),
            meta=node.get("meta", {}),
            original_file_path=node.get("original_file_path"),
            raw_sql=node.get("raw_sql"),
            columns=columns,
            depends_on=node.get("depends_on", {}).get("nodes", [])
        )