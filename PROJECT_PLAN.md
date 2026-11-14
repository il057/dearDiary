# dearDiary 项目结构与架构说明

## 1. 架构与设计原则
- **极简且解耦**：前后端分离，后端专注数据沉淀与图+向量抽取检索，前端聚焦纯黑极简高触感移动 PWA。
- **本地自包含**：向量引擎采用嵌入式 LanceDB（免独立服务），关系型数据采用 SQLite，个人词典保存为本地 JSON，单机 Windows 运行零运维负担。
- **语义实体联想**：写入日记时通过后台任务队列异步调用 LLM 抽取实体、关系、摘要与情绪，建立图边与向量分块索引，检索时支持“关键词/语义 -> 实体发散 -> 跨日记深度关联召回”。

---

## 2. 实际目录结构

```
d:\Code\dearDiary\
│
├── backend/                      # Python FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口、路由与后台任务队列配置
│   │   ├── config.py             # 读取 .env (Ollama/OpenAI、向量维度、本地路径等)
│   │   ├── database.py           # SQLite 初始化、迁移与连接管理
│   │   ├── models.py             # SQLAlchemy 数据模型 (Diary, Entity, EntityRelation, DiaryEntity, DiaryQuote)
│   │   ├── schemas.py            # Pydantic 输入输出契约
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── vector_store.py   # LanceDB 向量嵌入与检索服务
│   │       ├── memory_engine.py  # 实体抽取、图关联写入与发散搜索
│   │       ├── llm_client.py     # Ollama / OpenAI 兼容协议客户端
│   │       ├── knowledge_base.py # 个人词典、称谓与别名对齐服务
│   │       └── analytics_service.py # 日记数据统计与分析总览
│   ├── data/                     # 持久化数据目录 (.gitignore 忽略敏感内容)
│   │   ├── diary.db              # SQLite 数据库文件
│   │   ├── knowledge.json        # 个人词典与别名配置
│   │   └── lancedb/              # LanceDB 向量索引目录
│   ├── requirements.txt          # Python 核心依赖清单
│   ├── knowledge.example.json    # 个人词典配置示例
│   └── .env.example              # 环境变量配置模板
│
├── frontend/                     # Vue 3 + Vite + Tailwind CSS v4 + PWA
│   ├── public/
│   │   ├── apple-touch-icon.png  # iOS 主屏幕图标
│   │   ├── favicon.ico
│   │   ├── favicon.svg
│   │   ├── icon-192.png          # PWA 图标 (iPhone/Android)
│   │   ├── icon-512.png
│   │   └── fonts/                # 内置点阵字体与打字机字体
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalyticsView.vue     # 数据分析总览视图
│   │   │   ├── ClusterView.vue       # 2D 力导向星系聚类视图
│   │   │   ├── DiaryComposerView.vue # 专注日记写作/编辑页
│   │   │   ├── DiaryDetailView.vue   # 日记详情与关联记忆页
│   │   │   ├── HeaderSearch.vue      # 顶部语义联想搜索栏
│   │   │   ├── KnowledgeModal.vue    # 个人词典与实体关系管理弹窗
│   │   │   ├── NotebookView.vue      # 笔记本/手账翻页视图
│   │   │   ├── SideMenu.vue          # 侧边导航、日历与导入导出菜单
│   │   │   ├── TimelineView.vue      # 时间轴流水列表
│   │   │   └── WeeklyTracker.vue     # 近一周记录打卡条
│   │   ├── api/
│   │   │   └── diary.js          # 后端 API 请求封装
│   │   ├── utils/
│   │   │   └── highlight.js      # 搜索关键词高亮工具
│   │   ├── App.vue               # 顶层布局与视图切换
│   │   ├── main.js
│   │   └── style.css             # 全局暗黑主题与 Tailwind CSS v4 入口
│   ├── vite.config.js            # Vite + Tailwind v4 + PWA 插件配置
│   └── package.json
│
└── scripts/                      # 运维与启动脚本
    ├── start_backend.bat         # 启动后端批处理
    ├── start_frontend.bat        # 启动前端开发服务
    ├── run_all.bat               # 一键双端拉起 (CMD)
    └── run_all.ps1               # 一键双端拉起 (PowerShell)
```

