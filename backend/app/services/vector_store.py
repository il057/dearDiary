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

    def search_similar(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        基于向量余弦/L2距离召回语义相似日记
        """
        if len(self.table) == 0:
            return []
        results = self.table.search(query_vector).limit(limit).to_list()
        return results

    def delete_by_diary_id(self, diary_id: int):
        try:
            self.table.delete(f"diary_id = {diary_id}")
        except Exception as e:
            print(f"[Warning] LanceDB delete failed: {e}")

vector_store = VectorStore()

