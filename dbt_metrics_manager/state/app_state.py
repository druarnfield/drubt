"""Global application state management."""

import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from ..models import Metric, DbtModel
from ..config import get_config


class AppState:
    """Global application state with persistence."""
    
    def __init__(self):
        self.config = get_config()
        self.db_path = self.config.db_file
        self._init_database()
        
        # Project state
        self.project_path: str = ""
        self.project_loaded: bool = False
        self.project_name: str = ""
        
        # Data
        self.models: List[DbtModel] = []
        self.metrics: List[Metric] = []
        self.discovered_metrics: List[Metric] = []
        
        # UI state
        self.loading: bool = False
        self.loading_message: str = ""
        self.error_message: str = ""
        self.success_message: str = ""
        
        # Services (lazy loaded)
        self._dbt_reader = None
        self._analyzer = None
        self._seed_manager = None
    
    def _init_database(self) -> None:
        """Initialize SQLite database for persistence."""
        self.config.app_dir.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_history (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    name TEXT,
                    last_opened TIMESTAMP,
                    model_count INTEGER,
                    metric_count INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
    
    def load_project(self, path: str) -> bool:
        """Load a dbt project from specified path."""
        try:
            self.loading = True
            self.error_message = ""
            self.loading_message = "Validating project..."
            
            # Import here to avoid circular imports
            from ..services import DbtReader
            
            # Validate project
            self._dbt_reader = DbtReader(path)
            valid, message = self._dbt_reader.validate_project()
            
            if not valid:
                self.error_message = message
                return False
            
            # Load project data
            self.loading_message = "Loading models..."
            self.project_path = path
            self.project_name = self._dbt_reader.get_project_name()
            self.models = self._dbt_reader.get_rollup_models()
            
            self.loading_message = "Loading existing metrics..."
            # TODO: Load existing metrics when seed manager is implemented
            self.metrics = []
            
            self.project_loaded = True
            self._save_project_to_history()
            
            self.success_message = f"Loaded project: {self.project_name}"
            return True
            
        except Exception as e:
            self.error_message = str(e)
            return False
        finally:
            self.loading = False
            self.loading_message = ""
    
    def _save_project_to_history(self) -> None:
        """Save project to recent history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO project_history 
                (path, name, last_opened, model_count, metric_count)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.project_path,
                self.project_name,
                datetime.now(),
                len(self.models),
                len(self.metrics)
            ))
    
    def get_recent_projects(self) -> List[Dict[str, Any]]:
        """Get recently opened projects."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT path, name, last_opened, model_count, metric_count
                FROM project_history
                ORDER BY last_opened DESC
                LIMIT 10
            """)
            
            return [
                {
                    "path": row[0],
                    "name": row[1],
                    "last_opened": row[2],
                    "model_count": row[3],
                    "metric_count": row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def clear_error(self) -> None:
        """Clear error message."""
        self.error_message = ""
    
    def clear_success(self) -> None:
        """Clear success message."""
        self.success_message = ""
    
    @property
    def total_metrics(self) -> int:
        """Total number of defined metrics."""
        return len(self.metrics)
    
    @property
    def total_models(self) -> int:
        """Total number of rollup models."""
        return len(self.models)
    
    @property
    def models_with_metrics(self) -> int:
        """Number of models that have metrics defined."""
        model_names = {metric.source_model for metric in self.metrics if metric.source_model}
        return len(model_names)
    
    @property
    def coverage_percentage(self) -> float:
        """Percentage of models with at least one metric."""
        if not self.models:
            return 0.0
        return (self.models_with_metrics / len(self.models)) * 100