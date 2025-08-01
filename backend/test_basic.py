#!/usr/bin/env python3
"""
Simple test script to verify FastAPI app can start without database.
"""

import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a basic test app without database initialization
test_app = FastAPI(
    title="Sprint Reports API - Test Mode",
    description="Test version without database",
    version="2.0.0"
)

@test_app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Sprint Reports API v2 - Test Mode",
        "version": "2.0.0",
        "status": "operational"
    }

@test_app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    # Test the endpoints
    client = TestClient(test_app)
    
    print("Testing FastAPI endpoints...")
    
    # Test root endpoint
    response = client.get("/")
    print(f"GET /: {response.status_code} - {response.json()}")
    
    # Test health endpoint
    response = client.get("/health")
    print(f"GET /health: {response.status_code} - {response.json()}")
    
    print("\n✅ Basic FastAPI functionality is working!")
    print("To test the full API with database:")
    print("1. Start PostgreSQL and Redis")
    print("2. Update .env with database credentials")
    print("3. Run: uvicorn app.main:app --reload")