import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    summary = Column(String(500), nullable=True) # 提炼简评/摘要
    mood = Column(String(50), nullable=True)     # 心情/情感色彩
    mood_color = Column(String(20), nullable=True) # 基于语义向量的主题色值

    # 关联该日记中出现的实体
    entities = relationship("DiaryEntity", back_populates="diary", cascade="all, delete-orphan")
    # 引用关系：本篇引用的日记 & 引用本篇的后续日记
    quote_links = relationship(
        "DiaryQuote",
        foreign_keys="[DiaryQuote.diary_id]",
        back_populates="diary",
        cascade="all, delete-orphan"
    )
    quoted_by_links = relationship(
        "DiaryQuote",
        foreign_keys="[DiaryQuote.quoted_diary_id]",
        back_populates="quoted_diary",
        cascade="all, delete-orphan"
    )
    echoes = relationship(
        "DiaryEcho",
        back_populates="diary",
        cascade="all, delete-orphan",
        order_by="DiaryEcho.created_at.asc(), DiaryEcho.id.asc()"
    )


class Entity(Base):
    """
    语义实体（人物、地点、事物、概念、别名等）
    """
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    entity_type = Column(String(50), index=True, default="concept") # person, place, alias, event, tag
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关联记录
    diary_associations = relationship("DiaryEntity", back_populates="entity")


class EntityRelation(Base):
    """
    实体间的关联图边（例如：A 是 B 的朋友、C 是 A 的别名、A 在 B 工作）
    支持关联检索与实体发散扩散；diary_id 为空表示用户手动添加，非空表示由该篇日记提取
    """
    __tablename__ = "entity_relations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    diary_id = Column(Integer, ForeignKey("diaries.id", ondelete="CASCADE"), nullable=True, index=True)
    source_name = Column(String(100), index=True, nullable=False)
    relation = Column(String(100), nullable=False) # 例如：friend_of, alias_of, colleague_of, located_at
    target_name = Column(String(100), index=True, nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DiaryEntity(Base):
    """
    日记与实体的多对多桥接表
    """
    __tablename__ = "diary_entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    diary_id = Column(Integer, ForeignKey("diaries.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)

    diary = relationship("Diary", back_populates="entities")
    entity = relationship("Entity", back_populates="diary_associations")


class DiaryQuote(Base):
    """
    日记引用关联表：diary_id 引用了 quoted_diary_id
    """
    __tablename__ = "diary_quotes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    diary_id = Column(Integer, ForeignKey("diaries.id", ondelete="CASCADE"), nullable=False, index=True)
    quoted_diary_id = Column(Integer, ForeignKey("diaries.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    diary = relationship("Diary", foreign_keys=[diary_id], back_populates="quote_links")
    quoted_diary = relationship("Diary", foreign_keys=[quoted_diary_id], back_populates="quoted_by_links")


class DiaryEcho(Base):
    """
    日记回响（事后批注/解码）：依附于原日记，不参与 AI 分析，可被关键词检索
    """
    __tablename__ = "diary_echoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    diary_id = Column(Integer, ForeignKey("diaries.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    diary = relationship("Diary", back_populates="echoes")

