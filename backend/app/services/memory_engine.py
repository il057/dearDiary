import time
import math
import re
import datetime
import threading
import numpy as np
from typing import List, Dict, Any, Set, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from app.models import Diary, Entity, EntityRelation, DiaryEntity, DiaryQuote
from app.services.llm_client import llm_service
from app.services.vector_store import vector_store
from app.schemas import (
    SearchResultItem, SearchResponse, DiaryOut, DiaryQuoteRef, GraphResponse, GraphNode, GraphLink,
    EntityGraphNode, EntityGraphLink, EntityGraphResponse
)
from app.database import SessionLocal
from app.services.knowledge_base import knowledge_base

def vector_to_hex_color(vector: List[float]) -> str:
    if not vector or len(vector) < 100:
        return "#dc143c"

    # 使用正交零均值投影消除句向量公共偏置，使不同语义的角分布均匀铺满 360° 色相环
    x = sum(v if i % 2 == 0 else -v for i, v in enumerate(vector))
    y = sum(v if (i // 2) % 2 == 0 else -v for i, v in enumerate(vector))
    z = sum(v if (i // 4) % 2 == 0 else -v for i, v in enumerate(vector))
    w = sum(v if (i // 8) % 2 == 0 else -v for i, v in enumerate(vector))

    angle = math.atan2(y, x)
    t = (angle + math.pi) / (2 * math.pi)

    # 围绕主点缀色 Crimson (#dc143c) 构建的暗调电影感色域（无刺眼绿/黄绿），兼顾整体统一与节点区分度
    if t < 0.35:
        # 35% 绯红 / 猩红 / 玫瑰红 (Hue 342° ~ 8°)
        local_t = t / 0.35
        hue = (342 + local_t * 26) % 360
        sat = 74 + 12 * math.tanh(w * 2.0)
        light = 52 + 10 * math.tanh(z * 2.0)
    elif t < 0.55:
        # 20% 铁锈红 / 焦糖铜 / 暗琥珀 (Hue 12° ~ 34°)
        local_t = (t - 0.35) / 0.20
        hue = 12 + local_t * 22
        sat = 64 + 12 * math.tanh(w * 2.0)
        light = 53 + 9 * math.tanh(z * 2.0)
    elif t < 0.78:
        # 23% 梅子暗紫 / 勃艮第酒红 / 暮紫 (Hue 278° ~ 332°)
        local_t = (t - 0.55) / 0.23
        hue = 278 + local_t * 54
        sat = 50 + 16 * math.tanh(w * 2.0)
        light = 54 + 10 * math.tanh(z * 2.0)
    else:
        # 22% 烟熏冷钢蓝 / 暗银灰蓝 (Hue 210° ~ 242°，低饱和冷调作冷暖对比)
        local_t = (t - 0.78) / 0.22
        hue = 210 + local_t * 32
        sat = 28 + 14 * math.tanh(w * 2.0)
        light = 56 + 11 * math.tanh(z * 2.0)

    h = hue / 360.0
    s = sat / 100.0
    l = light / 100.0

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = int(hue_to_rgb(p, q, h + 1/3) * 255)
    g = int(hue_to_rgb(p, q, h) * 255)
    b = int(hue_to_rgb(p, q, h - 1/3) * 255)

    return f"#{r:02x}{g:02x}{b:02x}"

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class MemoryEngine:
    def __init__(self):
        self._graph_cache: Optional[GraphResponse] = None
        self._graph_lock = threading.Lock()

    def invalidate_graph_cache(self):
        self._graph_cache = None

    def ensure_mood_color(self, db: Session, diary: Diary, commit: bool = True) -> str:
        """优先读取持久化的 mood_color，仅在缺失时计算并回填"""
        if diary.mood_color:
            return diary.mood_color
        vec = llm_service.get_embedding(diary.content[:200])
        if not vec:
            return "#dc143c"
        color = vector_to_hex_color(vec)
        diary.mood_color = color
        if commit:
            db.commit()
        return color

    def recolor_all_diaries(self, db: Session) -> int:
        """使用最新色域算法批量重算所有日记的 mood_color（优先复用 LanceDB 缓存向量）"""
        cached_vectors = {}
        try:
            tbl_data = vector_store.table.to_arrow()
            for did, vec in zip(tbl_data["diary_id"].to_pylist(), tbl_data["vector"].to_pylist()):
                cached_vectors[did] = vec
        except Exception:
            pass

        diaries = db.query(Diary).all()
        updated = 0
        for d in diaries:
            vec = cached_vectors.get(d.id) or llm_service.get_embedding(d.content[:100])
            new_color = vector_to_hex_color(vec)
            if d.mood_color != new_color:
                d.mood_color = new_color
                updated += 1
        if updated > 0:
            db.commit()
        return updated

    def sync_diary_quotes(self, db: Session, diary_id: int, quoted_diary_ids: Optional[List[int]]):
        """同步某篇日记引用的历史日记列表（传入 None 时保持不变）"""
        if quoted_diary_ids is None:
            return
        seen = set()
        clean_ids: List[int] = []
        for qid in quoted_diary_ids:
            if isinstance(qid, int) and qid != diary_id and qid not in seen:
                seen.add(qid)
                clean_ids.append(qid)

        db.query(DiaryQuote).filter(DiaryQuote.diary_id == diary_id).delete(synchronize_session=False)
        if clean_ids:
            valid_ids = {
                row[0] for row in db.query(Diary.id).filter(Diary.id.in_(clean_ids)).all()
            }
            for qid in clean_ids:
                if qid in valid_ids:
                    db.add(DiaryQuote(diary_id=diary_id, quoted_diary_id=qid))
        db.commit()

    def build_diary_out_list(self, db: Session, diaries: List[Diary]) -> List[DiaryOut]:
        """批量组装 DiaryOut，包含实体标签、情绪色及双向引用关系"""
        if not diaries:
            return []

        diary_ids = [d.id for d in diaries]
        quote_rows = (
            db.query(DiaryQuote)
            .filter(or_(DiaryQuote.diary_id.in_(diary_ids), DiaryQuote.quoted_diary_id.in_(diary_ids)))
            .order_by(DiaryQuote.id.asc())
            .all()
        )

        ref_ids: Set[int] = set()
        for q in quote_rows:
            ref_ids.add(q.diary_id)
            ref_ids.add(q.quoted_diary_id)

        diary_map: Dict[int, Diary] = {d.id: d for d in diaries}
        missing_ids = ref_ids - set(diary_map.keys())
        if missing_ids:
            for rd in db.query(Diary).filter(Diary.id.in_(missing_ids)).all():
                diary_map[rd.id] = rd

        quoted_map: Dict[int, List[DiaryQuoteRef]] = {did: [] for did in diary_ids}
        quoted_by_map: Dict[int, List[DiaryQuoteRef]] = {did: [] for did in diary_ids}

        def _to_ref(d: Diary) -> DiaryQuoteRef:
            return DiaryQuoteRef(
                id=d.id,
                content=d.content,
                summary=d.summary,
                mood=d.mood,
                mood_color=d.mood_color or "#dc143c",
                created_at=d.created_at,
            )

        for q in quote_rows:
            if q.diary_id in quoted_map and q.quoted_diary_id in diary_map:
                quoted_map[q.diary_id].append(_to_ref(diary_map[q.quoted_diary_id]))
            if q.quoted_diary_id in quoted_by_map and q.diary_id in diary_map:
                quoted_by_map[q.quoted_diary_id].append(_to_ref(diary_map[q.diary_id]))

        results: List[DiaryOut] = []
        color_backfilled = False
        for d in diaries:
            had_color = bool(d.mood_color)
            color = self.ensure_mood_color(db, d, commit=False)
            if not had_color:
                color_backfilled = True
            quoted_by_sorted = sorted(quoted_by_map.get(d.id, []), key=lambda x: x.created_at, reverse=True)
            results.append(DiaryOut(
                id=d.id,
                content=d.content,
                summary=d.summary,
                mood=d.mood,
                mood_color=color,
                created_at=d.created_at,
                entities=[b.entity.name for b in d.entities if b.entity],
                quoted_diaries=quoted_map.get(d.id, []),
                quoted_by=quoted_by_sorted,
            ))
        if color_backfilled:
            db.commit()
        return results

    def build_diary_out(self, db: Session, diary: Diary) -> DiaryOut:
        return self.build_diary_out_list(db, [diary])[0]

    def create_diary_immediate(self, db: Session, content: str, created_at: Optional[datetime.datetime] = None) -> Diary:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        first_line = lines[0] if lines else content[:30]
        summary = first_line[:40]

        if created_at and created_at.tzinfo is not None:
            created_at = created_at.astimezone().replace(tzinfo=None)

        diary = Diary(
            content=content,
            summary=summary,
            mood=None,
            created_at=created_at if created_at else datetime.datetime.now()
        )
        db.add(diary)
        db.commit()
        db.refresh(diary)
        return diary

    def update_diary_immediate(self, db: Session, diary_id: int, new_content: str, created_at: Optional[datetime.datetime] = None) -> Diary:
        diary = db.query(Diary).filter(Diary.id == diary_id).first()
        if not diary:
            return None

        diary.content = new_content
        lines = [line.strip() for line in new_content.splitlines() if line.strip()]
        first_line = lines[0] if lines else new_content[:30]
        diary.summary = first_line[:40]

        if created_at is not None:
            if created_at.tzinfo is not None:
                created_at = created_at.astimezone().replace(tzinfo=None)
            diary.created_at = created_at

        db.commit()
        db.refresh(diary)
        return diary

    def process_single_diary_memory(self, diary_id: int, raise_on_llm_error: bool = False) -> DiaryOut:
        db = SessionLocal()
        try:
            diary = db.query(Diary).filter(Diary.id == diary_id).first()
            if not diary:
                return None

            content = diary.content
            chunks = llm_service.split_text_chunks(content)
            chunk_vectors: List[Dict[str, Any]] = []
            primary_vector: Optional[List[float]] = None

            for idx, chunk_text in enumerate(chunks):
                vec = None
                for _ in range(2):
                    try:
                        vec = llm_service.get_embedding(chunk_text)
                        if vec and len(vec) == 1024:
                            break
                    except Exception:
                        time.sleep(0.4)
                if vec and len(vec) == 1024:
                    if primary_vector is None:
                        primary_vector = vec
                    chunk_vectors.append({"content": chunk_text, "vector": vec})

            if primary_vector:
                diary.mood_color = vector_to_hex_color(primary_vector)
                try:
                    vector_store.delete_by_diary_id(diary.id)
                    vector_store.add_diary_vectors(
                        diary_id=diary.id,
                        chunks=chunk_vectors,
                        created_at=diary.created_at.isoformat()
                    )
                except Exception as e:
                    print(f"[LanceDB error]: {e}")

            try:
                extracted = llm_service.extract_entities_and_relations(
                    content,
                    diary_date=diary.created_at,
                    raise_on_error=raise_on_llm_error
                )
                if extracted.get("summary"):
                    diary.summary = extracted.get("summary")
                if extracted.get("mood"):
                    diary.mood = extracted.get("mood")

                db.query(DiaryEntity).filter(DiaryEntity.diary_id == diary.id).delete()
                db.query(EntityRelation).filter(EntityRelation.diary_id == diary.id).delete()
                db.commit()

                self._save_entities_and_relations(db, diary, extracted)
                self.cleanup_orphan_entities(db)
            except Exception as e:
                print(f"[LLM error]: {e}")
                if raise_on_llm_error:
                    raise

            self.invalidate_graph_cache()
            db.refresh(diary)
            return self.build_diary_out(db, diary)
        finally:
            db.close()

    def get_cluster_graph_2d(self, db: Session) -> GraphResponse:
        """
        记忆动力学混合聚类星系图：
        1. 向量相似度 (Vector Distance)：使用内存矩阵乘法批量计算，避免循环检索 LanceDB 与同步阻塞请求 Ollama；
        2. 共享实体引力 (Shared Entity Attraction)：当两篇日记共同提及特定实体、地点或核心话题时，产生强弹簧引力；
        3. 心境共鸣 (Mood Resonance)：相同心境赋予轻微共鸣引力。
        """
        if self._graph_cache is not None:
            return self._graph_cache

        with self._graph_lock:
            if self._graph_cache is not None:
                return self._graph_cache

            diaries = (
                db.query(Diary)
                .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
                .all()
            )
            if not diaries:
                return GraphResponse(nodes=[], links=[])

            cached_vectors: Dict[int, List[float]] = {}
            try:
                tbl_data = vector_store.table.to_arrow()
                diary_ids = tbl_data["diary_id"].to_pylist()
                vectors = tbl_data["vector"].to_pylist()
                for did, vec in zip(diary_ids, vectors):
                    if did not in cached_vectors and vec:
                        cached_vectors[did] = vec
            except Exception:
                pass

            all_items = []
            diary_map: Dict[int, Diary] = {}
            diary_entities_map: Dict[int, Set[str]] = {}
            entity_to_diaries: Dict[str, Set[int]] = {}
            color_backfilled = False

            for d in diaries:
                vec = cached_vectors.get(d.id)
                if not d.mood_color and vec:
                    d.mood_color = vector_to_hex_color(vec)
                    color_backfilled = True
                all_items.append(d)
                diary_map[d.id] = d
                ent_set = set(b.entity.name for b in d.entities if b.entity)
                diary_entities_map[d.id] = ent_set
                for ent_name in ent_set:
                    entity_to_diaries.setdefault(ent_name, set()).add(d.id)

            if color_backfilled:
                db.commit()

            # 内存向量矩阵批量计算余弦相似度，彻底消除循环内 N 次 LanceDB 磁盘检索
            vec_ids = [d.id for d in all_items if cached_vectors.get(d.id)]
            id_to_idx: Dict[int, int] = {did: idx for idx, did in enumerate(vec_ids)}
            sim_matrix = None
            if len(vec_ids) > 1:
                mat = np.asarray([cached_vectors[did] for did in vec_ids], dtype=np.float32)
                norms = np.linalg.norm(mat, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                mat_norm = mat / norms
                sim_matrix = mat_norm @ mat_norm.T

            use_ann = len(all_items) > 50 and sim_matrix is not None
            links: List[GraphLink] = []
            node_degree: Dict[int, int] = {d.id: 0 for d in all_items}
            existing_edges = set()

            # 优先加入显式引用关系边
            for q in db.query(DiaryQuote).all():
                if q.diary_id in diary_map and q.quoted_diary_id in diary_map and q.diary_id != q.quoted_diary_id:
                    pair = tuple(sorted([q.diary_id, q.quoted_diary_id]))
                    if pair not in existing_edges:
                        existing_edges.add(pair)
                        links.append(GraphLink(
                            source=pair[0],
                            target=pair[1],
                            value=3.0,
                            reason="引用关联"
                        ))
                        node_degree[pair[0]] += 1
                        node_degree[pair[1]] += 1

            for d1 in all_items:
                e1 = diary_entities_map.get(d1.id, set())
                idx1 = id_to_idx.get(d1.id)
                candidates = []

                if use_ann:
                    cand_ids: Set[int] = set()
                    for ent_name in e1:
                        cand_ids.update(entity_to_diaries.get(ent_name, set()))
                    if idx1 is not None:
                        sims = sim_matrix[idx1]
                        top_k = min(17, len(vec_ids))
                        top_indices = np.argpartition(sims, -top_k)[-top_k:]
                        for tidx in top_indices:
                            if tidx != idx1:
                                cand_ids.add(vec_ids[int(tidx)])
                    cand_ids.discard(d1.id)
                    peer_items = [diary_map[cid] for cid in cand_ids if cid in diary_map]
                else:
                    peer_items = [d2 for d2 in all_items if d2.id != d1.id]

                for d2 in peer_items:
                    e2 = diary_entities_map.get(d2.id, set())
                    idx2 = id_to_idx.get(d2.id)
                    if sim_matrix is not None and idx1 is not None and idx2 is not None:
                        cos_sim = float(sim_matrix[idx1, idx2])
                    else:
                        cos_sim = 0.0

                    shared_ents = e1 & e2
                    shared_count = len(shared_ents)

                    # 混合打分公式：向量基础分 + 共享实体大幅加权 + 心境共鸣
                    if shared_count > 0:
                        ent_ratio = shared_count / max(1, len(e1 | e2))
                        mood_bonus = 0.08 if (d1.mood and d1.mood == d2.mood) else 0.0
                        composite_sim = 0.45 * cos_sim + 0.45 * (0.6 + 0.4 * ent_ratio) + mood_bonus
                        reason = f"共同提及: {'、'.join(list(shared_ents)[:3])}"
                    else:
                        mood_bonus = 0.04 if (d1.mood and d1.mood == d2.mood) else 0.0
                        composite_sim = 0.9 * cos_sim + mood_bonus
                        reason = "语义共鸣"

                    candidates.append((d2.id, composite_sim, reason, shared_count))

                # 优先连接共享实体的日记，再连接纯语义近邻
                candidates.sort(key=lambda x: (x[3] > 0, x[1]), reverse=True)

                # 为每个节点保留最强前 3 条纽带
                for target_id, sim, link_reason, sc in candidates[:3]:
                    pair = tuple(sorted([d1.id, target_id]))
                    threshold = 0.40 if sc > 0 else 0.46
                    if pair not in existing_edges and sim > threshold:
                        existing_edges.add(pair)
                        # 共享实体的连线给予更高的弹性张力
                        link_val = round(sim * (2.8 if sc > 0 else 1.8), 2)
                        links.append(GraphLink(
                            source=pair[0],
                            target=pair[1],
                            value=link_val,
                            reason=link_reason
                        ))
                        node_degree[pair[0]] += 1
                        node_degree[pair[1]] += 1

            nodes: List[GraphNode] = []
            for d in all_items:
                deg = node_degree.get(d.id, 0)
                ents = list(diary_entities_map.get(d.id, set()))
                # 实体丰富的枢纽节点稍大一些，作为星系核心
                node_size = round(max(5.0, min(16.0, 5.0 + deg * 1.5 + len(ents) * 0.8)), 1)
                vec = cached_vectors.get(d.id)
                color = d.mood_color or (vector_to_hex_color(vec) if vec else "#dc143c")
                title = d.summary if d.summary else d.content[:25]

                nodes.append(GraphNode(
                    id=d.id,
                    name=title,
                    color=color,
                    val=node_size,
                    content=d.content,
                    created_at=d.created_at.strftime("%Y-%m-%d"),
                    entities=ents,
                    mood=d.mood
                ))

            resp = GraphResponse(nodes=nodes, links=links)
            self._graph_cache = resp
            return resp

    def _save_entities_and_relations(self, db: Session, diary: Diary, extracted: dict):
        entities_data = extracted.get("entities", [])
        for ent_item in entities_data:
            name = str(ent_item.get("name") or "").strip()
            if not name or name.lower() in ["null", "none"]:
                continue
            entity = db.query(Entity).filter(Entity.name == name).first()
            if not entity:
                entity = Entity(
                    name=name,
                    entity_type=ent_item.get("entity_type", "concept"),
                    description=ent_item.get("description", "")
                )
                db.add(entity)
                db.commit()
                db.refresh(entity)

            existing_bridge = db.query(DiaryEntity).filter(
                DiaryEntity.diary_id == diary.id,
                DiaryEntity.entity_id == entity.id
            ).first()
            if not existing_bridge:
                bridge = DiaryEntity(diary_id=diary.id, entity_id=entity.id)
                db.add(bridge)

        relations_data = extracted.get("relations", [])
        for rel in relations_data:
            s_name = str(rel.get("source") or "").strip()
            r_type = str(rel.get("relation") or "").strip()
            t_name = str(rel.get("target") or "").strip()
            if s_name and t_name and r_type and s_name.lower() != "null" and t_name.lower() != "null":
                existing = db.query(EntityRelation).filter(
                    EntityRelation.diary_id == diary.id,
                    EntityRelation.source_name == s_name,
                    EntityRelation.relation == r_type,
                    EntityRelation.target_name == t_name
                ).first()
                if not existing:
                    new_rel = EntityRelation(
                        diary_id=diary.id,
                        source_name=s_name,
                        relation=r_type,
                        target_name=t_name
                    )
                    db.add(new_rel)

        db.commit()

    def cleanup_orphan_entities(self, db: Session):
        """
        自动垃圾回收：
        1. 清理所属日记已不存在的孤立自动提取关系（diary_id 非空但日记已删除）；
        2. 检查所有实体，若在 diary_entities 桥接表中没有被任何日记引用（引用计数为 0），
           则自动物理删除该孤儿实体及其孤立关系，并同步从本地知识库中清除。
        """
        valid_diary_ids = db.query(Diary.id)
        db.query(EntityRelation).filter(
            EntityRelation.diary_id.isnot(None),
            ~EntityRelation.diary_id.in_(valid_diary_ids)
        ).delete(synchronize_session=False)

        orphans = (
            db.query(Entity)
            .outerjoin(DiaryEntity, DiaryEntity.entity_id == Entity.id)
            .group_by(Entity.id)
            .having(func.count(DiaryEntity.id) == 0)
            .all()
        )
        if orphans:
            orphan_names = [e.name for e in orphans]
            orphan_ids = [e.id for e in orphans]

            # 清理孤立图谱边
            db.query(EntityRelation).filter(
                or_(EntityRelation.source_name.in_(orphan_names), EntityRelation.target_name.in_(orphan_names))
            ).delete(synchronize_session=False)

            # 从实体表中删除
            db.query(Entity).filter(Entity.id.in_(orphan_ids)).delete(synchronize_session=False)

            # 同步从知识库中移除无引用的孤儿标签
            for name in orphan_names:
                knowledge_base.remove_entity(name)

        db.commit()

    def hybrid_associative_search(self, db: Session, query: str, limit: int = 20) -> SearchResponse:
        expanded_entities: Set[str] = set()
        direct_matched_entities: Set[str] = set()
        entity_reason_map: Dict[str, str] = {}

        # 1. 整词别名对齐 + 从自然语言查询中扫描已知实体/别名
        canonical = knowledge_base.resolve_entity(query)
        if canonical != query:
            expanded_entities.add(canonical)
            direct_matched_entities.add(canonical)
            entity_reason_map[canonical] = f"别名「{query}」→「{canonical}」"

        for scanned in knowledge_base.scan_custom_entities(query):
            c_name = scanned["name"]
            expanded_entities.add(c_name)
            direct_matched_entities.add(c_name)
            if c_name not in entity_reason_map:
                if scanned.get("alias_source"):
                    entity_reason_map[c_name] = f"别名「{scanned['alias_source']}」→「{c_name}」"
                else:
                    entity_reason_map[c_name] = f"标签「{c_name}」"

        all_entities = db.query(Entity).all()
        query_lower = query.lower()
        direct_entities = [
            ent for ent in all_entities
            if query_lower in ent.name.lower()
            or (ent.description and query_lower in ent.description.lower())
            or (len(ent.name) >= 2 and ent.name.lower() in query_lower)
        ]

        for ent in direct_entities:
            expanded_entities.add(ent.name)
            direct_matched_entities.add(ent.name)
            if ent.name not in entity_reason_map:
                entity_reason_map[ent.name] = f"标签「{ent.name}」"

            relations = db.query(EntityRelation).filter(
                EntityRelation.relation != "alias_of",
                or_(EntityRelation.source_name == ent.name, EntityRelation.target_name == ent.name)
            ).all()

            for r in relations:
                other = r.target_name if r.source_name == ent.name else r.source_name
                if other not in expanded_entities:
                    expanded_entities.add(other)
                    rel_label = (r.relation or "").strip()
                    if rel_label and rel_label not in ("提及", "相关", "关联"):
                        entity_reason_map[other] = f"关联「{other}」（与「{ent.name}」· {rel_label}）"
                    else:
                        entity_reason_map[other] = f"关联「{other}」（与「{ent.name}」相关）"

        # 2. 图谱实体召回
        graph_diary_scores: Dict[int, Dict[str, Any]] = {}
        if expanded_entities:
            matched_bridges = (
                db.query(DiaryEntity)
                .options(joinedload(DiaryEntity.entity))
                .join(Entity)
                .filter(Entity.name.in_(list(expanded_entities)))
                .all()
            )
            for b in matched_bridges:
                did = b.diary_id
                ent_name = b.entity.name if b.entity else ""
                if not ent_name:
                    continue
                if did not in graph_diary_scores:
                    graph_diary_scores[did] = {
                        "diary_id": did,
                        "direct_hits": 1 if ent_name in direct_matched_entities else 0,
                        "entities": [ent_name]
                    }
                else:
                    if ent_name not in graph_diary_scores[did]["entities"]:
                        graph_diary_scores[did]["entities"].append(ent_name)
                        if ent_name in direct_matched_entities:
                            graph_diary_scores[did]["direct_hits"] += 1

            for info in graph_diary_scores.values():
                direct_ents = [e for e in info["entities"] if e in direct_matched_entities]
                target_ents = direct_ents if direct_ents else info["entities"]
                reasons = []
                for e in target_ents:
                    r_text = entity_reason_map.get(e, f"标签「{e}」")
                    if r_text not in reasons:
                        reasons.append(r_text)
                info["reasons"] = reasons

        graph_ranked_ids = [
            did for did, _ in sorted(
                graph_diary_scores.items(),
                key=lambda kv: (kv[1]["direct_hits"], len(kv[1]["entities"])),
                reverse=True
            )
        ]

        # 3. 向量语义召回（余弦相似度 + 阈值过滤）
        query_vector = llm_service.get_embedding(query)
        vector_diary_scores: Dict[int, float] = {}
        if query_vector:
            vector_matches = vector_store.search_similar(query_vector, limit=max(limit * 2, 30))
            for vm in vector_matches:
                did = vm.get("diary_id")
                if did is None:
                    continue
                distance = float(vm.get("_distance", 1.0))
                sim = max(0.0, 1.0 - distance)
                if sim >= 0.30:
                    vector_diary_scores[did] = sim

        vector_ranked_ids = [
            did for did, _ in sorted(vector_diary_scores.items(), key=lambda kv: kv[1], reverse=True)
        ]

        # 4. 关键词全文召回（始终参与 RRF 融合，避免精确词被向量淹没）
        terms = [t.strip() for t in re.split(r'[\s,，。！？、；;]+', query) if t.strip()]
        if not terms:
            terms = [query]
        term_filters = []
        for t in terms[:6]:
            term_filters.append(Diary.content.ilike(f"%{t}%"))
            term_filters.append(Diary.summary.ilike(f"%{t}%"))
        keyword_candidates = (
            db.query(Diary.id, Diary.content, Diary.summary, Diary.created_at)
            .filter(or_(*term_filters))
            .order_by(Diary.created_at.desc())
            .limit(max(limit * 2, 40))
            .all()
        )
        keyword_hits: Dict[int, int] = {}
        for row in keyword_candidates:
            haystack = f"{row.summary or ''}\n{row.content or ''}".lower()
            hit_cnt = sum(1 for t in terms if t.lower() in haystack)
            if hit_cnt > 0:
                keyword_hits[row.id] = hit_cnt
        keyword_ranked_ids = [
            did for did, _ in sorted(keyword_hits.items(), key=lambda kv: kv[1], reverse=True)
        ]

        # 5. RRF 倒数排名融合 (Graph + Vector + Keyword)
        rrf_k = 30.0
        rrf_scores: Dict[int, float] = {}
        for rank, did in enumerate(graph_ranked_ids, start=1):
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.35 / (rrf_k + rank)
        for rank, did in enumerate(vector_ranked_ids, start=1):
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.0 / (rrf_k + rank)
        for rank, did in enumerate(keyword_ranked_ids, start=1):
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.15 / (rrf_k + rank)

        all_diary_ids = set(rrf_scores.keys())
        if not all_diary_ids:
            return SearchResponse(query=query, expanded_entities=list(expanded_entities), results=[])

        diaries = (
            db.query(Diary)
            .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
            .filter(Diary.id.in_(list(all_diary_ids)))
            .all()
        )
        diary_map = {d.id: d for d in diaries}

        result_items: List[SearchResultItem] = []
        color_backfilled = False
        for did in all_diary_ids:
            d = diary_map.get(did)
            if not d:
                continue

            v_score = vector_diary_scores.get(did, 0.0)
            g_info = graph_diary_scores.get(did)
            k_hits = keyword_hits.get(did, 0)
            final_score = rrf_scores[did]

            reasons: List[str] = []
            if g_info:
                reasons.extend(g_info["reasons"])
            if k_hits > 0:
                reasons.append(f"包含「{query}」" if len(terms) == 1 else f"匹配 {k_hits} 个关键词")
            if not reasons and v_score > 0:
                reasons.append("语义相近")

            rel_ents = g_info["entities"] if g_info else [b.entity.name for b in d.entities if b.entity]

            had_color = bool(d.mood_color)
            color = self.ensure_mood_color(db, d, commit=False)
            if not had_color:
                color_backfilled = True

            result_items.append(SearchResultItem(
                diary_id=d.id,
                content=d.content,
                created_at=d.created_at,
                summary=d.summary,
                mood=d.mood,
                mood_color=color,
                score=round(float(final_score) * 10, 3),
                matched_reason=" · ".join(reasons[:3]),
                related_entities=rel_ents
            ))

        if color_backfilled:
            db.commit()

        result_items.sort(key=lambda x: x.score, reverse=True)

        return SearchResponse(
            query=query,
            expanded_entities=list(expanded_entities),
            results=result_items[:limit]
        )

    def get_related_diaries(self, db: Session, diary_id: int, limit: int = 5) -> List[SearchResultItem]:
        """为指定日记推荐最相关的历史记忆（向量相似度 + 共享实体 + 心境共鸣）"""
        target = (
            db.query(Diary)
            .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
            .filter(Diary.id == diary_id)
            .first()
        )
        if not target:
            return []

        target_entities = {b.entity.name for b in target.entities if b.entity}

        # 优先复用 LanceDB 中该日记的向量
        target_vec: Optional[List[float]] = None
        try:
            tbl_data = vector_store.table.to_arrow()
            for did, vec in zip(tbl_data["diary_id"].to_pylist(), tbl_data["vector"].to_pylist()):
                if did == diary_id:
                    target_vec = vec
                    break
        except Exception:
            pass
        if not target_vec:
            target_vec = llm_service.get_embedding(target.content[:800])

        vector_scores: Dict[int, float] = {}
        if target_vec:
            for vm in vector_store.search_similar(target_vec, limit=max(limit * 3, 15)):
                did = vm.get("diary_id")
                if did is None or did == diary_id:
                    continue
                sim = max(0.0, 1.0 - float(vm.get("_distance", 1.0)))
                if sim >= 0.35:
                    vector_scores[did] = sim

        # 共享实体候选
        entity_candidate_ids: Set[int] = set()
        if target_entities:
            bridges = (
                db.query(DiaryEntity.diary_id)
                .join(Entity)
                .filter(Entity.name.in_(list(target_entities)), DiaryEntity.diary_id != diary_id)
                .all()
            )
            entity_candidate_ids = {row[0] for row in bridges}

        candidate_ids = set(vector_scores.keys()) | entity_candidate_ids
        if not candidate_ids:
            return []

        peers = (
            db.query(Diary)
            .options(joinedload(Diary.entities).joinedload(DiaryEntity.entity))
            .filter(Diary.id.in_(list(candidate_ids)))
            .all()
        )

        items: List[SearchResultItem] = []
        for p in peers:
            p_ents = {b.entity.name for b in p.entities if b.entity}
            shared = target_entities & p_ents
            v_sim = vector_scores.get(p.id, 0.0)
            mood_bonus = 0.08 if (target.mood and target.mood == p.mood) else 0.0

            if shared:
                ent_ratio = len(shared) / max(1, len(target_entities | p_ents))
                score = 0.45 * v_sim + 0.47 * (0.55 + 0.45 * ent_ratio) + mood_bonus
                reason = f"共同提及: {'、'.join(list(shared)[:3])}"
            else:
                score = 0.9 * v_sim + mood_bonus
                reason = "语义相近" if not mood_bonus else f"语义相近 · 同为「{p.mood}」"

            if score < 0.35:
                continue

            items.append(SearchResultItem(
                diary_id=p.id,
                content=p.content,
                created_at=p.created_at,
                summary=p.summary,
                mood=p.mood,
                mood_color=p.mood_color or "#dc143c",
                score=round(float(score), 3),
                matched_reason=reason,
                related_entities=list(p_ents)
            ))

        items.sort(key=lambda x: x.score, reverse=True)
        return items[:limit]

    def get_entity_graph(self, db: Session) -> EntityGraphResponse:
        """构建实体与关系知识图谱，供前端可视化"""
        self.cleanup_orphan_entities(db)
        owner_name = knowledge_base.get_owner_name()
        custom_entities = knowledge_base.get_all().get("custom_entities", {})

        counts = dict(
            db.query(Entity.name, func.count(DiaryEntity.id))
            .join(DiaryEntity, DiaryEntity.entity_id == Entity.id, isouter=True)
            .group_by(Entity.name)
            .all()
        )

        node_map: Dict[str, EntityGraphNode] = {}
        for ent in db.query(Entity).all():
            node_map[ent.name] = EntityGraphNode(
                id=ent.name,
                name=ent.name,
                entity_type=custom_entities.get(ent.name, ent.entity_type or "concept"),
                count=counts.get(ent.name, 0),
                is_owner=(ent.name == owner_name)
            )

        links: List[EntityGraphLink] = []
        seen_triples: Set[tuple] = set()
        for rel in db.query(EntityRelation).filter(EntityRelation.relation != "alias_of").order_by(EntityRelation.id.desc()).all():
            triple = (rel.source_name, rel.relation, rel.target_name)
            if triple in seen_triples:
                continue
            seen_triples.add(triple)

            for endpoint in (rel.source_name, rel.target_name):
                if endpoint not in node_map:
                    node_map[endpoint] = EntityGraphNode(
                        id=endpoint,
                        name=endpoint,
                        entity_type="person" if endpoint == owner_name else custom_entities.get(endpoint, "concept"),
                        count=counts.get(endpoint, 0),
                        is_owner=(endpoint == owner_name)
                    )

            links.append(EntityGraphLink(
                source=rel.source_name,
                target=rel.target_name,
                relation=rel.relation,
                weight=rel.weight or 1.0
            ))

        return EntityGraphResponse(nodes=list(node_map.values()), links=links)

memory_engine = MemoryEngine()
