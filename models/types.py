"""Type definitions and Pydantic models for the review bot."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Protocol, Union

from pydantic import BaseModel, Field, ConfigDict


class Provider(str, Enum):
    """Available AI providers."""
    CLAUDE = "claude"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"


class Priority(str, Enum):
    """Priority levels for issues and todos."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class FileStatus(str, Enum):
    """Git file status."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ReviewConfig(BaseModel):
    """Configuration for code reviews."""
    model_config = ConfigDict(extra='forbid')
    
    provider: Provider = Provider.CLAUDE
    model: Optional[str] = None
    api_key: str = Field(..., min_length=1)
    prompt_template: str = "default"
    auto_review: Dict[str, bool] = Field(default_factory=lambda: {
        "on_commit": False,
        "on_push": False
    })
    output_dir: Path = Path("./reviews")
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "node_modules/**", "*.log", "dist/**", "build/**", "__pycache__/**"
    ])
    include_patterns: List[str] = Field(default_factory=lambda: [
        "**/*.py", "**/*.ts", "**/*.js", "**/*.tsx", "**/*.jsx", 
        "**/*.go", "**/*.rs", "**/*.java", "**/*.cpp", "**/*.c"
    ])
    max_files_per_review: int = Field(default=50, gt=0)
    max_tokens: int = Field(default=4000, gt=0)
    temperature: float = Field(default=0.1, ge=0, le=2)


class ProviderConfig(BaseModel):
    """Configuration for AI providers."""
    model_config = ConfigDict(extra='forbid')
    
    api_key: str
    model: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1


class TokenUsage(BaseModel):
    """Token usage information."""
    model_config = ConfigDict(extra='forbid')
    
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class Issue(BaseModel):
    """A code review issue."""
    model_config = ConfigDict(extra='forbid')
    
    severity: Severity
    type: str
    file: Optional[str] = None
    line: Optional[int] = None
    description: str
    suggestion: Optional[str] = None
    code_example: Optional[str] = None


class Suggestion(BaseModel):
    """A code improvement suggestion."""
    model_config = ConfigDict(extra='forbid')
    
    id: str
    title: str
    description: str
    files: List[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    completed: bool = False
    example: Optional[str] = None


class TodoItem(Suggestion):
    """A TODO item extending Suggestion."""
    model_config = ConfigDict(extra='forbid')
    
    created_at: datetime = Field(default_factory=datetime.now)
    review_id: str
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None


class ReviewResult(BaseModel):
    """Result of a code review."""
    model_config = ConfigDict(extra='forbid')
    
    provider: str
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: str = ""
    strengths: List[str] = Field(default_factory=list)
    issues: List[Issue] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    raw_response: Optional[str] = None
    tokens: Optional[TokenUsage] = None
    estimated_cost: Optional[float] = None


class FileChange(BaseModel):
    """Information about a changed file."""
    model_config = ConfigDict(extra='forbid')
    
    path: str
    status: FileStatus
    additions: int = 0
    deletions: int = 0
    patch: Optional[str] = None


class GitStats(BaseModel):
    """Git statistics."""
    model_config = ConfigDict(extra='forbid')
    
    files_changed: int
    insertions: int
    deletions: int


class GitDiff(BaseModel):
    """Git diff information."""
    model_config = ConfigDict(extra='forbid')
    
    files: List[FileChange] = Field(default_factory=list)
    stats: GitStats = Field(default_factory=GitStats)
    commit_message: Optional[str] = None
    branch: Optional[str] = None


class PromptTemplate(BaseModel):
    """A prompt template."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    description: str
    template: str
    variables: List[str] = Field(default_factory=list)


class AIProvider(Protocol):
    """Protocol for AI providers."""
    
    name: str
    
    async def review(self, code: str, prompt: str) -> ReviewResult:
        """Perform a code review."""
        ...
    
    def configure(self, config: ProviderConfig) -> None:
        """Configure the provider."""
        ...
    
    def validate_config(self) -> bool:
        """Validate the provider configuration."""
        ...
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate the cost for the given number of tokens."""
        ...