"""
AI Processing for SARAL-TN
YOLOv8 violation detection + EasyOCR license plate recognition
"""

import os
import cv2
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import torch
import numpy as np
from ultralytics import YOLO
import easyocr

from app.config import settings


@dataclass
class DetectionResult:
    """Violation detection result"""
    violation_type: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x1, y1, x2, y2
    vehicle_crop: Optional[np.ndarray] = None


@dataclass
class OCRResult:
    """License plate OCR result"""
    plate_number: str
    confidence: float
    raw_text: str


class AIProcessor:
    """AI pipeline for traffic violation detection"""
    
    VIOLATION_CLASSES = {
        0: "red_light_jump",
        1: "wrong_side_driving", 
        2: "no_helmet",
        3: "triple_riding",
        4: "illegal_parking",
    }
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() and settings.OCR_GPU else "cpu"
        print(f"Initializing AI Processor on {self.device}")
        
        # Load YOLOv8
        self.yolo = YOLO(settings.YOLO_MODEL_PATH)
        self.yolo.to(self.device)
        
        # Load EasyOCR
        self.reader = easyocr.Reader(
            ['en'],
            gpu=(self.device == "cuda"),
            model_storage_directory=str(settings.MODEL_DIR)
        )
        
        print("AI models loaded successfully")
    
    def detect_violations(self, video_path: str) -> List[DetectionResult]:
        """
        Detect traffic violations in video
        Returns list of violations with vehicle crops
        """
        results = []
        
        # Extract frames (sample every 0.5 seconds)
        frames = self._extract_frames(video_path, interval=0.5)
        
        for frame_idx, frame in enumerate(frames):
            # YOLO inference
            yolo_results = self.yolo(
                frame,
                conf=settings.YOLO_CONFIDENCE,
                verbose=False
            )
            
            for result in yolo_results:
                boxes = result.boxes
                
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # Check if it's a violation class
                    if cls_id in self.VIOLATION_CLASSES:
                        # Get bounding box
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Crop vehicle
                        vehicle_crop = frame[y1:y2, x1:x2]
                        
                        detection = DetectionResult(
                            violation_type=self.VIOLATION_CLASSES[cls_id],
                            confidence=conf,
                            bounding_box=(x1, y1, x2, y2),
                            vehicle_crop=vehicle_crop
                        )
                        results.append(detection)
        
        # Deduplicate overlapping detections
        return self._deduplicate_detections(results)
    
    def recognize_plate(self, vehicle_image: np.ndarray) -> Optional[OCRResult]:
        """
        Extract license plate from vehicle crop
        """
        if vehicle_image is None or vehicle_image.size == 0:
            return None
        
        # Preprocess for OCR
        gray = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Contrast enhancement
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
        
        # EasyOCR
        ocr_results = self.reader.readtext(gray)
        
        best_plate = None
        best_conf = 0.0
        
        for (bbox, text, conf) in ocr_results:
            # Clean text
            clean_text = self._clean_plate_text(text)
            
            # Check if looks like TN plate
            if self._is_plate_like(clean_text) and conf > best_conf:
                best_plate = clean_text
                best_conf = conf
        
        if best_plate and best_conf >= settings.OCR_CONFIDENCE:
            return OCRResult(
                plate_number=best_plate,
                confidence=best_conf,
                raw_text=best_plate
            )
        
        return None
    
    def process_video(self, video_path: str) -> Dict:
        """
        Full pipeline: detect violations + recognize plates
        """
        print(f"Processing video: {video_path}")
        
        # Step 1: Detect violations
        detections = self.detect_violations(video_path)
        
        if not detections:
            return {
                "success": False,
                "message": "No violations detected",
                "violations": []
            }
        
        # Step 2: Recognize plates for each detection
        violations_data = []
        
        for detection in detections:
            plate_result = None
            if detection.vehicle_crop is not None:
                plate_result = self.recognize_plate(detection.vehicle_crop)
            
            violation_info = {
                "type": detection.violation_type,
                "confidence": round(detection.confidence, 3),
                "bounding_box": detection.bounding_box,
                "plate_number": plate_result.plate_number if plate_result else None,
                "plate_confidence": round(plate_result.confidence, 3) if plate_result else None,
            }
            violations_data.append(violation_info)
        
        return {
            "success": True,
            "violations_count": len(violations_data),
            "violations": violations_data
        }
    
    def _extract_frames(self, video_path: str, interval: float = 0.5) -> List[np.ndarray]:
        """Extract frames from video at specified interval"""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval)
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frames.append(frame)
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def _deduplicate_detections(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Remove overlapping detections (same violation, multiple frames)"""
        if not detections:
            return detections
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x.confidence, reverse=True)
        
        unique = []
        for det in detections:
            # Check if overlaps with already selected
            is_duplicate = False
            for existing in unique:
                if self._iou(det.bounding_box, existing.bounding_box) > 0.5:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(det)
        
        return unique
    
    def _iou(self, box1: Tuple, box2: Tuple) -> float:
        """Calculate Intersection over Union"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Intersection
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # Union
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def _clean_plate_text(self, text: str) -> str:
        """Clean OCR output to TN plate format"""
        # Remove spaces and special chars, keep alphanumeric
        cleaned = ''.join(c for c in text if c.isalnum()).upper()
        
        # Try to format as TN-XX-XX-XXXX
        if len(cleaned) >= 8:
            # Extract TN prefix if present
            if cleaned.startswith('TN'):
                return cleaned
            # Try to find number pattern
            elif cleaned[0].isdigit() and len(cleaned) >= 10:
                # Might be missing TN prefix
                return "TN" + cleaned
        
        return cleaned
    
    def _is_plate_like(self, text: str) -> bool:
        """Check if text resembles TN license plate"""
        # Basic pattern: starts with TN, has numbers
        return (
            len(text) >= 8 and
            text.startswith('TN') and
            any(c.isdigit() for c in text)
        )


# Global processor instance (lazy loaded)
_ai_processor = None

def get_ai_processor():
    """Get or create AI processor singleton"""
    global _ai_processor
    if _ai_processor is None:
        _ai_processor = AIProcessor()
    return _ai_processor
