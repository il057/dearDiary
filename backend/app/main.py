import os
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.config import settings
from app.database import engine, Base, get_db, ensure_sqlite_migrations, SessionLocal
from app.models import Diary, Entity, EntityRelation, DiaryEntity, DiaryQuote
from app.schemas import (
    DiaryCreate, DiaryUpdate, DiaryEntitiesUpdate, DiaryMoodUpdate, AliasCreateRequest, EntityTypeUpdateRequest, RelationCreateRequest, OwnerNameUpdateRequest, DiaryOut, SearchResultItem, SearchResponse, GraphResponse, EntityGraphResponse, EntityOut, RelationOut, DiaryImportRequest
)
from app.services.memory_engine import memory_engine
from app.services.knowledge_base import knowledge_base

# 单线程后台任务队列：避免批量导入时并发写 SQLite 锁库或同时压垮本地 Ollama
_memory_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="memory_worker")

def _enqueue_memory_task(diary_id: int):
    _memory_executor.submit(memory_engine.process_single_diary_memory, diary_id)

Base.metadata.create_all(bind=engine)
ensure_sqlite_migrations()

app = FastAPI(
    title="dearDiary - 个人语义记忆与关联日记系统 API",
    version="1.6.0",
    description="基于本地向量检索、实体关系图谱与 2D 力导向星系聚类图的极简关联日记系统"
)

def _startup_warmup():
    """后台预热：压缩 LanceDB 碎片事务并预计算 2D 星图缓存"""
    from app.services.vector_store import vector_store
    vector_store.compact()
    db = SessionLocal()
    try:
        memory_engine.get_cluster_graph_2d(db)
    except Exception as e:
        print(f"[Warmup Warning] graph prewarm failed: {e}")
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    threading.Thread(target=_startup_warmup, daemon=True, name="startup_warmup").start()

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
def create_diary(payload: DiaryCreate, db: Session = Depends(get_db)):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="日记内容不能为空")
    diary = memory_engine.create_diary_immediate(db, payload.content, created_at=payload.created_at)
    memory_engine.sync_diary_quotes(db, diary.id, payload.quoted_diary_ids)
    memory_engine.ensure_mood_color(db, diary)
    memory_engine.invalidate_graph_cache()
    _enqueue_memory_task(diary.id)

    return memory_engine.build_diary_out(db, diary)

@app.put("/api/diaries/{diary_id}", response_model=DiaryOut)
def update_diary(diary_id: int, payload: DiaryUpdate, db: Session = Depends(get_db)):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="日记内容不能为空")
    diary = memory_engine.update_diary_immediate(db, diary_id, payload.content, created_at=payload.created_at)
    if not diary:
        raise HTTPException(status_code=404, detail="未找到该篇日记")

    memory_engine.sync_diary_quotes(db, diary.id, payload.quoted_diary_ids)
    diary.mood_color = None
    memory_engine.ensure_mood_color(db, diary)
    memory_engine.invalidate_graph_cache()
    _enqueue_memory_task(diary.id)

    return memory_engine.build_diary_out(db, diary)

