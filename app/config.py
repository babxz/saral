"""
SARAL-TN Configuration
Centralized settings for Tamil Nadu traffic enforcement system
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_DIR = BASE_DIR / "temp"
MODEL_DIR = BASE_DIR / "models"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "SARAL-TN"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key"
    
    # Database
    DATABASE_URL: str = "sqlite:///./saral_tn.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "saral-tn-uploads"
    AWS_REGION: str = "ap-south-1"
    
    # MoRTH Vahan API
    VAHAN_API_URL: str = "https://vahan.nic.in/api"
    VAHAN_API_KEY: str = ""
    
    # AI Models
    YOLO_MODEL_PATH: str = str(MODEL_DIR / "yolov8n.pt")
    OCR_GPU: bool = False
    
    # Violation types supported
    VIOLATION_TYPES = {
        0: {"name": "red_light_jump", "fine": 1000, "section": "119/177 MVA"},
        1: {"name": "wrong_side_driving", "fine": 1500, "section": "177 MVA"},
        2: {"name": "no_helmet", "fine": 500, "section": "129/177 MVA"},
        3: {"name": "triple_riding", "fine": 1000, "section": "128/177 MVA"},
        4: {"name": "illegal_parking", "fine": 500, "section": "122/177 MVA"},
    }
    
    # TN License plate regex
    TN_PLATE_PATTERN = r"^TN-\d{2}-[A-Z]{1,2}-\d{4}$"
    
    # Reporter reward percentage
    REWARD_PERCENTAGE: float = 10.0
    
    # Confidence thresholds
    YOLO_CONFIDENCE: float = 0.7
    OCR_CONFIDENCE: float = 0.7
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
