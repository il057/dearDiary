<div align="center">
  <img src="frontend/public/favicon.svg" width="84" height="84" alt="dearDiary 图标" />
  <h1>dearDiary</h1>
  <p><strong>本地优先的个人语义记忆与关联日记系统</strong></p>
  <p>基于本地向量检索与实体关联图谱，让每一段零散记录都能跨越时间产生共鸣</p>
</div>

---

## ✨ 核心特性

- **本地优先，隐私可控**：所有日记正文、向量索引与个人词典均保存在本地 `backend/data/` 目录，默认已通过 `.gitignore` 排除，绝不上传云端或仓库。
- **语义 + 图谱发散检索**：结合 **LanceDB** 向量相似度检索与实体关系图谱（`MemoryEngine`），即使搜索词与原文用词不同，也能顺着人物、地点与事件关联召回历史记忆。
- **AI 自动提取情绪与实体**：接入本地 **Ollama**（或任意 OpenAI 兼容接口），自动识别日记心境、人物、宠物、地点、核心意象与回忆中的绝对年份，并严格过滤代词与无意义虚词。
- **专属词典与别名对齐（`KnowledgeBase`）**：支持将同一人物/事物的不同昵称、别名自动归并为主实体，可在前端弹窗中实时编辑，也支持通过 `backend/data/knowledge.json` 管理（参考模板 `backend/knowledge.example.json`）。
- **2D 力导向星系聚类视图**：基于 D3 力导向图（`ClusterView`）直观呈现日记与实体之间的星系网络，支持缩放、拖拽与节点跳转。
- **极简暗黑美学 & 移动端 PWA**：采用 Vue 3 + Tailwind CSS + `UnifontJP` 打造纯黑（`#050505`）+ 绯红（`#dc143c`）视觉体验，内置近一周记录打卡、时间轴列表、笔记本视图、数据分析总览、专注写作页、日记引用与侧边日历，支持 iOS / Android 添加至主屏幕作为独立 PWA 使用。

---

## 🛠️ 技术栈

- **后端**：Python、FastAPI、SQLAlchemy、SQLite、LanceDB、Pydantic Settings
- **模型与向量**：本地 Ollama（默认 `qwen3:8b` 负责实体抽取与摘要/情绪提取，`qwen3-embedding:0.6b` 负责 1024 维向量嵌入），亦兼容 OpenAI 格式接口；无模型服务时自动回退至词典扫描与首行摘要兜底
- **前端**：Vue 3、Vite、Tailwind CSS v4、D3（`d3-force`、`d3-zoom`、`d3-drag`、`d3-selection`）、Lucide Icons（`@lucide/vue` / `lucide-vue-next`）、`vite-plugin-pwa`

---

## 📁 目录结构

```text
dearDiary/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口与接口路由
│   │   ├── config.py               # 环境变量与本地路径配置
│   │   ├── database.py             # SQLite 初始化与会话管理
│   │   ├── models.py               # 日记、实体、关系数据模型
│   │   ├── schemas.py              # Pydantic 请求/响应模型
│   │   └── services/
│   │       ├── llm_client.py        # Ollama / OpenAI 兼容 LLM 与 Embedding 客户端
│   │       ├── memory_engine.py     # 实体抽取、图谱写入与发散检索
│   │       ├── vector_store.py      # LanceDB 向量存储与查询
│   │       ├── knowledge_base.py    # 个人词典与别名对齐
│   │       └── analytics_service.py # 日记统计与数据分析总览
│   ├── .env.example                # 环境变量配置模板
│   ├── knowledge.example.json      # 个人词典配置示例
│   └── requirements.txt            # Python 依赖清单
├── frontend/
│   ├── public/                     # Favicon、PWA 图标与字体文件
│   ├── src/
│   │   ├── api/diary.js            # 后端 API 封装
│   │   ├── components/             # 时间轴、笔记本、星系图、写作页、统计、侧边栏等组件
│   │   ├── utils/highlight.js      # 搜索关键词高亮工具
│   │   ├── App.vue                 # 主布局与导航切换
│   │   └── style.css               # 全局暗黑主题样式
│   ├── index.html
│   └── vite.config.js              # Vite 与 PWA Manifest 配置
├── scripts/                        # Windows 一键启动脚本
└── DEPLOYMENT.md                   # 部署、开机自启与 iOS PWA 配置指南
```

---

## 🚀 快速开始

### 环境准备

- **Python 3.10+**
- **Node.js 18+**
- **Ollama**（推荐安装，用于本地私有化语义理解与向量计算）

如使用本地 Ollama，可提前拉取默认模型：

```bash
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b
```

### 1. 启动后端

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

如需修改 `OLLAMA_HOST`、`LLM_MODEL` 或 `EMBEDDING_MODEL`，可按需编辑 `backend/.env`。

启动后端服务：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后可访问 `http://localhost:8000/docs` 查看接口文档。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

在浏览器打开 `http://localhost:5173` 即可使用。

### 3. Windows 一键启动

也可以直接运行 `scripts/` 目录下的启动脚本同时拉起前后端：

- `scripts/run_all.bat`
- `scripts/run_all.ps1`

关于局域网 / Tailscale 远程访问、iPhone Safari 添加主屏幕（PWA）以及 Windows 开机自启配置，请参阅 [DEPLOYMENT.md](DEPLOYMENT.md)。

---

## 🔒 隐私安全说明

以下目录和文件已在 [.gitignore](.gitignore) 中默认忽略，用于保护个人隐私：

- `backend/data/`（SQLite 日记数据库、LanceDB 向量索引、`knowledge.json`）
- `backend/.env`（本地环境变量与密钥配置）
- `*.db`、`*.sqlite3`

推送代码到公开仓库前，请勿移除这些忽略规则或手动提交个人数据文件。

---

## 🙏 致谢与引用

- **界面字体**：内置点阵字体使用 [GNU Unifont](https://unifoundry.com/unifont/)（`unifont_jp.otf`），笔记本视图打字机字体使用 `迫真打字油印體.ttf`。
- **核心开源生态**：感谢 [FastAPI](https://fastapi.tiangolo.com/)、[LanceDB](https://lancedb.com/)、[Ollama](https://ollama.com/)、[Vue 3](https://vuejs.org/)、[Tailwind CSS](https://tailwindcss.com/)、[D3.js](https://d3js.org/) 与 [Lucide](https://lucide.dev/) 等开源项目。

