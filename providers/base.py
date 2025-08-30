"""Base AI provider implementation."""

import re
from abc import ABC, abstractmethod
from typing import List

from models.types import (
    AIProvider, ProviderConfig, ReviewResult, Issue, Suggestion, 
    Severity, Priority, TokenUsage
)


class BaseAIProvider(ABC, AIProvider):
    """Base class for AI providers."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def review(self, code: str, prompt: str) -> ReviewResult:
        """Perform code review."""
        pass
    
    def configure(self, config: ProviderConfig) -> None:
        """Update provider configuration."""
        self.config = config
    
    def validate_config(self) -> bool:
        """Validate provider configuration."""
        if not self.config.api_key:
            raise ValueError(f"API key is required for {self.name}")
        return True
    
    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for given number of tokens."""
        pass
    
    def parse_review_response(
        self, response: str, provider: str, model: str
    ) -> ReviewResult:
        """Parse AI response into structured ReviewResult."""
        result = ReviewResult(
            provider=provider,
            model=model,
            raw_response=response
        )
        
        try:
            # Split response into sections
            sections = self._split_into_sections(response)
            
            # Parse each section
            for section_title, content in sections.items():
                title_lower = section_title.lower()
                
                if 'summary' in title_lower:
                    result.summary = content.strip()
                elif 'strength' in title_lower:
                    result.strengths = self._extract_list_items(content)
                elif 'issue' in title_lower or 'problem' in title_lower:
                    result.issues = self._parse_issues(content)
                elif 'suggestion' in title_lower or 'improvement' in title_lower:
                    result.suggestions = self._parse_suggestions(content)
        
        except Exception as e:
            # If parsing fails, create a basic result
            result.summary = f"Parsing error: {e}"
            result.issues = []
            result.suggestions = []
        
        return result
    
    def _split_into_sections(self, response: str) -> dict[str, str]:
        """Split response into sections based on headers."""
        sections = {}
        current_section = "general"
        current_content = []
        
        lines = response.split('\n')
        
        for line in lines:
            # Check if line is a header (starts with # or ##)
            header_match = re.match(r'^#{1,3}\s+(.+)$', line.strip())
            if header_match:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = header_match.group(1)
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_list_items(self, content: str) -> List[str]:
        """Extract list items from content."""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Match various list formats
            if re.match(r'^[-*•]\s+', line) or re.match(r'^\d+\.\s+', line):
                # Remove list marker
                item = re.sub(r'^[-*•]\s+', '', line)
                item = re.sub(r'^\d+\.\s+', '', item)
                if item:
                    items.append(item)
        
        return items
    
    def _parse_issues(self, content: str) -> List[Issue]:
        """Parse issues from content."""
        issues = []
        current_issue = None
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for severity indicators
            if '🔴' in line or 'critical' in line.lower():
                if current_issue:
                    issues.append(current_issue)
                current_issue = Issue(
                    severity=Severity.CRITICAL,
                    type="general",
                    description=self._clean_issue_text(line)
                )
            elif '🟡' in line or 'major' in line.lower():
                if current_issue:
                    issues.append(current_issue)
                current_issue = Issue(
                    severity=Severity.MAJOR,
                    type="general",
                    description=self._clean_issue_text(line)
                )
            elif '🟢' in line or 'minor' in line.lower():
                if current_issue:
                    issues.append(current_issue)
                current_issue = Issue(
                    severity=Severity.MINOR,
                    type="general",
                    description=self._clean_issue_text(line)
                )
            elif current_issue and line:
                # Add to current issue description
                current_issue.description += f" {line}"
        
        if current_issue:
            issues.append(current_issue)
        
        return issues
    
    def _parse_suggestions(self, content: str) -> List[Suggestion]:
        """Parse suggestions from content."""
        suggestions = []
        items = self._extract_list_items(content)
        
        for i, item in enumerate(items):
            # Determine priority based on keywords
            priority = Priority.MEDIUM
            if any(word in item.lower() for word in ['urgent', 'critical', 'important']):
                priority = Priority.HIGH
            elif any(word in item.lower() for word in ['minor', 'optional', 'consider']):
                priority = Priority.LOW
            
            suggestion = Suggestion(
                id=f"suggestion-{i + 1}",
                title=item.split('.')[0] if '.' in item else item[:50],
                description=item,
                priority=priority
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _clean_issue_text(self, text: str) -> str:
        """Clean issue text by removing severity indicators."""
        # Remove emoji and severity keywords
        text = re.sub(r'[🔴🟡🟢]', '', text)
        text = re.sub(r'\*?\*?(Critical|Major|Minor)\*?\*?:?\s*', '', text, flags=re.IGNORECASE)
        return text.strip()