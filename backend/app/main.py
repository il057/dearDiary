import os
import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.config import settings
from app.database import engine, Base, get_db, ensure_sqlite_migrations
from app.models import Diary, Entity, EntityRelation, DiaryEntity
from app.schemas import (
    DiaryCreate, DiaryUpdate, DiaryEntitiesUpdate, DiaryMoodUpdate, AliasCreateRequest, EntityTypeUpdateRequest, DiaryOut, SearchResponse, GraphResponse, EntityOut, RelationOut, DiaryImportRequest
)
from app.services.memory_engine import memory_engine
from app.services.knowledge_base import knowledge_base

Base.metadata.create_all(bind=engine)
ensure_sqlite_migrations()

app = FastAPI(
    title="dearDiary - 个人语义记忆与关联日记系统 API",
    version="1.6.0",
    description="基于本地向量检索、实体关系图谱与 2D 力导向星系聚类图的极简关联日记系统"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"app": "dearDiary", "status": "online"}

# ----------------- 记录层 API -----------------

@app.post("/api/diaries", response_model=DiaryOut)
def create_diary(payload: DiaryCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="日记内容不能为空")
    diary = memory_engine.create_diary_immediate(db, payload.content, created_at=payload.created_at)
    color = memory_engine.ensure_mood_color(db, diary)
    background_tasks.add_task(memory_engine.process_single_diary_memory, diary.id)

    return DiaryOut(
        id=diary.id,
        content=diary.content,
        summary=diary.summary,
        mood=diary.mood,
        mood_color=color,
        created_at=diary.created_at,
        entities=[]
    )

@app.put("/api/diaries/{diary_id}", response_model=DiaryOut)
def update_diary(diary_id: int, payload: DiaryUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="日记内容不能为空")
    diary = memory_engine.update_diary_immediate(db, diary_id, payload.content, created_at=payload.created_at)
    if not diary:
        raise HTTPException(status_code=404, detail="未找到该篇日记")

    diary.mood_color = None
    color = memory_engine.ensure_mood_color(db, diary)
    background_tasks.add_task(memory_engine.process_single_diary_memory, diary.id)

    return DiaryOut(
        id=diary.id,
        content=diary.content,
        summary=diary.summary,
        mood=diary.mood,
        mood_color=color,
        created_at=diary.created_at,
        entities=[b.entity.name for b in diary.entities if b.entity]
    )

