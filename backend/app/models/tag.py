"""Tag models for categorizing and organizing sessions."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Tag(Base):
    """Tag model for categorizing sessions."""
    
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)  # e.g., "meeting", "urgent"
    category = Column(String, nullable=False)  # "type", "topic", "person", "priority", "context"
    color = Column(String, nullable=False)  # Hex color for UI display
    auto_generated = Column(Boolean, default=True)  # True if created by AI
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session_tags = relationship("SessionTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', category='{self.category}')>"


class SessionTag(Base):
    """Association table for many-to-many relationship between sessions and tags."""
    
    __tablename__ = "session_tags"
    __table_args__ = (
        Index('ix_session_tags_session_id', 'session_id'),
        Index('ix_session_tags_tag_id', 'tag_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, default=1.0)  # 0.0-1.0 confidence score for AI-generated tags
    auto_generated = Column(Boolean, default=True)  # True if added by AI, False if manual
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="session_tags")
    tag = relationship("Tag", back_populates="session_tags")
    
    def __repr__(self) -> str:
        return f"<SessionTag(session_id={self.session_id}, tag_id={self.tag_id}, confidence={self.confidence})>"
