import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "dearDiary"
    
    # Ollama 服务地址 (本地测试默认 localhost:11434，亦可填入远端迷你主机 Tailscale IP，如 http://100.x.y.z:11434)
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # LLM 配置 (适配本地或远端主机 qwen2.5:7b / 3b)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:3b")
    
    # Embedding 向量模型配置 (本地 qwen3-embedding:0.6b, 1024 维)
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "ollama")
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    
    # 路径配置
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    LANCEDB_DIR: str = os.path.join(DATA_DIR, "lancedb")
    SQLITE_PATH: str = os.path.join(DATA_DIR, "diary.db")
    
    # 服务网络配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        extra = "ignore"

settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LANCEDB_DIR, exist_ok=True)
