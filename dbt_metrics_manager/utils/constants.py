"""Application constants."""

DEFAULT_PATTERNS = {
    "direct_value": r".*_value$",
    "direct_count": r".*_count$",
    "ratio_numerator": r".*_numerator$",
    "ratio_denominator": r".*_denominator$",
}

SYSTEM_COLUMNS = {
    "id", "created_at", "updated_at", "_fivetran_synced", 
    "_dbt_source_relation", "_dbt_copied_at", "etl_updated"
}

METRIC_TYPES = {
    "direct": "Direct",
    "ratio": "Ratio", 
    "custom": "Custom"
}

DEFAULT_CONFIG = {
    "ui": {
        "theme": "dark",
        "items_per_page": 20,
        "auto_save": True,
        "show_line_numbers": True
    },
    "project": {
        "default_path": "",
        "auto_discover": True,
        "backup_count": 10
    },
    "patterns": DEFAULT_PATTERNS
}