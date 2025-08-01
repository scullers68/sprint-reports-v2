#!/usr/bin/env python3
"""
Start a test server without database dependencies for API testing.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create test app without database
app = FastAPI(
    title="Sprint Reports API - Test Mode",
    description="Test version without database dependencies",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Sprint Reports API v2 - Test Mode",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
        "note": "This is a test server without database connections"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "mode": "test"
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Test API endpoint."""
    return {
        "message": "Test endpoint working",
        "data": ["item1", "item2", "item3"]
    }

if __name__ == "__main__":
    print("🚀 Starting Sprint Reports Test Server...")
    print("📖 API Documentation: http://127.0.0.1:8000/docs")
    print("🔄 Alternative Docs: http://127.0.0.1:8000/redoc")
    print("💡 Root Endpoint: http://127.0.0.1:8000/")
    print("✨ Test Endpoint: http://127.0.0.1:8000/api/v1/test")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )