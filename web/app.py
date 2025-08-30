"""FastAPI web dashboard for the review bot."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.types import (
    ReviewResult, TodoItem, Priority, Provider, ReviewConfig
)
from core.review_manager import ReviewManager
from core.config_manager import ConfigManager
from core.todo_manager import TodoManager
from core.git_manager import GitManager
from core.prompt_manager import PromptManager


# Pydantic models for API
class ReviewRequest(BaseModel):
    staged: bool = False
    commit_hash: Optional[str] = None
    prompt_template: Optional[str] = None
    output_format: str = "markdown"


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None


class ConfigUpdate(BaseModel):
    provider: Optional[Provider] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    prompt_template: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)


# Initialize FastAPI app
app = FastAPI(
    title="Review Bot Dashboard",
    description="AI-powered code review dashboard",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
manager = ConnectionManager()

# Initialize managers
review_manager = ReviewManager()
config_manager = ConfigManager()
todo_manager = TodoManager()
git_manager = GitManager()
prompt_manager = PromptManager()


# Static files (will create later)
web_dir = Path(__file__).parent
static_dir = web_dir / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review Bot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-blue-600 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">🤖 Review Bot Dashboard</h1>
            <div class="space-x-4">
                <a href="/" class="hover:text-blue-200">Dashboard</a>
                <a href="/reviews" class="hover:text-blue-200">Reviews</a>
                <a href="/todos" class="hover:text-blue-200">TODOs</a>
                <a href="/settings" class="hover:text-blue-200">Settings</a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container mx-auto py-8 px-4" x-data="dashboard()">
        <!-- Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center">
                    <div class="p-3 bg-blue-100 rounded-full">
                        <i class="fas fa-code text-blue-600"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-gray-500 text-sm">Git Status</h3>
                        <p class="text-xl font-semibold" x-text="status.git_status"></p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center">
                    <div class="p-3 bg-green-100 rounded-full">
                        <i class="fas fa-robot text-green-600"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-gray-500 text-sm">AI Provider</h3>
                        <p class="text-xl font-semibold" x-text="status.provider"></p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center">
                    <div class="p-3 bg-yellow-100 rounded-full">
                        <i class="fas fa-tasks text-yellow-600"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-gray-500 text-sm">Active TODOs</h3>
                        <p class="text-xl font-semibold" x-text="status.active_todos"></p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="flex items-center">
                    <div class="p-3 bg-purple-100 rounded-full">
                        <i class="fas fa-history text-purple-600"></i>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-gray-500 text-sm">Reviews</h3>
                        <p class="text-xl font-semibold" x-text="status.total_reviews"></p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 class="text-2xl font-bold mb-4">Quick Actions</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button 
                    @click="runReview()"
                    :disabled="reviewInProgress"
                    class="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg flex items-center justify-center"
                >
                    <i class="fas fa-play mr-2"></i>
                    <span x-text="reviewInProgress ? 'Running Review...' : 'Run Review'"></span>
                </button>
                
                <button 
                    @click="runStagedReview()"
                    class="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg flex items-center justify-center"
                >
                    <i class="fas fa-check mr-2"></i>
                    Review Staged
                </button>
                
                <button 
                    @click="viewTodos()"
                    class="bg-yellow-500 hover:bg-yellow-600 text-white px-6 py-3 rounded-lg flex items-center justify-center"
                >
                    <i class="fas fa-list mr-2"></i>
                    View TODOs
                </button>
            </div>
        </div>

        <!-- Recent Reviews -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-2xl font-bold mb-4">Recent Reviews</h2>
            <div x-show="reviews.length === 0" class="text-gray-500 text-center py-8">
                No reviews yet. Run your first review!
            </div>
            <div class="space-y-4">
                <template x-for="review in reviews.slice(0, 5)" :key="review.timestamp">
                    <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                        <div class="flex justify-between items-start">
                            <div>
                                <h3 class="font-semibold" x-text="'Review - ' + new Date(review.timestamp).toLocaleDateString()"></h3>
                                <p class="text-gray-600 text-sm" x-text="review.provider + ' (' + review.model + ')'"></p>
                                <p class="text-gray-700 mt-2" x-text="review.summary.substring(0, 100) + '...'"></p>
                            </div>
                            <div class="text-right">
                                <div class="flex space-x-2 mb-2">
                                    <span class="bg-red-100 text-red-800 px-2 py-1 rounded text-xs" x-text="review.issues.filter(i => i.severity === 'critical').length + ' Critical'"></span>
                                    <span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs" x-text="review.issues.filter(i => i.severity === 'major').length + ' Major'"></span>
                                </div>
                                <p class="text-sm text-gray-500" x-text="new Date(review.timestamp).toLocaleTimeString()"></p>
                            </div>
                        </div>
                    </div>
                </template>
            </div>
        </div>
    </main>

    <script>
        function dashboard() {
            return {
                status: {
                    git_status: 'Loading...',
                    provider: 'Loading...',
                    active_todos: 0,
                    total_reviews: 0
                },
                reviews: [],
                reviewInProgress: false,
                
                async init() {
                    await this.loadStatus();
                    await this.loadReviews();
                    this.connectWebSocket();
                },
                
                async loadStatus() {
                    try {
                        const response = await fetch('/api/status');
                        this.status = await response.json();
                    } catch (error) {
                        console.error('Failed to load status:', error);
                    }
                },
                
                async loadReviews() {
                    try {
                        const response = await fetch('/api/reviews');
                        this.reviews = await response.json();
                    } catch (error) {
                        console.error('Failed to load reviews:', error);
                    }
                },
                
                async runReview() {
                    this.reviewInProgress = true;
                    try {
                        const response = await fetch('/api/review', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({staged: false})
                        });
                        
                        if (response.ok) {
                            await this.loadReviews();
                            await this.loadStatus();
                        } else {
                            alert('Review failed');
                        }
                    } catch (error) {
                        console.error('Review failed:', error);
                        alert('Review failed: ' + error.message);
                    } finally {
                        this.reviewInProgress = false;
                    }
                },
                
                async runStagedReview() {
                    // Similar to runReview but with staged: true
                    this.reviewInProgress = true;
                    try {
                        const response = await fetch('/api/review', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({staged: true})
                        });
                        
                        if (response.ok) {
                            await this.loadReviews();
                            await this.loadStatus();
                        }
                    } catch (error) {
                        console.error('Review failed:', error);
                    } finally {
                        this.reviewInProgress = false;
                    }
                },
                
                viewTodos() {
                    window.location.href = '/todos';
                },
                
                connectWebSocket() {
                    const ws = new WebSocket('ws://localhost:8000/ws');
                    
                    ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        if (data.type === 'review_complete') {
                            this.loadReviews();
                            this.loadStatus();
                        }
                    };
                }
            }
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/api/status")
async def get_status():
    """Get system status."""
    try:
        config = await config_manager.load_config()
        todos = await todo_manager.get_active_todos()
        
        # Get git status
        git_status = "Clean"
        if git_manager.is_git_repository():
            if git_manager.has_changes():
                git_status = "Changes"
            else:
                git_status = "Clean"
        else:
            git_status = "No Git"
        
        # Count total reviews (approximate by counting review files)
        review_files = list(Path("reviews").glob("review_*.md")) if Path("reviews").exists() else []
        
        return {
            "git_status": git_status,
            "provider": config.provider.value,
            "model": config.model or "default",
            "active_todos": len(todos),
            "total_reviews": len(review_files),
            "branch": git_manager.get_current_branch() if git_manager.is_git_repository() else "N/A"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review")
async def run_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks
):
    """Run a code review."""
    try:
        # Run review in background
        result = await review_manager.run_review(
            staged=request.staged,
            commit_hash=request.commit_hash,
            prompt_template=request.prompt_template,
            output_format=request.output_format
        )
        
        # Broadcast completion
        await manager.broadcast(json.dumps({
            "type": "review_complete",
            "data": {
                "timestamp": result.timestamp.isoformat(),
                "provider": result.provider,
                "issues_count": len(result.issues),
                "suggestions_count": len(result.suggestions)
            }
        }))
        
        return {
            "success": True,
            "timestamp": result.timestamp.isoformat(),
            "issues_count": len(result.issues),
            "suggestions_count": len(result.suggestions),
            "estimated_cost": result.estimated_cost
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/reviews")
async def get_reviews():
    """Get list of reviews."""
    try:
        reviews = []
        review_dir = Path("reviews")
        
        if review_dir.exists():
            # Get all review files
            for review_file in review_dir.glob("review_*.json"):
                try:
                    data = json.loads(review_file.read_text(encoding='utf-8'))
                    reviews.append(data)
                except:
                    continue
            
            # Sort by timestamp (newest first)
            reviews.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return reviews
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/todos")
async def get_todos():
    """Get TODO items."""
    try:
        todos = await todo_manager.get_all_todos()
        
        return [
            {
                "id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "priority": todo.priority.value,
                "completed": todo.completed,
                "created_at": todo.created_at.isoformat(),
                "assignee": todo.assignee,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "files": todo.files
            }
            for todo in todos
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/todos/{todo_id}")
async def update_todo(todo_id: str, update: TodoUpdate):
    """Update a TODO item."""
    try:
        success = await todo_manager.update_todo(
            todo_id=todo_id,
            title=update.title,
            description=update.description,
            priority=update.priority,
            assignee=update.assignee,
            due_date=update.due_date
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="TODO not found")
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/todos/{todo_id}/complete")
async def complete_todo(todo_id: str):
    """Mark TODO as completed."""
    try:
        success = await todo_manager.mark_completed(todo_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="TODO not found")
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str):
    """Delete a TODO item."""
    try:
        success = await todo_manager.delete_todo(todo_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="TODO not found")
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        config = await config_manager.load_config()
        
        # Don't expose API key in response
        config_dict = config.model_dump()
        config_dict['api_key'] = '***' if config_dict['api_key'] else ''
        
        return config_dict
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/config")
async def update_config(update: ConfigUpdate):
    """Update configuration."""
    try:
        config_data = {}
        
        if update.provider is not None:
            config_data['provider'] = update.provider.value
        if update.model is not None:
            config_data['model'] = update.model
        if update.api_key is not None:
            config_data['api_key'] = update.api_key
        if update.prompt_template is not None:
            config_data['prompt_template'] = update.prompt_template
        if update.max_tokens is not None:
            config_data['max_tokens'] = update.max_tokens
        if update.temperature is not None:
            config_data['temperature'] = update.temperature
        
        await config_manager.save_config(config_data, global_config=False)
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now - can add more functionality later
            await manager.send_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)