@app.put("/api/diaries/{diary_id}/mood")
def update_diary_mood(diary_id: int, payload: DiaryMoodUpdate, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    diary.mood = payload.mood.strip()
    db.commit()
    memory_engine.invalidate_graph_cache()
    return {"status": "success", "mood": diary.mood}

@app.get("/api/diaries/{diary_id}", response_model=DiaryOut)
def get_single_diary(diary_id: int, db: Session = Depends(get_db)):
    diary = (
        db.query(Diary)
        .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
        .filter(Diary.id == diary_id)
        .first()
    )
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    return memory_engine.build_diary_out(db, diary)

@app.get("/api/diaries/{diary_id}/related", response_model=List[SearchResultItem])
def get_related_diaries(diary_id: int, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """获取与指定日记最相关的历史记忆"""
    return memory_engine.get_related_diaries(db, diary_id, limit=limit)

@app.post("/api/diaries/recolor")
def recolor_all_diaries(db: Session = Depends(get_db)):
    updated = memory_engine.recolor_all_diaries(db)
    return {"status": "success", "updated": updated}

@app.post("/api/diaries/{diary_id}/reindex", response_model=DiaryOut)
def reindex_single_diary(diary_id: int):
    try:
        res = memory_engine.process_single_diary_memory(diary_id, raise_on_llm_error=True)
    except Exception as e:
        raise HTTPException(status_code=504, detail=f"远端模型推理超时或失败: {e}")
    if not res:
        raise HTTPException(status_code=404, detail="日记不存在")
    return res

@app.get("/api/diaries", response_model=List[DiaryOut])
def list_diaries(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    items = (
        db.query(Diary)
        .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
        .order_by(Diary.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return memory_engine.build_diary_out_list(db, items)

@app.delete("/api/diaries/{diary_id}")
def delete_diary(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    from app.services.vector_store import vector_store
    vector_store.delete_by_diary_id(diary_id)
    db.query(EntityRelation).filter(EntityRelation.diary_id == diary_id).delete(synchronize_session=False)
    db.query(DiaryQuote).filter(or_(DiaryQuote.diary_id == diary_id, DiaryQuote.quoted_diary_id == diary_id)).delete(synchronize_session=False)
    db.delete(diary)
    db.commit()
    memory_engine.cleanup_orphan_entities(db)
    memory_engine.invalidate_graph_cache()
    return {"status": "success", "deleted_id": diary_id}

# ----------------- 2D 平面力导向聚类星系图 API -----------------

@app.get("/api/graph/cluster2d", response_model=GraphResponse)
def get_cluster_graph_2d(db: Session = Depends(get_db)):
    """
    提供给前端 2D Force-Directed 社区聚类星系图
    """
    return memory_engine.get_cluster_graph_2d(db)

@app.get("/api/graph/entities", response_model=EntityGraphResponse)
def get_entity_graph(db: Session = Depends(get_db)):
    """
    提供给前端实体与关系知识图谱可视化
    """
    return memory_engine.get_entity_graph(db)

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

    relations = []
    seen_triples = set()
    for r in db.query(EntityRelation).order_by(EntityRelation.id.desc()).all():
        triple = (r.source_name, r.relation, r.target_name)
        if triple in seen_triples:
            continue
        seen_triples.add(triple)
        relations.append({
            "id": r.id,
            "source_name": r.source_name,
            "relation": r.relation,
            "target_name": r.target_name,
            "weight": r.weight
        })

    return {
        "owner_name": knowledge_base.get_owner_name(),
        "aliases": aliases,
        "entities": merged_entities,
        "relations": relations
    }

@app.put("/api/knowledge/owner")
def update_owner_name(payload: OwnerNameUpdateRequest, db: Session = Depends(get_db)):
    """设置日记主人称呼（默认“我”），并同步更新既有关系图谱中的称呼"""
    new_name = (payload.owner_name or "").strip() or "我"
    old_name = knowledge_base.set_owner_name(new_name)
    if old_name != new_name:
        db.query(EntityRelation).filter(EntityRelation.source_name == old_name).update(
            {"source_name": new_name}, synchronize_session=False
        )
        db.query(EntityRelation).filter(EntityRelation.target_name == old_name).update(
            {"target_name": new_name}, synchronize_session=False
        )
        db.commit()
        memory_engine.invalidate_graph_cache()
    return {"status": "success", "owner_name": new_name}

@app.post("/api/knowledge/relations", response_model=RelationOut)
def create_relation(payload: RelationCreateRequest, db: Session = Depends(get_db)):
    """手动新增实体关系"""
    s = knowledge_base.resolve_entity(payload.source_name.strip())
    rel_type = payload.relation.strip()
    t = knowledge_base.resolve_entity(payload.target_name.strip())
    if not s or not rel_type or not t or s == t:
        raise HTTPException(status_code=400, detail="主体、关系与客体不能为空且不能相同")

    existing = db.query(EntityRelation).filter(
        EntityRelation.source_name == s,
        EntityRelation.relation == rel_type,
        EntityRelation.target_name == t
    ).first()
    if existing:
        return existing

    new_rel = EntityRelation(source_name=s, relation=rel_type, target_name=t)
    db.add(new_rel)
    db.commit()
    db.refresh(new_rel)
    memory_engine.invalidate_graph_cache()
    return new_rel

@app.put("/api/knowledge/relations/{rel_id}", response_model=RelationOut)
def update_relation(rel_id: int, payload: RelationCreateRequest, db: Session = Depends(get_db)):
    """修改已有实体关系"""
    rel = db.query(EntityRelation).filter(EntityRelation.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    s = knowledge_base.resolve_entity(payload.source_name.strip())
    rel_type = payload.relation.strip()
    t = knowledge_base.resolve_entity(payload.target_name.strip())
    if not s or not rel_type or not t or s == t:
        raise HTTPException(status_code=400, detail="主体、关系与客体不能为空且不能相同")

    rel.source_name = s
    rel.relation = rel_type
    rel.target_name = t
    db.commit()
    db.refresh(rel)
    memory_engine.invalidate_graph_cache()
    return rel

@app.delete("/api/knowledge/relations/{rel_id}")
def delete_relation(rel_id: int, db: Session = Depends(get_db)):
    """删除实体关系"""
    rel = db.query(EntityRelation).filter(EntityRelation.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    db.delete(rel)
    db.commit()
    memory_engine.invalidate_graph_cache()
    return {"status": "success", "deleted_id": rel_id}

@app.post("/api/knowledge/alias")
def set_alias(payload: AliasCreateRequest):
    """设置别名映射（例如 将别名绑定到核心主实体）"""
    knowledge_base.set_alias(payload.alias, payload.canonical)
    memory_engine.invalidate_graph_cache()
    return {"status": "success", "alias": payload.alias, "canonical": payload.canonical}

@app.delete("/api/knowledge/alias/{alias}")
def delete_alias(alias: str):
    """删除别名映射"""
    knowledge_base.remove_alias(alias)
    memory_engine.invalidate_graph_cache()
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

    memory_engine.invalidate_graph_cache()
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
    memory_engine.invalidate_graph_cache()

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

@app.get("/api/export")
def export_diaries(db: Session = Depends(get_db)):
    items = (
        db.query(Diary)
        .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
        .order_by(Diary.created_at.desc())
        .all()
    )
    exported = []
    for d in items:
        exported.append({
            "content": d.content,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "mood": d.mood,
            "summary": d.summary,
            "entities": [b.entity.name for b in d.entities if b.entity]
        })

    kb_data = knowledge_base.get_all()
    exported_relations = []
    seen_triples = set()
    for r in db.query(EntityRelation).order_by(EntityRelation.id.asc()).all():
        triple = (r.source_name, r.relation, r.target_name)
        if triple in seen_triples:
            continue
        seen_triples.add(triple)
        exported_relations.append({
            "source_name": r.source_name,
            "relation": r.relation,
            "target_name": r.target_name,
            "weight": r.weight
        })

    return {
        "app": "dearDiary",
        "exported_at": datetime.datetime.now().isoformat(),
        "total": len(exported),
        "knowledge": {
            "owner_name": knowledge_base.get_owner_name(),
            "aliases": kb_data.get("aliases", {}),
            "custom_entities": kb_data.get("custom_entities", {})
        },
        "relations": exported_relations,
        "diaries": exported
    }

@app.post("/api/import")
def import_diaries(payload: DiaryImportRequest, db: Session = Depends(get_db)):
    imported_count = 0
    skipped_count = 0

    # 1. 恢复知识库配置（称呼、别名、实体分类）
    if payload.knowledge:
        owner = (payload.knowledge.get("owner_name") or "").strip()
        if owner:
            knowledge_base.set_owner_name(owner)
        aliases = payload.knowledge.get("aliases") or {}
        for alias, canonical in aliases.items():
            if alias and canonical:
                knowledge_base.set_alias(str(alias), str(canonical))
        custom_entities = payload.knowledge.get("custom_entities") or {}
        for ent_name, etype in custom_entities.items():
            if ent_name and etype:
                knowledge_base.update_entity_type(str(ent_name), str(etype))
                ent = db.query(Entity).filter(Entity.name == str(ent_name)).first()
                if ent:
                    ent.entity_type = str(etype)
        db.commit()

    # 2. 恢复实体关系（去重写入）
    if payload.relations:
        for rel_item in payload.relations:
            s = knowledge_base.resolve_entity(rel_item.source_name.strip())
            r_type = rel_item.relation.strip()
            t = knowledge_base.resolve_entity(rel_item.target_name.strip())
            if not s or not r_type or not t or s == t:
                continue
            existing_rel = db.query(EntityRelation).filter(
                EntityRelation.source_name == s,
                EntityRelation.relation == r_type,
                EntityRelation.target_name == t
            ).first()
            if not existing_rel:
                db.add(EntityRelation(diary_id=None, source_name=s, relation=r_type, target_name=t))
        db.commit()

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

        _enqueue_memory_task(diary.id)
        imported_count += 1

    memory_engine.invalidate_graph_cache()
    return {"status": "success", "imported": imported_count, "skipped": skipped_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
