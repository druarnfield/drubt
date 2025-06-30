"""Settings screen implementation."""

from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, DirectoryTree, Label
from textual.binding import Binding

from ..state import AppState


class SettingsScreen(Screen):
    """Settings and project configuration screen."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.selected_path = ""
    
    def compose(self) -> ComposeResult:
        """Create settings layout."""
        yield Header()
        
        yield Container(
            Static("Project Configuration", classes="section-title"),
            self._create_project_section(),
            self._create_recent_projects_section(),
            classes="settings-container"
        )
        
        yield Footer()
    
    def _create_project_section(self) -> Container:
        """Create project configuration section."""
        return Container(
            Vertical(
                Label("Project Path:"),
                Input(
                    placeholder="Enter path to your dbt project...",
                    value=self.app_state.project_path,
                    id="project-path-input"
                ),
                Horizontal(
                    Button("Browse", id="browse-btn"),
                    Button("Load Project", id="load-btn", variant="primary"),
                    Button("Validate", id="validate-btn"),
                    classes="button-row"
                ),
                self._create_directory_browser(),
                classes="project-config"
            ),
            classes="project-section"
        )
    
    def _create_directory_browser(self) -> Container:
        """Create directory browser."""
        try:
            initial_path = Path(self.app_state.project_path) if self.app_state.project_path else Path.home()
            if not initial_path.exists():
                initial_path = Path.home()
        except Exception:
            initial_path = Path.home()
        
        return Container(
            Label("Browse for dbt project:"),
            DirectoryTree(str(initial_path), id="directory-tree"),
            classes="directory-browser"
        )
    
    def _create_recent_projects_section(self) -> Container:
        """Create recent projects section."""
        recent_projects = self.app_state.get_recent_projects()
        
        if not recent_projects:
            content = Static("No recent projects", classes="no-recent")
        else:
            project_buttons = []
            for project in recent_projects[:5]:  # Show last 5 projects
                project_buttons.append(
                    Button(
                        f"{project['name']} ({project['path']})",
                        id=f"recent-{project['path']}",
                        classes="recent-project-btn"
                    )
                )
            
            content = Vertical(*project_buttons, classes="recent-projects-list")
        
        return Container(
            Static("Recent Projects", classes="section-title"),
            content,
            classes="recent-section"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "browse-btn":
            self.action_browse()
        elif event.button.id == "load-btn":
            self.action_load()
        elif event.button.id == "validate-btn":
            self.action_validate()
        elif event.button.id and event.button.id.startswith("recent-"):
            project_path = event.button.id[7:]  # Remove "recent-" prefix
            self.load_project(project_path)
    
    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection."""
        self.selected_path = str(event.path)
        project_input = self.query_one("#project-path-input", Input)
        project_input.value = self.selected_path
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "project-path-input":
            self.selected_path = event.value
    
    def action_browse(self) -> None:
        """Focus on directory browser."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.focus()
    
    def action_validate(self) -> None:
        """Validate the selected project path."""
        path = self.selected_path or self.query_one("#project-path-input", Input).value
        
        if not path:
            self.notify("Please enter a project path", severity="warning")
            return
        
        try:
            from ..services import DbtReader
            reader = DbtReader(path)
            valid, message = reader.validate_project()
            
            if valid:
                self.notify("✓ Valid dbt project", severity="information")
            else:
                self.notify(f"✗ {message}", severity="error")
        except Exception as e:
            self.notify(f"Error validating project: {e}", severity="error")
    
    def action_load(self) -> None:
        """Load the selected project."""
        path = self.selected_path or self.query_one("#project-path-input", Input).value
        self.load_project(path)
    
    def load_project(self, path: str) -> None:
        """Load a project by path."""
        if not path:
            self.notify("Please enter a project path", severity="warning")
            return
        
        self.notify("Loading project...", timeout=1)
        
        # Use call_after_refresh to ensure UI updates
        self.call_after_refresh(self._do_load_project, path)
    
    def _do_load_project(self, path: str) -> None:
        """Actually load the project."""
        success = self.app_state.load_project(path)
        
        if success:
            self.notify(f"✓ Loaded project: {self.app_state.project_name}")
            # Update the input field
            project_input = self.query_one("#project-path-input", Input)
            project_input.value = path
            # Go back to dashboard
            self.app.pop_screen()
        else:
            self.notify(f"✗ Failed to load project: {self.app_state.error_message}", severity="error")
    
    def action_save(self) -> None:
        """Save current settings."""
        # Update config with current path
        if self.selected_path:
            self.app_state.config.set("project.default_path", self.selected_path)
            self.app_state.config.save_settings()
            self.notify("Settings saved")
    
    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()