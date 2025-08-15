from fastapi import FastAPI, File, UploadFile, HTTPException, Header, Depends
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Union
import aiofiles
import shutil
from pathlib import Path

# Load environment variables from .env
load_dotenv()

app = FastAPI(title="JSON Store API", description="API for storing JSON files in database")

# Security token from environment variable
SECURITY_TOKEN = os.getenv("SECURITY_TOKEN", "optional-token")

def verify_token(authorization: str = Header(None)):
    """Verify the security token (required)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format. Use 'Bearer <token>'")
    
    token = authorization.replace("Bearer ", "")
    if token != SECURITY_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token

# Database connection
@app.on_event("startup")
def startup():
    global conn, cur
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432)
    )
    cur = conn.cursor()

# Pydantic models
class JsonFileResponse(BaseModel):
    id: str
    fileName: str
    jsonPayload: str
    size: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class JsonFileListResponse(BaseModel):
    success: bool
    data: List[JsonFileResponse]
    
    class Config:
        orm_mode = True

class UploadResponse(BaseModel):
    success: bool
    data: Optional[JsonFileResponse] = None
    error: Optional[str] = None
    
    class Config:
        orm_mode = True

@app.get("/")
def read_root():
    cur.execute("SELECT NOW();")
    return {"time": cur.fetchone()[0], "message": "JSON Store API is running"}

@app.post("/upload", response_model=UploadResponse)
async def upload_json_file(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """
    Upload a JSON file and store it in the database
    """
    # Validate file type
    if not file.content_type or file.content_type not in ['application/json', 'text/plain']:
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Generate unique ID
        file_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate JSON content
        try:
            json_content = file_content.decode('utf-8')
            json.loads(json_content)  # Validate JSON format
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="File must contain valid JSON")
        
        # Store JSON data in database
        cur.execute(
            """
            INSERT INTO json_files (id, fileName, jsonPayload, size, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, fileName, jsonPayload, size, created_at, updated_at
            """,
            [
                file_id,
                file.filename or f"json_file_{file_id}.json",
                json_content,
                file_size,
                datetime.utcnow(),
                datetime.utcnow()
            ]
        )
        
        result = cur.fetchone()
        conn.commit()
        
        return UploadResponse(
            success=True,
            data=JsonFileResponse(
                id=result[0],
                fileName=result[1],
                jsonPayload=result[2],
                size=result[3],
                created_at=result[4],
                updated_at=result[5]
            )
        )
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/json-files", response_model=JsonFileListResponse)
async def get_json_files(token: str = Depends(verify_token)):
    """
    Get all stored JSON files metadata
    """
    try:
        cur.execute(
            """
            SELECT id, fileName, jsonPayload, size, created_at, updated_at 
            FROM json_files 
            ORDER BY created_at DESC
            """
        )
        
        results = cur.fetchall()
        json_files = []
        
        for row in results:
            json_files.append(JsonFileResponse(
                id=row[0],
                fileName=row[1],
                jsonPayload=row[2],
                size=row[3],
                created_at=row[4],
                updated_at=row[5]
            ))
        
        return JsonFileListResponse(success=True, data=json_files)
        
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch JSON files")

@app.get("/json-files/{file_id}")
async def get_json_file(file_id: str, token: str = Depends(verify_token)):
    """
    Get the actual JSON file content by ID
    """
    try:
        cur.execute(
            "SELECT fileName, jsonPayload FROM json_files WHERE id = %s", 
            [file_id]
        )
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="JSON file not found")
        
        fileName, jsonPayload = result
        
        return Response(
            content=jsonPayload,
            media_type="application/json",
            headers={"Content-Disposition": f"inline; filename={fileName}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get JSON file error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve JSON file")

@app.delete("/json-files/{file_id}")
async def delete_json_file(file_id: str, token: str = Depends(verify_token)):
    """
    Delete a JSON file by ID
    """
    try:
        # Check if file exists
        cur.execute("SELECT id FROM json_files WHERE id = %s", [file_id])
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="JSON file not found")
        
        # Delete from database
        cur.execute("DELETE FROM json_files WHERE id = %s", [file_id])
        conn.commit()
        
        return {"success": True, "message": "JSON file deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete JSON file")

@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    try:
        cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


