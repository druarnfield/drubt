"""Model tree widget for hierarchical model navigation."""

from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.widgets import Tree, Static
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message

from ..models.dbt_model import DbtModel
# from ..services.sql_parser import SqlParseResult  # TODO: Implement in Phase 2


@dataclass
class ModelNodeData:
    """Data associated with a tree node."""
    model: Optional[DbtModel] = None
    path: Optional[str] = None
    is_directory: bool = False
    # sql_result: Optional[SqlParseResult] = None  # TODO: Implement in Phase 2


class ModelTree(Widget):
    """Widget for displaying and navigating dbt models in a tree structure."""
    
    # Reactive attributes
    selected_model: reactive[Optional[DbtModel]] = reactive(None)
    show_rollup_only: reactive[bool] = reactive(False)
    
    def __init__(
        self,
        models: List[DbtModel],
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """Initialize the model tree.
        
        Args:
            models: List of dbt models to display
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.models = models
        self.models_by_path: Dict[str, DbtModel] = {}
        self.tree: Optional[Tree] = None
        self._build_models_index()
    
    class ModelSelected(Message):
        """Message sent when a model is selected."""
        
        def __init__(self, model: DbtModel) -> None:
            self.model = model
            super().__init__()
    
    class ModelDetailsRequested(Message):
        """Message sent when model details are requested."""
        
        def __init__(self, model: DbtModel) -> None:
            self.model = model
            super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create the tree widget."""
        self.tree = Tree("Models", id="model-tree")
        self.tree.show_root = True
        self.tree.show_guides = True
        yield self.tree
    
    def on_mount(self) -> None:
        """Initialize tree when mounted."""
        if self.tree:
            self._populate_tree()
    
    def _build_models_index(self) -> None:
        """Build index of models by path for quick lookup."""
        for model in self.models:
            if model.file_path:
                self.models_by_path[model.file_path] = model
    
    def _populate_tree(self) -> None:
        """Populate the tree with model data."""
        if not self.tree:
            return
        
        # Clear existing tree
        self.tree.clear()
        
        # Filter models if needed
        models_to_show = self._filter_models()
        
        # Group models by directory structure
        directory_structure = self._build_directory_structure(models_to_show)
        
        # Add nodes to tree
        self._add_directory_nodes(self.tree.root, directory_structure)
    
    def _filter_models(self) -> List[DbtModel]:
        """Filter models based on current settings."""
        if self.show_rollup_only:
            return [model for model in self.models if model.is_rollup]
        return self.models
    
    def _build_directory_structure(self, models: List[DbtModel]) -> Dict:
        """Build hierarchical directory structure from model paths."""
        structure = {}
        
        for model in models:
            if not model.file_path:
                # Add to root for models without file paths
                if "__root__" not in structure:
                    structure["__root__"] = {"models": [], "subdirs": {}}
                structure["__root__"]["models"].append(model)
                continue
            
            # Parse path components
            path = Path(model.file_path)
            parts = path.parts[:-1]  # Exclude filename
            filename = path.name
            
            # Build nested structure
            current = structure
            for part in parts:
                if part not in current:
                    current[part] = {"models": [], "subdirs": {}}
                current = current[part]["subdirs"]
            
            # Add model to the appropriate directory
            if "models" not in current:
                current["models"] = []
            current["models"].append(model)
        
        return structure
    
    def _add_directory_nodes(self, parent_node, structure: Dict) -> None:
        """Recursively add directory nodes to the tree."""
        for name, content in structure.items():
            if name == "__root__":
                # Add root models directly
                for model in content.get("models", []):
                    self._add_model_node(parent_node, model)
            else:
                # Create directory node
                dir_node = parent_node.add(
                    self._format_directory_name(name),
                    data=ModelNodeData(path=name, is_directory=True)
                )
                
                # Add models in this directory
                for model in content.get("models", []):
                    self._add_model_node(dir_node, model)
                
                # Add subdirectories
                if content.get("subdirs"):
                    self._add_directory_nodes(dir_node, content["subdirs"])
    
    def _add_model_node(self, parent_node, model: DbtModel) -> None:
        """Add a model node to the tree."""
        label = self._format_model_name(model)
        node = parent_node.add(
            label,
            data=ModelNodeData(model=model, path=model.file_path)
        )
        
        # Add model details as child nodes if expanded
        if model.columns:
            columns_node = node.add("📊 Columns", expand=False)
            for column in model.columns[:10]:  # Limit to first 10
                columns_node.add(f"  {column}", expand=False)
            if len(model.columns) > 10:
                columns_node.add(f"  ... and {len(model.columns) - 10} more")
    
    def _format_directory_name(self, name: str) -> str:
        """Format directory name for display."""
        return f"📁 {name}"
    
    def _format_model_name(self, model: DbtModel) -> str:
        """Format model name for display."""
        icon = "📈" if model.is_rollup else "📄"
        status = " (rollup)" if model.is_rollup else ""
        return f"{icon} {model.name}{status}"
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        if event.node.data and isinstance(event.node.data, ModelNodeData):
            if event.node.data.model:
                self.selected_model = event.node.data.model
                self.post_message(self.ModelSelected(event.node.data.model))
    
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Handle tree node highlighting."""
        if event.node.data and isinstance(event.node.data, ModelNodeData):
            if event.node.data.model:
                # Could emit a preview message here
                pass
    
    def watch_show_rollup_only(self, show_rollup_only: bool) -> None:
        """React to changes in rollup filter."""
        if self.tree:
            self._populate_tree()
    
    def refresh_models(self, models: List[DbtModel]) -> None:
        """Update the tree with new model data."""
        self.models = models
        self._build_models_index()
        if self.tree:
            self._populate_tree()
    
    def expand_model_path(self, model_path: str) -> None:
        """Expand tree to show a specific model path."""
        if not self.tree:
            return
        
        # Find and expand path to model
        path_parts = Path(model_path).parts[:-1]
        current_node = self.tree.root
        
        for part in path_parts:
            for child in current_node.children:
                if (child.data and 
                    isinstance(child.data, ModelNodeData) and 
                    child.data.path == part):
                    child.expand()
                    current_node = child
                    break
    
    def select_model(self, model_name: str) -> bool:
        """Select a model by name."""
        model = next((m for m in self.models if m.name == model_name), None)
        if model:
            self.selected_model = model
            # Could also highlight the node in the tree
            return True
        return False
    
    def get_visible_models(self) -> List[DbtModel]:
        """Get list of currently visible models (after filtering)."""
        return self._filter_models()
    
    def get_rollup_models(self) -> List[DbtModel]:
        """Get list of rollup models."""
        return [model for model in self.models if model.is_rollup]
    
    def get_model_count(self) -> Dict[str, int]:
        """Get count of different model types."""
        total = len(self.models)
        rollup = len([m for m in self.models if m.is_rollup])
        return {
            "total": total,
            "rollup": rollup,
            "regular": total - rollup,
            "visible": len(self.get_visible_models())
        }


class ModelDetailsPanel(Widget):
    """Panel for displaying detailed information about a selected model."""
    
    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """Initialize the details panel."""
        super().__init__(name=name, id=id, classes=classes)
        self.current_model: Optional[DbtModel] = None
        self.sql_result: Optional[SqlParseResult] = None
    
    def compose(self) -> ComposeResult:
        """Create the details panel layout."""
        yield Static("Select a model to view details", id="model-details", classes="model-details")
    
    def update_model(self, model: DbtModel, sql_result: Optional[SqlParseResult] = None) -> None:
        """Update the panel with model information."""
        self.current_model = model
        self.sql_result = sql_result
        
        # Build details content
        content = self._build_model_details()
        
        # Update the display
        details_widget = self.query_one("#model-details")
        details_widget.update(content)
    
    def _build_model_details(self) -> str:
        """Build detailed model information string."""
        if not self.current_model:
            return "Select a model to view details"
        
        model = self.current_model
        lines = []
        
        # Basic info
        lines.append(f"[bold]Model: {model.name}[/bold]")
        lines.append(f"Type: {'Rollup Model' if model.is_rollup else 'Regular Model'}")
        
        if model.file_path:
            lines.append(f"File: {model.file_path}")
        
        if model.description:
            lines.append(f"Description: {model.description}")
        
        lines.append("")
        
        # Columns
        if model.columns:
            lines.append(f"[bold]Columns ({len(model.columns)}):[/bold]")
            for i, column in enumerate(model.columns[:20]):  # Limit display
                lines.append(f"  • {column}")
            if len(model.columns) > 20:
                lines.append(f"  ... and {len(model.columns) - 20} more columns")
        
        # SQL Analysis (if available)
        if self.sql_result:
            lines.append("")
            lines.append("[bold]SQL Analysis:[/bold]")
            
            if self.sql_result.source_tables:
                lines.append(f"Source Tables: {', '.join(self.sql_result.source_tables)}")
            
            if self.sql_result.cte_names:
                lines.append(f"CTEs: {', '.join(self.sql_result.cte_names)}")
            
            if self.sql_result.columns:
                metric_columns = [col for col in self.sql_result.columns if col.is_aggregated]
                if metric_columns:
                    lines.append(f"Aggregated Columns: {len(metric_columns)}")
                    for col in metric_columns[:5]:
                        lines.append(f"  • {col.name} ({col.function_type})")
            
            if self.sql_result.errors:
                lines.append("")
                lines.append("[bold red]Parsing Errors:[/bold red]")
                for error in self.sql_result.errors:
                    lines.append(f"  • {error}")
        
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear the details panel."""
        self.current_model = None
        self.sql_result = None
        details_widget = self.query_one("#model-details")
        details_widget.update("Select a model to view details")