"""
Database operations for SARAL-TN
PostgreSQL for persistence, Redis for caching
"""

import json
import redis
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings


Base = declarative_base()


class ViolationRecord(Base):
    """Database model for violation records"""
    __tablename__ = "violations"
    
    id = Column(String(36), primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Reporter info
    reporter_id = Column(String(50))
    reporter_phone = Column(String(15))
    
    # Violation details
    violation_type = Column(String(50))
    violation_confidence = Column(Float)
    plate_number = Column(String(20))
    plate_confidence = Column(Float)
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    location_name = Column(String(200))
    
    # Evidence
    video_url = Column(String(500))
    video_hash = Column(String(64))
    challan_pdf_url = Column(String(500))
    
    # Enforcement
    fine_amount = Column(Integer)
    mv_act_section = Column(String(50))
    payment_status = Column(String(20), default="pending")  # pending, paid, disputed
    
    # Reward
    reporter_reward = Column(Integer)
    reward_status = Column(String(20), default="pending")  # pending, credited
    
    # Metadata
    raw_detection_data = Column(JSON)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "violation_type": self.violation_type,
            "plate_number": self.plate_number,
            "fine_amount": self.fine_amount,
            "payment_status": self.payment_status,
            "reward_status": self.reward_status,
        }


class DatabaseManager:
    """Handle all database operations"""
    
    def __init__(self):
        # PostgreSQL
        self.engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Redis
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    def create_violation(self, violation_data: Dict) -> str:
        """Store new violation record"""
        session = self.Session()
        try:
            record = ViolationRecord(**violation_data)
            session.add(record)
            session.commit()
            
            # Cache in Redis
            self.redis_client.setex(
                f"violation:{record.id}",
                3600,  # 1 hour TTL
                json.dumps(record.to_dict())
            )
            
            return record.id
            
        finally:
            session.close()
    
    def get_violation(self, violation_id: str) -> Optional[Dict]:
        """Get violation by ID (with caching)"""
        # Try cache first
        cached = self.redis_client.get(f"violation:{violation_id}")
        if cached:
            return json.loads(cached)
        
        # Fallback to DB
        session = self.Session()
        try:
            record = session.query(ViolationRecord).filter_by(id=violation_id).first()
            if record:
                data = record.to_dict()
                # Update cache
                self.redis_client.setex(f"violation:{violation_id}", 3600, json.dumps(data))
                return data
            return None
        finally:
            session.close()
    
    def update_payment_status(self, violation_id: str, status: str):
        """Update payment status"""
        session = self.Session()
        try:
            record = session.query(ViolationRecord).filter_by(id=violation_id).first()
            if record:
                record.payment_status = status
                session.commit()
                
                # Invalidate cache
                self.redis_client.delete(f"violation:{violation_id}")
        finally:
            session.close()
    
    def get_reporter_stats(self, reporter_id: str) -> Dict:
        """Get statistics for a reporter"""
        session = self.Session()
        try:
            violations = session.query(ViolationRecord).filter_by(reporter_id=reporter_id).all()
            
            total_reports = len(violations)
            total_reward = sum(v.reward for v in violations if v.reward_status == "credited")
            pending_reward = sum(v.reward for v in violations if v.reward_status == "pending")
            
            return {
                "total_reports": total_reports,
                "total_reward": total_reward,
                "pending_reward": pending_reward,
                "recent_violations": [v.to_dict() for v in violations[-5:]]
            }
        finally:
            session.close()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top reporters by reward earned"""
        session = self.Session()
        try:
            # This would use a proper GROUP BY in production
            results = session.query(
                ViolationRecord.reporter_id,
                ViolationRecord.reporter_phone,
                db.func.sum(ViolationRecord.reporter_reward).label("total_reward")
            ).filter(
                ViolationRecord.reward_status == "credited"
            ).group_by(
                ViolationRecord.reporter_id
            ).order_by(
                db.desc("total_reward")
            ).limit(limit).all()
            
            return [
                {
                    "reporter_id": r[0],
                    "phone": r[1],
                    "total_reward": r[2]
                }
                for r in results
            ]
        finally:
            session.close()


# Global instance
db_manager = DatabaseManager()
