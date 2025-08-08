from fastapi import FastAPI, File, UploadFile, HTTPException
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

app = FastAPI(title="Image Store API", description="API for storing images in database")

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
class ImageResponse(BaseModel):
    id: str
    name: str
    size: int
    type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ImageListResponse(BaseModel):
    success: bool
    data: List[ImageResponse]
    
    class Config:
        orm_mode = True

class UploadResponse(BaseModel):
    success: bool
    data: Optional[ImageResponse] = None
    error: Optional[str] = None
    
    class Config:
        orm_mode = True

@app.get("/")
def read_root():
    cur.execute("SELECT NOW();")
    return {"time": cur.fetchone()[0], "message": "Image Store API is running"}

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file and store it directly in the database
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Generate unique ID
        file_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Store image data directly in database
        cur.execute(
            """
            INSERT INTO images (id, name, image_data, size, type, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, size, type, created_at, updated_at
            """,
            [
                file_id,
                file.filename or f"image_{file_id}",
                file_content,  # Store binary data directly
                file_size,
                file.content_type,
                datetime.utcnow(),
                datetime.utcnow()
            ]
        )
        
        result = cur.fetchone()
        conn.commit()
        
        return UploadResponse(
            success=True,
            data=ImageResponse(
                id=result[0],
                name=result[1],
                size=result[2],
                type=result[3],
                created_at=result[4],
                updated_at=result[5]
            )
        )
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/images", response_model=ImageListResponse)
async def get_images():
    """
    Get all stored images metadata (without the actual image data)
    """
    try:
        cur.execute(
            """
            SELECT id, name, size, type, created_at, updated_at 
            FROM images 
            ORDER BY created_at DESC
            """
        )
        
        results = cur.fetchall()
        images = []
        
        for row in results:
            images.append(ImageResponse(
                id=row[0],
                name=row[1],
                size=row[2],
                type=row[3],
                created_at=row[4],
                updated_at=row[5]
            ))
        
        return ImageListResponse(success=True, data=images)
        
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch images")

@app.get("/images/{image_id}")
async def get_image(image_id: str):
    """
    Get the actual image data by ID
    """
    try:
        cur.execute(
            "SELECT name, image_data, type FROM images WHERE id = %s", 
            [image_id]
        )
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Image not found")
        
        name, image_data, content_type = result
        
        return Response(
            content=bytes(image_data),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={name}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get image error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")

@app.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """
    Delete an image by ID
    """
    try:
        # Check if image exists
        cur.execute("SELECT id FROM images WHERE id = %s", [image_id])
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Delete from database
        cur.execute("DELETE FROM images WHERE id = %s", [image_id])
        conn.commit()
        
        return {"success": True, "message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")

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
