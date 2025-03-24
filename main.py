import uvicorn
from fastapi import FastAPI
from app.api.routers import files
from app.api import auth
from app.core.config import settings
from app.services.cleanup_service import setup_cleanup_tasks

# Create FastAPI application
app = FastAPI(title=settings.PROJECT_NAME)

# Include routers
app.include_router(files.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")

# Set up background cleanup tasks
setup_cleanup_tasks(app)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
