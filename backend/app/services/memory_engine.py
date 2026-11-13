import time
import math
import datetime
from typing import List, Dict, Any, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models import Diary, Entity, EntityRelation, DiaryEntity
from app.services.llm_client import llm_service
from app.services.vector_store import vector_store
from app.schemas import SearchResultItem, SearchResponse, DiaryOut, GraphResponse, GraphNode, GraphLink
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
    def ensure_mood_color(self, db: Session, diary: Diary, commit: bool = True) -> str:
        """优先读取持久化的 mood_color，仅在缺失时计算并回填"""
        if diary.mood_color:
            return diary.mood_color
        vec = llm_service.get_embedding(diary.content[:100])
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
            vector = None
            for attempt in range(3):
                try:
                    vector = llm_service.get_embedding(content)
                    if vector and len(vector) == 1024:
                        break
                except Exception:
                    time.sleep(0.5)

            if vector:
                diary.mood_color = vector_to_hex_color(vector)
                try:
                    vector_store.delete_by_diary_id(diary.id)
                    vector_store.add_diary_vector(
                        diary_id=diary.id,
                        content=content,
                        vector=vector,
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
                if extracted.get("mood"):
                    diary.mood = extracted.get("mood")

                db.query(DiaryEntity).filter(DiaryEntity.diary_id == diary.id).delete()
                db.commit()

                self._save_entities_and_relations(db, diary, extracted)
                self.cleanup_orphan_entities(db)
            except Exception as e:
                print(f"[LLM error]: {e}")
                if raise_on_llm_error:
                    raise

            db.refresh(diary)
            color = diary.mood_color or vector_to_hex_color(vector)
            return DiaryOut(
                id=diary.id,
                content=diary.content,
                summary=diary.summary,
                mood=diary.mood,
                mood_color=color,
                created_at=diary.created_at,
                entities=[b.entity.name for b in diary.entities if b.entity]
            )
        finally:
            db.close()

    def get_cluster_graph_2d(self, db: Session) -> GraphResponse:
        """
        记忆动力学混合聚类星系图：
        1. 向量相似度 (Vector Distance)：反映日记行文、语言风格与隐式语义距离；
        2. 共享实体引力 (Shared Entity Attraction)：当两篇日记共同提及特定实体（包括别名归一后的同义实体）、地点或核心话题时，产生强弹簧引力；
        3. 心境共鸣 (Mood Resonance)：相同心境赋予轻微共鸣引力；
        4. 真正形成如参考图所示的“围绕人物与核心事件的高度致密群落（Community Clusters）”。
        """
        diaries = db.query(Diary).all()
        if not diaries:
            return GraphResponse(nodes=[], links=[])

        cached_vectors = {}
        try:
            tbl_data = vector_store.table.to_arrow()
            diary_ids = tbl_data["diary_id"].to_pylist()
            vectors = tbl_data["vector"].to_pylist()
            for did, vec in zip(diary_ids, vectors):
                cached_vectors[did] = vec
        except Exception:
            pass

        all_items = []
        diary_map: Dict[int, Diary] = {}
        diary_entities_map: Dict[int, Set[str]] = {}
        entity_to_diaries: Dict[str, Set[int]] = {}
        color_backfilled = False

        for d in diaries:
            vec = cached_vectors.get(d.id) or llm_service.get_embedding(d.content[:100])
            cached_vectors[d.id] = vec
            if not d.mood_color:
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

        use_ann = len(all_items) > 50 and len(vector_store.table) > 0
        links: List[GraphLink] = []
        node_degree: Dict[int, int] = {d.id: 0 for d in all_items}
        existing_edges = set()

        for d1 in all_items:
            v1 = cached_vectors[d1.id]
            e1 = diary_entities_map.get(d1.id, set())
            candidates = []

            if use_ann:
                cand_ids: Set[int] = set()
                for ent_name in e1:
                    cand_ids.update(entity_to_diaries.get(ent_name, set()))
                for vm in vector_store.search_similar(v1, limit=16):
                    vid = vm.get("diary_id")
                    if vid is not None:
                        cand_ids.add(vid)
                cand_ids.discard(d1.id)
                peer_items = [diary_map[cid] for cid in cand_ids if cid in diary_map]
            else:
                peer_items = [d2 for d2 in all_items if d2.id != d1.id]

            for d2 in peer_items:
                v2 = cached_vectors[d2.id]
                e2 = diary_entities_map.get(d2.id, set())

                cos_sim = cosine_similarity(v1, v2)
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
            color = d.mood_color or vector_to_hex_color(cached_vectors[d.id])
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

        return GraphResponse(nodes=nodes, links=links)

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
                    EntityRelation.source_name == s_name,
                    EntityRelation.relation == r_type,
                    EntityRelation.target_name == t_name
                ).first()
                if not existing:
                    new_rel = EntityRelation(
                        source_name=s_name,
                        relation=r_type,
                        target_name=t_name
                    )
                    db.add(new_rel)

        db.commit()

    def cleanup_orphan_entities(self, db: Session):
        """
        自动垃圾回收：
        检查所有实体，若在 diary_entities 桥接表中没有被任何日记引用（引用计数为 0），
        则自动物理删除该孤儿实体及其孤立关系，并同步从本地知识库中清除。
        """
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
            db.commit()

            # 同步从知识库中移除无引用的孤儿标签
            for name in orphan_names:
                knowledge_base.remove_entity(name)

    def hybrid_associative_search(self, db: Session, query: str, limit: int = 20) -> SearchResponse:
        expanded_entities: Set[str] = set()
        entity_reason_map: Dict[str, str] = {}

        # 知识库别名对齐（如搜索别名自动扩展主实体）
        canonical = knowledge_base.resolve_entity(query)
        if canonical != query:
            expanded_entities.add(canonical)
            entity_reason_map[canonical] = f"别名映射:「{query}」即「{canonical}」"

        direct_entities = db.query(Entity).filter(
            or_(Entity.name.ilike(f"%{query}%"), Entity.description.ilike(f"%{query}%"))
        ).all()

        for ent in direct_entities:
            expanded_entities.add(ent.name)
            entity_reason_map[ent.name] = f"命中实体「{ent.name}」"

            relations = db.query(EntityRelation).filter(
                or_(EntityRelation.source_name == ent.name, EntityRelation.target_name == ent.name)
            ).all()

            for r in relations:
                other = r.target_name if r.source_name == ent.name else r.source_name
                if other not in expanded_entities:
                    expanded_entities.add(other)
                    entity_reason_map[other] = f"图扩散召回: 与「{ent.name}」关系「{r.relation}」"

        graph_diary_scores: Dict[int, Dict[str, Any]] = {}
        if expanded_entities:
            matched_bridges = db.query(DiaryEntity).join(Entity).filter(
                Entity.name.in_(list(expanded_entities))
            ).all()
            for b in matched_bridges:
                did = b.diary_id
                ent_name = b.entity.name if b.entity else ""
                if not ent_name:
                    continue
                reason = entity_reason_map.get(ent_name, f"提及实体「{ent_name}」")
                if did not in graph_diary_scores:
                    graph_diary_scores[did] = {
                        "diary_id": did,
                        "boost": 1.2,
                        "reasons": [reason],
                        "entities": [ent_name]
                    }
                else:
                    graph_diary_scores[did]["boost"] += 0.3
                    graph_diary_scores[did]["reasons"].append(reason)
                    if ent_name not in graph_diary_scores[did]["entities"]:
                        graph_diary_scores[did]["entities"].append(ent_name)

        query_vector = llm_service.get_embedding(query)
        vector_matches = vector_store.search_similar(query_vector, limit=limit)

        vector_diary_scores: Dict[int, float] = {}
        for vm in vector_matches:
            did = vm.get("diary_id")
            distance = vm.get("_distance", 1.0)
            score = max(0.0, 1.0 - (distance / 2.0))
            vector_diary_scores[did] = score

        all_diary_ids = set(graph_diary_scores.keys()).union(set(vector_diary_scores.keys()))
        
        if not all_diary_ids:
            text_matches = db.query(Diary).filter(Diary.content.ilike(f"%{query}%")).limit(limit).all()
            for tm in text_matches:
                all_diary_ids.add(tm.id)

        diaries = db.query(Diary).filter(Diary.id.in_(list(all_diary_ids))).all()
        diary_map = {d.id: d for d in diaries}

        result_items: List[SearchResultItem] = []
        color_backfilled = False
        for did in all_diary_ids:
            d = diary_map.get(did)
            if not d:
                continue

            v_score = vector_diary_scores.get(did, 0.0)
            g_info = graph_diary_scores.get(did)

            if g_info and v_score > 0:
                final_score = v_score * g_info["boost"]
                reason = f"混合匹配: 向量相似 + {', '.join(g_info['reasons'])}"
                rel_ents = g_info["entities"]
            elif g_info:
                final_score = 0.8 * g_info["boost"]
                reason = f"{'; '.join(g_info['reasons'])}"
                rel_ents = g_info["entities"]
            elif v_score > 0:
                final_score = v_score
                reason = "语义向量相似"
                rel_ents = [b.entity.name for b in d.entities if b.entity]
            else:
                final_score = 0.5
                reason = "关键词字面匹配"
                rel_ents = [b.entity.name for b in d.entities if b.entity]

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
                score=round(float(final_score), 3),
                matched_reason=reason,
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

memory_engine = MemoryEngine()
