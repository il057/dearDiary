# dearDiary 部署与运行全指南

## 1. 快速启动（开发/日常运行）

在 Windows 迷你主机上双击运行或在命令行执行：
```powershell
d:\Code\dearDiary\scripts\run_all.bat
```
它将同时弹出并维护两个控制台窗口：
- **后端服务**：运行在 `http://0.0.0.0:8000`（API 调试文档可查看 `http://localhost:8000/docs`）
- **前端服务**：运行在 `http://0.0.0.0:5173`

---

## 2. 外部访问与 iOS PWA（Safari）配置

### 2.1 获取内网或 Tailscale IP
在 Windows 主机打开终端运行：
```powershell
ipconfig
# 或查看 Tailscale 分配的 100.x.y.z IP
tailscale ip -4
```

### 2.2 iPhone Safari 安装为独立 App (PWA)
1. 确保手机与迷你主机处于同一 Wi-Fi 或均已连接同一 Tailscale 网络。
2. 在 iPhone Safari 打开：`http://<您的IP>:5173`。
3. 点击底部 Safari 分享按钮（带箭头的方框） -> 选择 **“添加到主屏幕” (Add to Home Screen)**。
4. 主屏幕即会生成黑色纯粹的 dearDiary 独立 App 图标，点击直接进入全屏无边框 App 模式。

> **提示（HTTPS 与 PWA Service Worker 说明）**：
> 现代移动端对标准 Service Worker 缓存和离线特性通常需要 HTTPS 或 `localhost`。如果后续配合 Tailscale，可以使用 Tailscale 官方一键 HTTPS 功能：
> ```powershell
> tailscale serve https / http://127.0.0.1:5173
> ```
> 即可直接获得一个合法的公信 HTTPS 域名（例如 `https://minipc.ts.net`），完美激活 iOS PWA 的所有离线增强特性。

---

## 3. Windows 开机自启与后台无感运行方案

为了让迷你主机开机后无需人工登录双击批处理，推荐两种方案：

### 方案 A：使用 NSSM 将服务注册为 Windows 系统后台服务（推荐）
1. 下载开源轻量级服务管理工具 [NSSM (Non-Sucking Service Manager)](https://nssm.cc/download)。
2. 将 `nssm.exe` 放置于系统 PATH 或 `d:\Code\dearDiary\scripts\`。
3. 以管理员身份运行终端，执行以下命令安装后端服务：
```powershell
# 1. 注册后端服务
nssm install dearDiary-Backend "d:\Code\dearDiary\backend\venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set dearDiary-Backend AppDirectory "d:\Code\dearDiary\backend"
nssm start dearDiary-Backend
```

4. 对于前端，建议使用 Nginx / Caddy 托管 `frontend/dist` 并将 `/api` 反向代理至 `http://127.0.0.1:8000`，或直接使用 Vite Preview 作为前端服务：
```powershell
cd d:\Code\dearDiary\frontend
npm run build
# 启动生产构建预览（自动继承 vite.config.js 中的 /api 代理）
npm run preview -- --host 0.0.0.0 --port 5173
```

### 方案 B：Windows 计划任务（Task Scheduler）或开机启动文件夹
按 `Win + R` 输入 `shell:startup`，将 `d:\Code\dearDiary\scripts\run_all.bat`（或 `run_all.ps1`）的快捷方式放入该文件夹，主机开机登录后会自动自启。

---

## 4. 大模型与向量模型配置 (Ollama / OpenAI 兼容接口)

参考 `d:\Code\dearDiary\backend\.env.example` 创建或编辑 `d:\Code\dearDiary\backend\.env` 文件：
```ini
# 默认配置：本地 Ollama 服务 (免 API Key)
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3:8b
OLLAMA_KEEP_ALIVE=5m

# 向量嵌入配置：本地 Qwen3-Embedding-0.6B (1024 维)
EMBEDDING_API_KEY=ollama
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_MODEL=qwen3-embedding:0.6b
EMBEDDING_DIM=1024

# 若 Ollama 部署在局域网或 Tailscale 远端主机，可取消注释并填写对应地址：
# OLLAMA_HOST=http://100.x.y.z:11434

# 若改用云端 OpenAI 兼容大模型（如 DeepSeek、OpenAI 等）：
# LLM_API_KEY=sk-xxxx
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat
# EMBEDDING_API_KEY=sk-xxxx
# EMBEDDING_BASE_URL=https://api.openai.com/v1
# EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_DIM=1536
```
> 当模型服务未启动或不可用时，日记的写入、浏览与导出仍可正常使用（实体提取会回退至 `knowledge.json` 自定义词典扫描，摘要回退为首行文本），但语义向量检索与 AI 实体关系抽取需要可用的模型服务支持。

