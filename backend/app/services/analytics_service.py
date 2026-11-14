import datetime
import re
from collections import Counter, defaultdict
from typing import Dict, Any, List
from sqlalchemy.orm import Session, joinedload

from app.models import Diary, Entity, DiaryEntity, EntityRelation, DiaryQuote


_WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _count_words(text: str) -> int:
    """统计有效字数（去除空白符后的字符数，兼顾中文与英文）"""
    if not text:
        return 0
    return len(re.sub(r"\s+", "", text))


def _compute_streaks(active_dates_sorted: List[datetime.date], check_current: bool = False) -> Dict[str, int]:
    """计算最长连续天数；若 check_current=True，同时计算截至今日/昨日的当前连击"""
    if not active_dates_sorted:
        return {"longest": 0, "current": 0}

    longest = 1
    run = 1
    for i in range(1, len(active_dates_sorted)):
        if (active_dates_sorted[i] - active_dates_sorted[i - 1]).days == 1:
            run += 1
            if run > longest:
                longest = run
        else:
            run = 1

    current = 0
    if check_current:
        today = datetime.date.today()
        date_set = set(active_dates_sorted)
        cursor = today if today in date_set else (today - datetime.timedelta(days=1))
        while cursor in date_set:
            current += 1
            cursor -= datetime.timedelta(days=1)

    return {"longest": longest, "current": current}