@app.put("/api/diaries/{diary_id}/mood")
def update_diary_mood(diary_id: int, payload: DiaryMoodUpdate, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    diary.mood = payload.mood.strip()
    db.commit()
    return {"status": "success", "mood": diary.mood}

@app.get("/api/diaries/{diary_id}", response_model=DiaryOut)
def get_single_diary(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    color = memory_engine.ensure_mood_color(db, diary)
    return DiaryOut(
        id=diary.id,
        content=diary.content,
        summary=diary.summary,
        mood=diary.mood,
        mood_color=color,
        created_at=diary.created_at,
        entities=[b.entity.name for b in diary.entities if b.entity]
    )

@app.post("/api/diaries/{diary_id}/reindex", response_model=DiaryOut)
def reindex_single_diary(diary_id: int):
    res = memory_engine.process_single_diary_memory(diary_id)
    if not res:
        raise HTTPException(status_code=404, detail="日记不存在")
    return res

@app.get("/api/diaries", response_model=List[DiaryOut])
def list_diaries(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    items = db.query(Diary).order_by(Diary.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    color_backfilled = False
    for d in items:
        had_color = bool(d.mood_color)
        color = memory_engine.ensure_mood_color(db, d, commit=False)
        if not had_color:
            color_backfilled = True
        results.append(DiaryOut(
            id=d.id,
            content=d.content,
            summary=d.summary,
            mood=d.mood,
            mood_color=color,
            created_at=d.created_at,
            entities=[b.entity.name for b in d.entities if b.entity]
        ))
    if color_backfilled:
        db.commit()
    return results

@app.delete("/api/diaries/{diary_id}")
def delete_diary(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    from app.services.vector_store import vector_store
    vector_store.delete_by_diary_id(diary_id)
    db.delete(diary)
    db.commit()
    memory_engine.cleanup_orphan_entities(db)
    return {"status": "success", "deleted_id": diary_id}

# ----------------- 2D 平面力导向聚类星系图 API -----------------

@app.get("/api/graph/cluster2d", response_model=GraphResponse)
def get_cluster_graph_2d(db: Session = Depends(get_db)):
    """
    提供给前端 2D Force-Directed 社区聚类星系图
    """
    return memory_engine.get_cluster_graph_2d(db)

# ----------------- 记忆与关联检索 API -----------------

@app.get("/api/search", response_model=SearchResponse)
def hybrid_search(
    q: str = Query(..., description="搜索词或自然语言问题"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if not q.strip():
        return SearchResponse(query="", expanded_entities=[], results=[])
    return memory_engine.hybrid_associative_search(db, q.strip(), limit=limit)

# ----------------- 认知知识库与别名对齐 API -----------------

@app.get("/api/knowledge")
def get_knowledge(db: Session = Depends(get_db)):
    """获取用户认知词典与别名映射，执行自动垃圾回收确保无引用标签自动清理"""
    memory_engine.cleanup_orphan_entities(db)
    kb_data = knowledge_base.get_all()
    aliases = kb_data.get("aliases", {})
    custom_entities = kb_data.get("custom_entities", {})

    # 统计数据库中每个实体实际被几篇日记引用
    counts = dict(
        db.query(Entity.name, func.count(DiaryEntity.id))
        .join(DiaryEntity, DiaryEntity.entity_id == Entity.id, isouter=True)
        .group_by(Entity.name)
        .all()
    )

    merged_entities = {}
    # 首先收录数据库中实际关联的所有实体
    for ent in db.query(Entity).all():
        merged_entities[ent.name] = {
            "entity_type": custom_entities.get(ent.name, ent.entity_type or "concept"),
            "count": counts.get(ent.name, 0)
        }

    # 补充知识库中已配置的实体
    for name, etype in custom_entities.items():
        if name not in merged_entities:
            merged_entities[name] = {
                "entity_type": etype,
                "count": 0
            }

    return {
        "aliases": aliases,
        "entities": merged_entities
    }

@app.post("/api/knowledge/alias")
def set_alias(payload: AliasCreateRequest):
    """设置别名映射（例如 将别名绑定到核心主实体）"""
    knowledge_base.set_alias(payload.alias, payload.canonical)
    return {"status": "success", "alias": payload.alias, "canonical": payload.canonical}

@app.delete("/api/knowledge/alias/{alias}")
def delete_alias(alias: str):
    """删除别名映射"""
    knowledge_base.remove_alias(alias)
    return {"status": "success", "deleted_alias": alias}

@app.delete("/api/knowledge/entity/{name}")
def delete_entity(name: str, db: Session = Depends(get_db)):
    """
    深度级联删除实体：
    1. 从本地 knowledge_base 词典中移除；
    2. 显式删除 diary_entities 桥接记录（彻底从所有日记中抹除该标签）；
    3. 清理 entity_relations 图谱边；
    4. 从 entities 实体主表删除。
    """
    knowledge_base.remove_entity(name)

    ent = db.query(Entity).filter(Entity.name == name).first()
    if ent:
        db.query(DiaryEntity).filter(DiaryEntity.entity_id == ent.id).delete()
        db.query(EntityRelation).filter(
            or_(EntityRelation.source_name == name, EntityRelation.target_name == name)
        ).delete()
        db.delete(ent)
        db.commit()

    return {"status": "success", "deleted_entity": name}

@app.put("/api/knowledge/entity")
def update_entity_type(payload: EntityTypeUpdateRequest, db: Session = Depends(get_db)):
    """
    修改实体的类型分类（例如把宠物误判为人名改为 pet；或改为 place / concept / time / person）
    """
    knowledge_base.update_entity_type(payload.name, payload.entity_type)
    ent = db.query(Entity).filter(Entity.name == payload.name).first()
    if ent:
        ent.entity_type = payload.entity_type
        db.commit()
    return {"status": "success", "name": payload.name, "entity_type": payload.entity_type}

# ----------------- 日记标签手工修改 API -----------------

@app.put("/api/diaries/{diary_id}/entities", response_model=DiaryOut)
def update_diary_entities(diary_id: int, payload: DiaryEntitiesUpdate, db: Session = Depends(get_db)):
    """
    前端直接修改某篇日记的标签（增删改）：
    1. 自动对齐别名归一；
    2. 自动沉淀新标签到知识库；
    3. 实时更新日记与实体的多对多关联。
    """
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    # 清除旧关联
    db.query(DiaryEntity).filter(DiaryEntity.diary_id == diary.id).delete()

    canonical_entities = []
    for raw_tag in payload.entities:
        tag = raw_tag.strip()
        if not tag:
            continue
        canonical = knowledge_base.resolve_entity(tag)
        canonical_entities.append(canonical)

        ent = db.query(Entity).filter(Entity.name == canonical).first()
        if not ent:
            ent = Entity(name=canonical, entity_type="concept")
            db.add(ent)
            db.commit()
            db.refresh(ent)

        bridge = DiaryEntity(diary_id=diary.id, entity_id=ent.id)
        db.add(bridge)

    db.commit()
    db.refresh(diary)
    memory_engine.cleanup_orphan_entities(db)

    # 自动沉淀到 knowledge.json
    knowledge_base.auto_register_entities([{"name": c, "entity_type": "concept"} for c in canonical_entities])

    color = memory_engine.ensure_mood_color(db, diary)

    return DiaryOut(
        id=diary.id,
        content=diary.content,
        summary=diary.summary,
        mood=diary.mood,
        mood_color=color,
        created_at=diary.created_at,
        entities=[b.entity.name for b in diary.entities if b.entity]
    )

@app.put("/api/diaries/{diary_id}/mood")
def update_diary_mood(diary_id: int, payload: DiaryMoodUpdate, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    diary.mood = payload.mood.strip()
    db.commit()
    return {"status": "success", "mood": diary.mood}

@app.get("/api/export")
def export_diaries(db: Session = Depends(get_db)):
    items = db.query(Diary).order_by(Diary.created_at.desc()).all()
    exported = []
    for d in items:
        exported.append({
            "content": d.content,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "mood": d.mood,
            "summary": d.summary,
            "entities": [b.entity.name for b in d.entities if b.entity]
        })
    return {
        "app": "dearDiary",
        "exported_at": datetime.datetime.now().isoformat(),
        "total": len(exported),
        "diaries": exported
    }

@app.post("/api/import")
def import_diaries(payload: DiaryImportRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    imported_count = 0
    skipped_count = 0

    for item in payload.diaries:
        content = (item.content or "").strip()
        if not content:
            skipped_count += 1
            continue

        dt = item.created_at
        if dt and dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)

        # 去重检查：同内容同时间则跳过
        existing_query = db.query(Diary).filter(Diary.content == content)
        if dt:
            existing_query = existing_query.filter(Diary.created_at == dt)
        if existing_query.first():
            skipped_count += 1
            continue

        diary = memory_engine.create_diary_immediate(db, content, created_at=dt)
        if item.mood:
            diary.mood = item.mood.strip()
            db.commit()

        # 若导出数据已包含标签，提前关联
        if item.entities:
            for raw_tag in item.entities:
                tag = raw_tag.strip()
                if not tag:
                    continue
                canonical = knowledge_base.resolve_entity(tag)
                ent = db.query(Entity).filter(Entity.name == canonical).first()
                if not ent:
                    ent = Entity(name=canonical, entity_type="concept")
                    db.add(ent)
                    db.commit()
                    db.refresh(ent)
                db.add(DiaryEntity(diary_id=diary.id, entity_id=ent.id))
            db.commit()

        background_tasks.add_task(memory_engine.process_single_diary_memory, diary.id)
        imported_count += 1

    return {"status": "success", "imported": imported_count, "skipped": skipped_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
