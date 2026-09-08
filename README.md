# Enterprise Knowledge Retrieval Assistant

这是一个以企业知识库为核心的 AI 对话系统，支持：

- Vue 3 + Vite + Element Plus 前端交互
- FastAPI + LangGraph + LangChain 后端编排
- 飞书知识库目录树递归抓取与检索
- 向量数据库 Milvus 存储与相似度召回
- 多模型分层：路由模型、召回增强、生成回答
- 对相似问题进行缓存，降低重复检索成本

## 目录结构

- backend: Python FastAPI 服务
- frontend: Vue 3 前端应用
- .env: 环境变量配置

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### 5. 访问地址

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000/docs

## 关键设计

### 架构原则

1. 先做知识树抓取与标准化分块，再做向量索引。
2. 在问答时先路由，再召回，再生成，避免无目标的大模型调用。
3. 对高频重复问题做 TTL 缓存，减少 Milvus + LLM 的重复成本。
4. 把 Feishu、Milvus、LLM 等关键配置都集中在 .env 中。

### 优化策略

- 多模型分层：小模型做路由与意图判断；大模型负责答案生成。
- 文档拆分：按标题、段落、章节与 token 预算切分。
- 向量缓存：仅对新增文档做增量索引，避免全量重建。
- 相同问题缓存：同一提示词命中缓存后直接返回回答。
- 过滤高噪声内容：过滤无关目录、空文档、重复页面。

## 配置说明

所有关键配置都在 .env 中，示例见 .env.example。包含：

- 飞书知识库目录与令牌
- 大模型 API 和模型名
- Milvus 向量库参数
- 检索和缓存阈值

## 维护建议

- 把飞书目录结构纳入增量同步入口，避免每次全量重建索引。
- 对文档源和分块记录唯一 ID，便于修正与重建
- 根据真实访问量调整缓存 TTL 与返回文档数量
- 监控 LLM 调用成本和召回命中率
