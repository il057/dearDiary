import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DiaryCreate(BaseModel):
    content: str = Field(..., description="随手记或日记内容")
    created_at: Optional[datetime.datetime] = Field(None, description="自定义补档创建时间")
    quoted_diary_ids: Optional[List[int]] = Field(None, description="引用的历史日记 ID 列表")

class DiaryUpdate(BaseModel):
    content: str = Field(..., description="更新后的日记内容")
    created_at: Optional[datetime.datetime] = Field(None, description="更新后的时间")
    quoted_diary_ids: Optional[List[int]] = Field(None, description="更新后的引用日记 ID 列表（不传则保持不变）")

class DiaryEntitiesUpdate(BaseModel):
    entities: List[str] = Field(..., description="日记关联的实体标签列表")

class DiaryMoodUpdate(BaseModel):
    mood: str = Field(..., description="情绪心境词")

class AliasCreateRequest(BaseModel):
    alias: str = Field(..., description="别名或昵称")
    canonical: str = Field(..., description="主实体名")

class EntityTypeUpdateRequest(BaseModel):
    name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="目标分类: person/pet/place/time/concept")

class EntityOut(BaseModel):
    id: int
    name: str
    entity_type: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class RelationOut(BaseModel):
    id: int
    source_name: str
    relation: str
    target_name: str
    weight: float

    class Config:
        from_attributes = True

class RelationCreateRequest(BaseModel):
    source_name: str = Field(..., description="主体实体名")
    relation: str = Field(..., description="关系词")
    target_name: str = Field(..., description="客体实体名")

class OwnerNameUpdateRequest(BaseModel):
    owner_name: str = Field(..., description="日记主人的称呼（默认为“我”）")

class EntityGraphNode(BaseModel):
    id: str
    name: str
    entity_type: str = "concept"
    count: int = 0
    is_owner: bool = False

class EntityGraphLink(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0

class EntityGraphResponse(BaseModel):
    nodes: List[EntityGraphNode] = []
    links: List[EntityGraphLink] = []

class DiaryQuoteRef(BaseModel):
    id: int
    content: str
    summary: Optional[str] = None
    mood: Optional[str] = None
    mood_color: Optional[str] = "#dc143c"
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DiaryEchoCreate(BaseModel):
    content: str = Field(..., description="回响/批注内容")


class DiaryEchoUpdate(BaseModel):
    content: str = Field(..., description="更新后的回响/批注内容")


class DiaryEchoOut(BaseModel):
    id: int
    diary_id: int
    content: str
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class DiaryOut(BaseModel):
    id: int
    content: str
    summary: Optional[str] = None
    mood: Optional[str] = None
    mood_color: Optional[str] = "#dc143c"
    created_at: datetime.datetime
    entities: List[str] = []
    quoted_diaries: List[DiaryQuoteRef] = []
    quoted_by: List[DiaryQuoteRef] = []
    echoes: List[DiaryEchoOut] = []

    class Config:
        from_attributes = True

class SearchResultItem(BaseModel):
    diary_id: int
    content: str
    created_at: datetime.datetime
    summary: Optional[str] = None
    mood: Optional[str] = None
    mood_color: Optional[str] = "#dc143c"
    score: float = 0.0
    matched_reason: str = "语义向量相似"
    related_entities: List[str] = []
    echoes: List[DiaryEchoOut] = []

class SearchResponse(BaseModel):
    query: str
    expanded_entities: List[str] = []
    results: List[SearchResultItem] = []

class GraphNode(BaseModel):
    id: int
    name: str
    color: str
    val: float = 3.0
    content: str
    created_at: str
    entities: List[str] = []
    mood: Optional[str] = None

class GraphLink(BaseModel):
    source: int
    target: int
    value: float = 1.0
    reason: Optional[str] = None

class GraphResponse(BaseModel):
    nodes: List[GraphNode] = []
    links: List[GraphLink] = []

class DiaryEchoImportItem(BaseModel):
    content: str
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

class DiaryImportItem(BaseModel):
    content: str
    created_at: Optional[datetime.datetime] = None
    mood: Optional[str] = None
    entities: Optional[List[str]] = []
    echoes: Optional[List[DiaryEchoImportItem]] = []

class DiaryImportRequest(BaseModel):
    diaries: List[DiaryImportItem]
    knowledge: Optional[Dict[str, Any]] = None
    relations: Optional[List[RelationCreateRequest]] = None
