import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base

class Content(Base):
    __tablename__ = "contents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(32), nullable=False, index=True)  # VIDEO, IMAGE, PDF, TEXT
    status = Column(String(32), default="READY", index=True)       # UPLOADING, READY, FAILED
    text_content = Column(Text, nullable=True)                    # For direct text / markdown notes
    thumbnail_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 1 -> N Relationship with Assets
    assets = relationship("Asset", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    variants = relationship("ContentVariant", back_populates="content", cascade="all, delete-orphan", lazy="selectin")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, default=0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("Content", back_populates="assets")

class ContentVariant(Base):
    __tablename__ = "content_variants"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(64), nullable=False)  # youtube, instagram, tiktok, linkedin, x, facebook
    format = Column(String(32), nullable=False)    # 16:9, 9:16, 1:1, 4:5, Text, PDF
    storage_path = Column(String(512), default="")
    copy_text = Column(Text, default="")
    status = Column(String(32), default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("Content", back_populates="variants")

class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    handle = Column(String(128), default="")
    connected = Column(Boolean, default=False)
    avatar_url = Column(String(512), default="")
    capabilities_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def capabilities(self):
        try:
            return json.loads(self.capabilities_json)
        except Exception:
            return []

    @capabilities.setter
    def capabilities(self, value):
        self.capabilities_json = json.dumps(value)

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    active = Column(Boolean, default=True)
    description = Column(String(512), default="")
    trigger = Column(String(64), default="Manual Upload")
    nodes_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    type = Column(String(64), nullable=False)
    status = Column(String(32), default="QUEUED", index=True)
    payload_json = Column(Text, default="{}")
    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(String(64), primary_key=True, index=True)
    level = Column(String(16), default="INFO")
    service = Column(String(64), default="System")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
