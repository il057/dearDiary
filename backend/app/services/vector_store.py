from typing import List, Dict, Any
import lancedb
import pyarrow as pa
from app.config import settings

class VectorStore:
    def __init__(self):
        self.db = lancedb.connect(settings.LANCEDB_DIR)
        self.table_name = "diaries_vector"
        self._ensure_table()

    def _ensure_table(self):
        schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), settings.EMBEDDING_DIM)),
            pa.field("diary_id", pa.int64()),
            pa.field("content", pa.string()),
            pa.field("created_at", pa.string()),
        ])
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=schema)
        else:
            self.table = self.db.open_table(self.table_name)

    def add_diary_vector(self, diary_id: int, content: str, vector: List[float], created_at: str):
        data = [{
            "vector": vector,
            "diary_id": diary_id,
            "content": content,
            "created_at": created_at
        }]
        self.table.add(data)

    def add_diary_vectors(self, diary_id: int, chunks: List[Dict[str, Any]], created_at: str):
        """批量写入同一篇日记的多个文本分块向量"""
        data = [
            {
                "vector": c["vector"],
                "diary_id": diary_id,
                "content": c["content"],
                "created_at": created_at
            }
            for c in chunks if c.get("vector")
        ]
        if data:
            self.table.add(data)

    def search_similar(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        基于向量余弦距离召回语义相似日记（自动对多 chunk 结果按 diary_id 去重取最优）
        """
        if not query_vector or len(self.table) == 0:
            return []
        try:
            raw_results = self.table.search(query_vector).metric("cosine").limit(limit * 3).to_list()
        except Exception:
            raw_results = self.table.search(query_vector).limit(limit * 3).to_list()

        deduped: Dict[int, Dict[str, Any]] = {}
        for row in raw_results:
            did = row.get("diary_id")
            if did is None:
                continue
            dist = float(row.get("_distance", 1.0))
            if did not in deduped or dist < float(deduped[did].get("_distance", 1.0)):
                deduped[did] = row

        ordered = sorted(deduped.values(), key=lambda x: float(x.get("_distance", 1.0)))
        return ordered[:limit]

    def delete_by_diary_id(self, diary_id: int):
        try:
            self.table.delete(f"diary_id = {diary_id}")
        except Exception as e:
            print(f"[Warning] LanceDB delete failed: {e}")

vector_store = VectorStore()

