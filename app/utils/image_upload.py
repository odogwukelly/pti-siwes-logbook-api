import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException
from PIL import Image


# Base directory for storing uploads (you can adjust this)
UPLOAD_DIR = "images"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_file(file: UploadFile, subfolder: str = "") -> str:
    """
    Save an uploaded image or PDF to a specified folder.
    
    Args:
        file (UploadFile): The uploaded file (Image or PDF).
        subfolder (str): Optional subfolder inside uploads/.

    Returns:
        str: The saved file path.
    """
    # 1. Expanded validation for both Images and PDFs
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only JPEG, PNG, and PDF allowed."
        )

    # 2. Generate unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"

    # 3. Determine save path
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, unique_name)

    # 4. Save file to disk
    try:
        # Reset file pointer to the beginning before saving
        file.file.seek(0)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # 5. Conditional Validation based on file type
    try:
        if file.content_type.startswith("image/"):
            # If it's an image, verify it using PIL
            with Image.open(file_path) as img:
                img.verify()
        
        elif file.content_type == "application/pdf":
            # For PDFs, check if the file size is greater than 0
            # (Optional: Use PyPDF2 if you want to verify internal PDF structure)
            if os.path.getsize(file_path) == 0:
                raise ValueError("Empty PDF file")

    except Exception:
        # If validation fails, clean up the file and throw error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="Uploaded file is corrupted or invalid.")

    # Return the relative path for database storage
    return file_path


def delete_image(file_path: str) -> bool:
    """
    Delete an image file if it exists.

    Args:
        file_path (str): Path to the image file.

    Returns:
        bool: True if deleted, False if not found.
    """
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