def get_analytics_overview(db: Session, range_key: str = "all") -> Dict[str, Any]:
    """聚合现有日记、情绪、实体与引用数据，生成 Part A 数据分析总览"""
    now = datetime.datetime.now()
    cutoff = None
    if range_key == "30d":
        cutoff = now - datetime.timedelta(days=30)
    elif range_key == "90d":
        cutoff = now - datetime.timedelta(days=90)
    elif range_key == "365d":
        cutoff = now - datetime.timedelta(days=365)

    # 全局活跃日期用于计算当前连续记录天数
    all_dates_rows = db.query(Diary.created_at).all()
    all_unique_dates = sorted({r[0].date() for r in all_dates_rows if r[0] is not None})
    global_streaks = _compute_streaks(all_unique_dates, check_current=True)

    query = (
        db.query(Diary)
        .options(
            joinedload(Diary.entities).joinedload(DiaryEntity.entity),
            joinedload(Diary.quote_links),
        )
        .order_by(Diary.created_at.asc())
    )
    if cutoff is not None:
        query = query.filter(Diary.created_at >= cutoff)

    diaries: List[Diary] = query.all()

    total_diaries = len(diaries)
    total_words = 0
    max_words = 0
    quoted_source_count = 0
    total_quotes = 0

    daily_map: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "words": 0})
    hourly_counts = [0] * 24
    hourly_words = [0] * 24
    weekday_counts = [0] * 7
    weekday_words = [0] * 7

    mood_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "words": 0, "colors": Counter()}
    )
    mood_timeline: List[Dict[str, Any]] = []

    entity_counter: Dict[str, Dict[str, int]] = defaultdict(Counter)
    diary_ids_in_range = set()

    for d in diaries:
        diary_ids_in_range.add(d.id)
        words = _count_words(d.content)
        total_words += words
        if words > max_words:
            max_words = words

        if d.created_at:
            date_str = d.created_at.strftime("%Y-%m-%d")
            daily_map[date_str]["count"] += 1
            daily_map[date_str]["words"] += words

            h = d.created_at.hour
            # 排除导入日记默认的 12:00:00 时间戳，避免干扰真实写作时段统计
            if not (h == 12 and d.created_at.minute == 0 and d.created_at.second == 0):
                hourly_counts[h] += 1
                hourly_words[h] += words

            wd = d.created_at.weekday()
            weekday_counts[wd] += 1
            weekday_words[wd] += words

        if d.quote_links:
            quoted_source_count += 1
            total_quotes += len(d.quote_links)

        mood_label = (d.mood or "").strip()
        color = d.mood_color or "#dc143c"
        if mood_label:
            mood_stats[mood_label]["count"] += 1
            mood_stats[mood_label]["words"] += words
            mood_stats[mood_label]["colors"][color] += 1

        mood_timeline.append({
            "id": d.id,
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "",
            "mood": mood_label or "未标注",
            "color": color,
            "summary": (d.summary or d.content[:40].replace("\n", " ")) if d.content else "",
        })

        for de in d.entities:
            if de.entity:
                etype = de.entity.entity_type or "concept"
                entity_counter[etype][de.entity.name] += 1

    range_unique_dates = sorted(
        datetime.date.fromisoformat(k) for k in daily_map.keys()
    )
    range_streaks = _compute_streaks(range_unique_dates, check_current=False)

    heatmap = [
        {"date": date_str, "count": vals["count"], "words": vals["words"]}
        for date_str, vals in sorted(daily_map.items())
    ]

    hourly_distribution = [
        {"hour": h, "count": hourly_counts[h], "words": hourly_words[h]}
        for h in range(24)
    ]

    weekday_distribution = [
        {
            "weekday": wd,
            "label": _WEEKDAY_LABELS[wd],
            "count": weekday_counts[wd],
            "words": weekday_words[wd],
        }
        for wd in range(7)
    ]

    mood_distribution = []
    for mood_label, info in sorted(mood_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:12]:
        top_color = info["colors"].most_common(1)[0][0] if info["colors"] else "#dc143c"
        mood_distribution.append({
            "mood": mood_label,
            "count": info["count"],
            "avg_words": round(info["words"] / info["count"]) if info["count"] else 0,
            "color": top_color,
        })

    # 实体按类型分组排行
    entity_groups: Dict[str, List[Dict[str, Any]]] = {}
    for etype, counter in entity_counter.items():
        entity_groups[etype] = [
            {"name": name, "entity_type": etype, "count": cnt}
            for name, cnt in counter.most_common(10)
        ]

    # 高频实体关系（若在时间范围内，优先统计该范围内日记提取的关系 + 手动关系）
    rel_query = db.query(EntityRelation)
    if cutoff is not None and diary_ids_in_range:
        rel_query = rel_query.filter(
            (EntityRelation.diary_id.in_(diary_ids_in_range)) | (EntityRelation.diary_id.is_(None))
        )
    relations = rel_query.order_by(EntityRelation.weight.desc()).limit(30).all()
    rel_agg: Dict[tuple, float] = defaultdict(float)
    for r in relations:
        rel_agg[(r.source_name, r.relation, r.target_name)] += (r.weight or 1.0)
    top_relations = [
        {
            "source_name": k[0],
            "relation": k[1],
            "target_name": k[2],
            "weight": round(v, 2),
        }
        for k, v in sorted(rel_agg.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # 被引用最多的核心记忆
    quote_counts = Counter()
    all_quotes = db.query(DiaryQuote).all()
    for q in all_quotes:
        if cutoff is None or q.diary_id in diary_ids_in_range:
            quote_counts[q.quoted_diary_id] += 1

    top_quoted_diaries = []
    if quote_counts:
        top_ids = [did for did, _ in quote_counts.most_common(5)]
        quoted_objs = {
            d.id: d for d in db.query(Diary).filter(Diary.id.in_(top_ids)).all()
        }
        for did in top_ids:
            d = quoted_objs.get(did)
            if d:
                top_quoted_diaries.append({
                    "id": d.id,
                    "created_at": d.created_at.strftime("%Y-%m-%d") if d.created_at else "",
                    "summary": d.summary or (d.content[:50].replace("\n", " ") if d.content else ""),
                    "mood": d.mood,
                    "mood_color": d.mood_color or "#dc143c",
                    "quote_count": quote_counts[did],
                })

    return {
        "range": range_key,
        "overview": {
            "total_diaries": total_diaries,
            "total_words": total_words,
            "active_days": len(daily_map),
            "avg_words": round(total_words / total_diaries) if total_diaries else 0,
            "max_words": max_words,
            "current_streak": global_streaks["current"],
            "longest_streak": range_streaks["longest"],
            "quote_rate": round((quoted_source_count / total_diaries) * 100, 1) if total_diaries else 0.0,
            "total_quotes": total_quotes,
        },
        "heatmap": heatmap,
        "hourly_distribution": hourly_distribution,
        "weekday_distribution": weekday_distribution,
        "mood_distribution": mood_distribution,
        "mood_timeline": mood_timeline[-150:],
        "entity_groups": entity_groups,
        "top_relations": top_relations,
        "top_quoted_diaries": top_quoted_diaries,
    }

