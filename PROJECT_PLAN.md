# dearDiary 项目结构与环境初始化规划

## 1. 架构与设计原则
- **极简且解耦**：前后端分离，后端专注数据沉淀与图+向量抽取检索，前端聚焦纯黑极简高触感移动 PWA。
- **本地自包含**：向量引擎采用嵌入式 LanceDB（免独立服务），关系型数据采用 SQLite，单机 Windows 运行零运维负担。
- **语义实体联想**：写入日记时通过 LLM 异步/同步抽取实体与关联（例如：人物、别名、关系），建立图边，检索时支持“关键词/语义 -> 实体发散 -> 跨日记深度关联召回”。

---

## 2. 精简目录结构规划

```
d:\Code\dearDiary\
│
├── backend/                      # Python FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口与 CORS/静态文件配置
│   │   ├── config.py             # 读取 .env (LLM Key, BaseURL, 模型配置)
│   │   ├── database.py           # SQLite 初始化与连接管理
│   │   ├── models.py             # SQLAlchemy/SQLModel 数据模型 (Diary, Entity, Relation)
│   │   ├── schemas.py            # Pydantic 输入输出契约
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── vector_store.py   # LanceDB 向量嵌入与检索服务
│   │       ├── memory_engine.py  # 实体抽取、图关联写入与发散搜索
│   │       └── llm_client.py     # OpenAI 兼容协议客户端 (支持云端/Ollama)
│   ├── data/                     # 持久化数据目录 (.gitignore 忽略敏感内容)
│   │   ├── diary.db              # SQLite 数据库文件
│   │   └── lancedb/              # LanceDB 向量索引目录
│   ├── requirements.txt          # Python 核心依赖清单
│   └── .env.example              # 环境变量配置模板
│
├── frontend/                     # Vue 3 + Vite + Tailwind CSS + PWA
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── icon-192.png          # PWA 图标 (iPhone/Android)
│   │   └── icon-512.png
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── HeaderSearch.vue  # 顶部语义联想搜索栏
│   │   │   ├── QuickComposer.vue # 极简随手记录入框
│   │   │   ├── TimelineView.vue  # 时间轴流水列表
│   │   │   └── ClusterView.vue   # 实体/主题聚类卡片视图
│   │   ├── api/
│   │   │   └── diary.js          # 后端 API 请求封装
│   │   ├── App.vue               # 顶层布局与底栏 Tab 切换
│   │   └── main.js
│   ├── vite.config.js            # Vite + PWA 插件配置 (HTTPS/Manifest/Cache)
│   ├── tailwind.config.js        # 纯黑极简暗黑主题配置
│   └── package.json
│
└── scripts/                      # 运维与后台守护脚本
    ├── start_backend.bat         # 启动后端批处理
    ├── start_frontend.bat        # 启动前端/预览服务
    └── run_all.bat               # 一键双端后台拉起
```

