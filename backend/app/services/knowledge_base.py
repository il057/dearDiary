import os
import json
import threading
from typing import Dict, Any, List
from app.config import settings

class KnowledgeBase:
    """
    用户专属认知词典与实体对齐系统：
    1. 保持开源代码干净：不硬编码任何具体名字，配置存放在本地数据目录（默认 .gitignore）；
    2. 实体别名对齐（Entity Resolution）：支持将多个别名/昵称映射归一至核心主实体；
    3. 支持 AI 自动扩充与前端可视化编辑：AI 提取的新标签自动持久化，用户可在前端实时修改；
    4. 线程安全 + mtime 缓存：避免并发读写冲突与高频重复磁盘解析。
    """
    def __init__(self):
        self.knowledge_path = os.path.join(settings.DATA_DIR, "knowledge.json")
        self._lock = threading.RLock()
        self._last_mtime: float = -1.0
        self.aliases: Dict[str, str] = {}
        self.custom_entities: Dict[str, str] = {}
        self.owner_name: str = "我"
        self._load(force=True)

    def _load(self, force: bool = False):
        with self._lock:
            if not os.path.exists(self.knowledge_path):
                if force or self._last_mtime != -1.0:
                    self.aliases = {}
                    self.custom_entities = {}
                    self.owner_name = "我"
                    self._last_mtime = -1.0
                return
            try:
                mtime = os.path.getmtime(self.knowledge_path)
                if not force and mtime == self._last_mtime:
                    return
                with open(self.knowledge_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.aliases = data.get("aliases", {})
                    self.custom_entities = data.get("custom_entities", {})
                    self.owner_name = (data.get("owner_name") or "我").strip() or "我"
                self._last_mtime = mtime
            except Exception as e:
                print(f"[KnowledgeBase load error]: {e}")

    def save(self):
        """持久化到本地数据文件"""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.knowledge_path), exist_ok=True)
                with open(self.knowledge_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "owner_name": self.owner_name,
                        "aliases": self.aliases,
                        "custom_entities": self.custom_entities
                    }, f, ensure_ascii=False, indent=2)
                self._last_mtime = os.path.getmtime(self.knowledge_path)
            except Exception as e:
                print(f"[KnowledgeBase save error]: {e}")

    def get_owner_name(self) -> str:
        with self._lock:
            self._load()
            return self.owner_name or "我"

    def set_owner_name(self, name: str) -> str:
        with self._lock:
            self._load()
            cleaned = (name or "").strip() or "我"
            old = self.owner_name or "我"
            self.owner_name = cleaned
            self.save()
            return old

    def resolve_entity(self, name: str) -> str:
        """
        同义实体对齐：将别名自动映射为规范化主实体
        """
        with self._lock:
            self._load()
            if name in self.aliases:
                return self.aliases[name]
            name_lower = name.lower()
            for k, v in self.aliases.items():
                if k.lower() == name_lower:
                    return v
            return name

    def get_alias_mapping_for_name(self, name: str) -> str:
        """返回别名对应的主实体名"""
        with self._lock:
            self._load()
            if name in self.aliases:
                return self.aliases[name]
            name_lower = name.lower()
            for k, v in self.aliases.items():
                if k.lower() == name_lower:
                    return v
            return None

    def scan_custom_entities(self, text: str) -> List[Dict[str, str]]:
        """
        扫描文本中的自定义实体与别名
        """
        with self._lock:
            self._load()
            found: Dict[str, Dict[str, str]] = {}

            # 扫描别名字典
            text_lower = text.lower()
            for alias, canonical in self.aliases.items():
                if alias in text or alias.lower() in text_lower:
                    found[canonical] = {
                        "name": canonical,
                        "entity_type": self.custom_entities.get(canonical, "person"),
                        "description": f"别名来源: {alias}",
                        "alias_source": alias
                    }

            # 扫描主实体词典
            for ent_name, etype in self.custom_entities.items():
                if ent_name in text:
                    canonical = self.resolve_entity(ent_name)
                    if canonical not in found:
                        found[canonical] = {
                            "name": canonical,
                            "entity_type": etype,
                            "description": ""
                        }

            return list(found.values())

    def auto_register_entities(self, entities: List[Dict[str, Any]]):
        """
        自动学习与沉淀：将 AI 提取出的有效新实体自动写入 knowledge 字典
        """
        with self._lock:
            self._load()
            changed = False
            for item in entities:
                name = str(item.get("name") or "").strip()
                etype = str(item.get("entity_type") or "concept").strip()
                if not name or len(name) > 15:
                    continue

                # 如果不是已知别名且未注册为主实体，则自动收录
                canonical = self.resolve_entity(name)
                if canonical not in self.custom_entities and canonical not in self.aliases:
                    self.custom_entities[canonical] = etype
                    changed = True

            if changed:
                self.save()

    def set_alias(self, alias: str, canonical: str):
        """设置别名映射（例如 将别名绑定到主实体）"""
        with self._lock:
            self._load()
            alias = alias.strip()
            canonical = canonical.strip()
            if not alias or not canonical or alias == canonical:
                return
            self.aliases[alias] = canonical
            if canonical not in self.custom_entities:
                self.custom_entities[canonical] = "person"
            self.save()

    def update_entity_type(self, name: str, entity_type: str):
        """修改实体的分类属性（如 人物/宠物/地点/时间/事物）"""
        with self._lock:
            self._load()
            name = name.strip()
            if not name:
                return
            self.custom_entities[name] = entity_type.strip()
            self.save()

    def remove_alias(self, alias: str):
        """移除别名"""
        with self._lock:
            self._load()
            if alias in self.aliases:
                del self.aliases[alias]
                self.save()

    def remove_entity(self, name: str):
        """移除主实体及其绑定的别名"""
        with self._lock:
            self._load()
            if name in self.custom_entities:
                del self.custom_entities[name]
            # 清理指向它的别名
            to_del = [k for k, v in self.aliases.items() if v == name or k == name]
            for k in to_del:
                del self.aliases[k]
            self.save()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            self._load()
            return {
                "aliases": dict(self.aliases),
                "custom_entities": dict(self.custom_entities)
            }

knowledge_base = KnowledgeBase()
