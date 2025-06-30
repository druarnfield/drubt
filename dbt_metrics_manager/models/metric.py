"""Metric data model."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MetricType(Enum):
    """Enumeration of metric types."""
    DIRECT = "direct"
    RATIO = "ratio"
    CUSTOM = "custom"


@dataclass
class Metric:
    """Core metric data model."""
    
    # Required fields
    name: str
    short: str
    type: MetricType
    category: Optional[str] = None  # For backward compatibility
    
    # Legacy field for backward compatibility
    metric_category: Optional[str] = None
    
    # Type-specific fields
    value: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    sql: Optional[str] = None  # Renamed from expression for consistency
    expression: Optional[str] = None  # Keep for backward compatibility
    
    # Optional metadata
    multiplier: Optional[int] = None
    description: Optional[str] = None
    model_name: Optional[str] = None  # Renamed from source_model
    source_model: Optional[str] = None  # Keep for backward compatibility
    owner: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_date: Optional[datetime] = None  # For backward compatibility
    updated_date: Optional[datetime] = None  # For backward compatibility
    
    def __post_init__(self):
        """Set timestamps and handle backward compatibility."""
        now = datetime.now()
        
        if self.created_at is None:
            self.created_at = now
            self.created_date = now  # Backward compatibility
        self.updated_at = now
        self.updated_date = now  # Backward compatibility
        
        # Handle backward compatibility for category
        if self.metric_category and not self.category:
            self.category = self.metric_category
        elif self.category and not self.metric_category:
            self.metric_category = self.category
        
        # Handle backward compatibility for model name
        if self.source_model and not self.model_name:
            self.model_name = self.source_model
        elif self.model_name and not self.source_model:
            self.source_model = self.model_name
        
        # Handle backward compatibility for expression/sql
        if self.expression and not self.sql:
            self.sql = self.expression
        elif self.sql and not self.expression:
            self.expression = self.sql
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            "name": self.name,
            "short": self.short,
            "type": self.type.value if isinstance(self.type, MetricType) else self.type,
            "category": self.category or "",
            "value": self.value or "",
            "numerator": self.numerator or "",
            "denominator": self.denominator or "",
            "sql": self.sql or "",
            "model_name": self.model_name or "",
            "description": self.description or "",
            "owner": self.owner or "",
            "tags": ",".join(self.tags) if self.tags else "",
            "multiplier": self.multiplier or "",
            # Legacy fields for backward compatibility
            "metric_category": self.metric_category or self.category or "",
            "expression": self.expression or self.sql or "",
            "source_model": self.source_model or self.model_name or "",
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create from dictionary."""
        tags_str = data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None
        
        # Handle type conversion
        type_value = data.get("type", "")
        if isinstance(type_value, str):
            try:
                metric_type = MetricType(type_value)
            except ValueError:
                # Fallback for invalid types
                metric_type = MetricType.DIRECT
        else:
            metric_type = type_value
        
        return cls(
            name=data["name"],
            short=data["short"],
            type=metric_type,
            category=data.get("category") or data.get("metric_category"),
            value=data.get("value") or None,
            numerator=data.get("numerator") or None,
            denominator=data.get("denominator") or None,
            sql=data.get("sql") or data.get("expression") or None,
            model_name=data.get("model_name") or data.get("source_model") or None,
            description=data.get("description") or None,
            owner=data.get("owner") or None,
            multiplier=int(data["multiplier"]) if data.get("multiplier") else None,
            tags=tags,
            # Set legacy fields for backward compatibility
            metric_category=data.get("metric_category"),
            expression=data.get("expression"),
            source_model=data.get("source_model")
        )
    
    def validate(self) -> List[str]:
        """Validate metric configuration."""
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Name is required")
        
        if not self.short or not self.short.strip():
            errors.append("Short code is required")
        
        if not isinstance(self.type, MetricType):
            errors.append("Type must be a valid MetricType")
        else:
            if self.type == MetricType.DIRECT and not self.value:
                errors.append("Direct metrics require a value column")
            
            if self.type == MetricType.RATIO and (not self.numerator or not self.denominator):
                errors.append("Ratio metrics require numerator and denominator")
            
            if self.type == MetricType.CUSTOM and not (self.sql or self.expression):
                errors.append("Custom metrics require a SQL expression")
        
        return errors