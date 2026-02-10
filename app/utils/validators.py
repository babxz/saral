"""
Validation utilities for SARAL-TN
GPS, timestamp, and metadata validation
"""

import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass

import exifread
from geopy.distance import geodesic


@dataclass
class ValidationResult:
    """Validation result container"""
    is_valid: bool
    message: str
    metadata: Optional[dict] = None


class MetadataValidator:
    """Validate video metadata for tamper detection"""
    
    # TN boundaries (approximate)
    TN_BOUNDS = {
        "lat_min": 8.0,
        "lat_max": 13.5,
        "lon_min": 77.0,
        "lon_max": 80.5,
    }
    
    # Max video age (hours)
    MAX_VIDEO_AGE = 24
    
    def __init__(self):
        self.tn_plate_pattern = re.compile(r"^TN-\d{2}-[A-Z]{1,2}-\d{4}$")
    
    def validate_gps(self, lat: float, lon: float) -> ValidationResult:
        """Validate GPS coordinates are within Tamil Nadu"""
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return ValidationResult(False, "Invalid GPS coordinates")
        
        if not (self.TN_BOUNDS["lat_min"] <= lat <= self.TN_BOUNDS["lat_max"] and
                self.TN_BOUNDS["lon_min"] <= lon <= self.TN_BOUNDS["lon_max"]):
            return ValidationResult(False, "Location outside Tamil Nadu")
        
        return ValidationResult(True, "GPS valid", {"lat": lat, "lon": lon})
    
    def validate_timestamp(self, timestamp: datetime) -> ValidationResult:
        """Validate video timestamp is recent and not future-dated"""
        now = datetime.now()
        
        # Check not future-dated
        if timestamp > now + timedelta(minutes=5):
            return ValidationResult(False, "Timestamp is in future")
        
        # Check not too old
        if timestamp < now - timedelta(hours=self.MAX_VIDEO_AGE):
            return ValidationResult(False, f"Video older than {self.MAX_VIDEO_AGE} hours")
        
        return ValidationResult(True, "Timestamp valid", {"timestamp": timestamp})
    
    def validate_tn_plate(self, plate: str) -> ValidationResult:
        """Validate Tamil Nadu license plate format"""
        plate_clean = plate.replace(" ", "").upper()
        
        if not self.tn_plate_pattern.match(plate_clean):
            return ValidationResult(False, f"Invalid TN plate format: {plate}")
        
        return ValidationResult(True, "Plate format valid", {"plate": plate_clean})
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash for evidence integrity"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def extract_exif(self, video_path: str) -> Optional[dict]:
        """Extract EXIF metadata from video file"""
        try:
            with open(video_path, 'rb') as f:
                tags = exifread.process_file(f)
            
            metadata = {}
            
            # Extract GPS if available
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                lat = self._convert_gps(tags['GPS GPSLatitude'])
                lon = self._convert_gps(tags['GPS GPSLongitude'])
                metadata['gps'] = (lat, lon)
            
            # Extract timestamp
            if 'EXIF DateTimeOriginal' in tags:
                dt_str = str(tags['EXIF DateTimeOriginal'])
                metadata['timestamp'] = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            
            # Extract device info
            if 'Image Make' in tags:
                metadata['device_make'] = str(tags['Image Make'])
            if 'Image Model' in tags:
                metadata['device_model'] = str(tags['Image Model'])
            
            return metadata
            
        except Exception as e:
            return None
    
    def _convert_gps(self, gps_tag) -> float:
        """Convert EXIF GPS coordinates to decimal degrees"""
        def convert_to_degrees(value):
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)
        
        return convert_to_degrees(gps_tag)


# Global validator instance
validator = MetadataValidator()
