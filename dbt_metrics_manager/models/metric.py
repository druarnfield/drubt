"""Metric data model."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Metric:
    """Core metric data model."""
    
    # Required fields
    metric_category: str
    name: str
    short: str
    type: str  # "direct", "ratio", "custom"
    
    # Type-specific fields
    value: Optional[str] = None
    numerator: Optional[str] = None
    denominator: Optional[str] = None
    expression: Optional[str] = None
    
    # Optional metadata
    multiplier: Optional[int] = None
    description: Optional[str] = None
    source_model: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamps on creation."""
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            "metric_category": self.metric_category,
            "name": self.name,
            "short": self.short,
            "type": self.type,
            "value": self.value or "",
            "numerator": self.numerator or "",
            "denominator": self.denominator or "",
            "expression": self.expression or "",
            "multiplier": self.multiplier or "",
            "description": self.description or "",
            "source_model": self.source_model or "",
            "tags": ",".join(self.tags) if self.tags else ""
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create from dictionary."""
        tags = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
        
        return cls(
            metric_category=data["metric_category"],
            name=data["name"],
            short=data["short"],
            type=data["type"],
            value=data.get("value") or None,
            numerator=data.get("numerator") or None,
            denominator=data.get("denominator") or None,
            expression=data.get("expression") or None,
            multiplier=int(data["multiplier"]) if data.get("multiplier") else None,
            description=data.get("description") or None,
            source_model=data.get("source_model") or None,
            tags=tags
        )
    
    def validate(self) -> List[str]:
        """Validate metric configuration."""
        errors = []
        
        if not self.name.strip():
            errors.append("Name is required")
        
        if not self.short.strip():
            errors.append("Short code is required")
        
        if self.type not in ["direct", "ratio", "custom"]:
            errors.append("Type must be direct, ratio, or custom")
        
        if self.type == "direct" and not self.value:
            errors.append("Direct metrics require a value column")
        
        if self.type == "ratio" and (not self.numerator or not self.denominator):
            errors.append("Ratio metrics require numerator and denominator")
        
        if self.type == "custom" and not self.expression:
            errors.append("Custom metrics require an expression")
        
        return errors