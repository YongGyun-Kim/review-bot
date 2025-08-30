"""Prompt template management using Jinja2."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from jinja2 import Template, Environment, FileSystemLoader, TemplateError
import yaml

from models.types import PromptTemplate, GitDiff


class PromptManager:
    """Manages prompt templates for code reviews."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt templates
        """
        self.prompts_dir = prompts_dir or Path("prompts")
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        
        # Register custom filters
        self.env.filters['format_number'] = lambda x: f"{x:,}"
        self.env.filters['format_date'] = lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
    
    async def load_prompt(self, template_name: str) -> str:
        """Load a prompt template by name.
        
        Args:
            template_name: Name of the template (without extension)
            
        Returns:
            Template content as string
        """
        template_path = self.prompts_dir / f"{template_name}.md"
        
        if not template_path.exists():
            if template_name != "default":
                print(f"Template '{template_name}' not found, falling back to default")
                return await self.load_prompt("default")
            else:
                raise FileNotFoundError(f"Default template not found: {template_path}")
        
        return template_path.read_text(encoding='utf-8')
    
    async def get_available_prompts(self) -> List[PromptTemplate]:
        """Get list of available prompt templates.
        
        Returns:
            List of PromptTemplate objects
        """
        templates = []
        
        for template_file in self.prompts_dir.glob("*.md"):
            if template_file.is_file():
                name = template_file.stem
                content = template_file.read_text(encoding='utf-8')
                
                # Extract metadata from template
                metadata = self._extract_metadata(content)
                description = metadata.get('description', self._extract_description(content))
                variables = self._extract_variables(content)
                
                templates.append(PromptTemplate(
                    name=name,
                    description=description,
                    template=content,
                    variables=variables
                ))
        
        return sorted(templates, key=lambda t: t.name)
    
    async def create_prompt(self, name: str, content: str) -> None:
        """Create a new prompt template.
        
        Args:
            name: Template name
            content: Template content
        """
        template_path = self.prompts_dir / f"{name}.md"
        
        if template_path.exists():
            raise FileExistsError(f"Template '{name}' already exists")
        
        # Validate template syntax
        validation = self.validate_prompt(content)
        if not validation['valid']:
            raise ValueError(f"Invalid template: {', '.join(validation['errors'])}")
        
        template_path.write_text(content, encoding='utf-8')
        print(f"Template '{name}' created successfully")
    
    async def update_prompt(self, name: str, content: str) -> None:
        """Update an existing prompt template.
        
        Args:
            name: Template name
            content: New template content
        """
        template_path = self.prompts_dir / f"{name}.md"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{name}' not found")
        
        # Validate template syntax
        validation = self.validate_prompt(content)
        if not validation['valid']:
            raise ValueError(f"Invalid template: {', '.join(validation['errors'])}")
        
        # Backup existing template
        backup_path = self.prompts_dir / f"{name}.md.bak"
        backup_path.write_text(template_path.read_text(encoding='utf-8'), encoding='utf-8')
        
        template_path.write_text(content, encoding='utf-8')
        print(f"Template '{name}' updated successfully (backup saved as {name}.md.bak)")
    
    async def delete_prompt(self, name: str) -> None:
        """Delete a prompt template.
        
        Args:
            name: Template name
        """
        if name == "default":
            raise ValueError("Cannot delete default template")
        
        template_path = self.prompts_dir / f"{name}.md"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{name}' not found")
        
        template_path.unlink()
        print(f"Template '{name}' deleted successfully")
    
    def populate_prompt(self, template: str, data: Dict[str, Any]) -> str:
        """Populate template with data using Jinja2.
        
        Args:
            template: Template string
            data: Data dictionary for template variables
            
        Returns:
            Populated template string
        """
        try:
            jinja_template = Template(template)
            
            # Prepare context with default values
            context = self._prepare_context(data)
            
            # Render template
            return jinja_template.render(**context)
            
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")
    
    def _prepare_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare template context with default values.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Context dictionary with defaults
        """
        context = {
            # Metadata
            'timestamp': datetime.now(),
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': datetime.now().strftime("%H:%M:%S"),
            
            # Git information
            'branch': 'unknown',
            'commit_message': '',
            'files_changed': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'files_list': [],
            
            # Code diff
            'code_diff': '',
            
            # User information
            'user': '',
            'email': '',
        }
        
        # Extract Git information if available
        if 'git_diff' in data and isinstance(data['git_diff'], GitDiff):
            git_diff = data['git_diff']
            context.update({
                'branch': git_diff.branch or 'unknown',
                'commit_message': git_diff.commit_message or '',
                'files_changed': git_diff.stats.files_changed,
                'lines_added': git_diff.stats.insertions,
                'lines_deleted': git_diff.stats.deletions,
                'files_list': [f.path for f in git_diff.files],
            })
        
        # Update with provided data
        context.update(data)
        
        return context
    
    def validate_prompt(self, template: str) -> Dict[str, Any]:
        """Validate prompt template syntax and requirements.
        
        Args:
            template: Template string to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Check for empty template
        if not template.strip():
            errors.append("Template cannot be empty")
        
        # Check for required variables
        required_vars = ['code_diff']
        template_vars = self._extract_variables(template)
        
        for var in required_vars:
            if var not in template_vars:
                errors.append(f"Required variable '{{{{ {var} }}}}' is missing")
        
        # Check Jinja2 syntax
        try:
            Template(template)
        except TemplateError as e:
            errors.append(f"Template syntax error: {e}")
        
        # Check for common issues
        if len(template) > 10000:
            warnings.append("Template is very long (>10000 characters)")
        
        if '{{{{' in template or '}}}}' in template:
            warnings.append("Template contains escaped brackets - make sure this is intentional")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'variables': template_vars
        }
    
    def _extract_variables(self, template: str) -> List[str]:
        """Extract variable names from template.
        
        Args:
            template: Template string
            
        Returns:
            List of unique variable names
        """
        # Match Jinja2 variables: {{ variable }}
        pattern = r'\{\{\s*(\w+)(?:\.\w+)*\s*(?:\|[^}]*)?\}\}'
        matches = re.findall(pattern, template)
        
        # Also match simple placeholders for backward compatibility
        simple_pattern = r'\{\{(\w+)\}\}'
        simple_matches = re.findall(simple_pattern, template)
        
        return list(set(matches + simple_matches))
    
    def _extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract YAML metadata from template if present.
        
        Args:
            content: Template content
            
        Returns:
            Metadata dictionary
        """
        # Check for YAML front matter
        if content.startswith('---'):
            try:
                end_index = content.index('---', 3)
                yaml_content = content[3:end_index]
                return yaml.safe_load(yaml_content) or {}
            except (ValueError, yaml.YAMLError):
                pass
        
        return {}
    
    def _extract_description(self, content: str) -> str:
        """Extract description from template content.
        
        Args:
            content: Template content
            
        Returns:
            Description string
        """
        # Skip YAML front matter if present
        if content.startswith('---'):
            try:
                end_index = content.index('---', 3)
                content = content[end_index + 3:].strip()
            except ValueError:
                pass
        
        # Extract first heading or first line
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
            elif line and not line.startswith('{{'):
                return line[:100]  # First 100 characters
        
        return "Custom prompt template"
    
    async def export_prompt(self, name: str, output_path: Path) -> None:
        """Export a prompt template to a file.
        
        Args:
            name: Template name
            output_path: Output file path
        """
        template = await self.load_prompt(name)
        output_path.write_text(template, encoding='utf-8')
        print(f"Template '{name}' exported to {output_path}")
    
    async def import_prompt(self, input_path: Path, name: Optional[str] = None) -> None:
        """Import a prompt template from a file.
        
        Args:
            input_path: Input file path
            name: Template name (uses file stem if not provided)
        """
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
        
        content = input_path.read_text(encoding='utf-8')
        template_name = name or input_path.stem
        
        await self.create_prompt(template_name, content)
        print(f"Template imported as '{template_name}'")