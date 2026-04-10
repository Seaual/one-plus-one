# 1+1>2 项目设计文档

> 一个 GitHub 项目灵感合成系统——给定一个想法或仓库，从已有的流行项目中检索匹配项，组合成可行的项目方向。

**日期**: 2026-04-10
**状态**: Draft

---

## 1. 系统概述

**核心流程**：用户输入一句话想法（或一个 GitHub 仓库 URL） → 系统从数据库中检索语义相关的流行项目 → 返回渐进式方向提案（先给候选 → 选中后展开为完整提案）。

**设计原则**：
- Hermes 风格：主控 Agent 编排，技能工具各司其职
- 本地优先：embedding 本地运行，数据存 SQLite 单文件
- 渐进式交互：通过 Claude Code 对话逐步收敛方案

**技术栈**：
- 语言：Python 3.12+
- Embedding：BAAI/bge-m3（本地，FlagEmbedding 库）
- 向量检索：sqlite-vec
- 关系存储：SQLite
- LLM：Claude API（sonnet-4-6），通过 Claude Code 对话使用
- MCP：用于暴露工具给 Claude Code
- CLI：数据层操作

---

## 2. 架构设计

```
┌─────────────────────────────────────────────────┐
│            Claude Code (你的对话)                │
│          Orchestrator Agent (主控)               │
│  理解意图 → 编排工具 → 渐进式交互 → 生成提案     │
└────────────┬──────┬──────┬──────┬───────────────┘
             │      │      │      │
      ┌──────▼┐  ┌─▼────┐ │  ┌───▼────┐
      │crawl  │  │index │ │  │retrieve│  ← MCP/CLI 技能层
      │skill  │  │skill │ │  │skill   │
      └───┬───┘  └──┬───┘ │  └───┬────┘
          │         │      │      │
          └─────────▼──────┴──────┘
                    │
         ┌──────────▼──────────┐
         │   SQLite + sqlite-vec│  ← 数据层
         │   projects + vectors │
         └─────────────────────┘
```

---

## 3. 组件分解

### 3.1 Crawler（爬虫技能）

**职责**：从 GitHub 获取项目数据（README + 元数据）

**两个入口**：
1. `crawl_trending(since="daily"|"weekly"|"monthly")` — 解析 GitHub trending 页面，返回 25-75 个项目
2. `crawl_by_topic(topics: list[str], limit=50)` — 按预设 topic 搜索，取 top N

**单项目解析** `parse_repo(url)`：
- 仓库基本信息（name, owner, description, stars, language, topics）
- README 原始内容
- 去重：通过 `owner/name` 唯一键判断

**实现细节**：
- 网络层：`httpx` 异步请求
- Trending 页面解析：`lxml` 或 `httpx` + regex（trending 无公开 API）
- API 调用：`/repos/{owner}/{repo}` 获取元数据，`/repos/{owner}/{repo}/readme` 获取 README
- 频率控制：遵守 GitHub API 速率限制，无 token 时 60 次/小时，有 token 时 5000 次/小时

### 3.2 Indexer（索引技能）

**职责**：向量化 + 入库

**流程**：
1. 接收 raw project dict
2. 调用 `bge-m3` 生成 1024 维 embedding（输入是 README 前 4000 字符 + description + topics 拼接）
3. 插入 SQLite `projects` 表（去重更新）
4. 插入 sqlite-vec `project_vectors` 表（关联 project_id）

**增量更新**：如果项目已存在且 stars 未变化 > 10%，跳过重新索引

**性能**：单条项目索引约 100-200ms（bge-m3 本地推理），批量 50 条/批

### 3.3 Retriever（检索技能）

**职责**：语义搜索相关项目

**流程**：
1. 用户查询（想法描述） → bge-m3 生成 query embedding
2. sqlite-vec 向量相似度搜索（cosine distance），top-k
3. 返回项目卡片列表：`{name, description, stars, url, language, topics, readme_excerpt(前500字)}`

**可选过滤**：`by_language`, `by_min_stars`, `exclude_owned`

### 3.4 Orchestrator（主控 Agent）

> **注意**：Orchestrator 不是一个独立的代码模块——它就是 **Claude Code 对话本身**（通过 CLAUDE.md 和 MCP tools.json 定义行为）。

**职责**：在 Claude Code 对话中编排工具调用

**实现方式**：
- 通过 `.claude/CLAUDE.md` 定义系统角色和行为规则
- 通过 `.claude/mcp.json` 注册 MCP 工具
- Claude Code 根据工具描述自主决定何时调用哪个工具

**交互流程**（两阶段）：

**阶段 1 — 方向探索**：
1. 用户输入想法："我想做一个 AI 记账助手"
2. 调用 `retrieve(idea, k=20)` 获取 top-20 相关项目
3. 基于项目列表，在对话中生成 3-5 个方向卡片，每个一句话概括 + 参考了哪些项目
4. 用户选择感兴趣的方向

**阶段 2 — 方案深化**：
1. 对选中方向，调用 `retrieve(细化描述, k=10)` 做针对性检索
2. 生成完整提案：项目名、一句话定位、核心功能列表、参考项目及贡献点、建议技术栈
3. 可迭代：用户说"换一个"或"再深入"，回到步骤 1

**主控的 Prompt 设计**：
- 系统 prompt 定义角色："你是一个项目灵感合成师"
- 工具描述清晰定义每个技能的用途和参数
- 输出格式：方向卡片统一用 markdown 表格/列表呈现

---

## 4. 数据设计

### 4.1 projects 表

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL UNIQUE,  -- "owner/repo"
    description TEXT,
    url TEXT NOT NULL,
    stars INTEGER DEFAULT 0,
    language TEXT,
    topics TEXT,  -- JSON array
    readme TEXT,
    crawled_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    quality_score REAL  -- 综合评分，用于排序
);
CREATE INDEX idx_projects_stars ON projects(stars DESC);
CREATE INDEX idx_projects_language ON projects(language);
```

### 4.2 project_vectors 表（sqlite-vec）

```sql
CREATE VIRTUAL TABLE project_vectors USING vec0(
    project_id INTEGER PRIMARY KEY,
    embedding FLOAT[1024]
);
```

### 4.3 crawl_jobs 表（记录抓取任务）

```sql
CREATE TABLE crawl_jobs (
    id INTEGER PRIMARY KEY,
    job_type TEXT NOT NULL,  -- "trending" | "topic" | "manual"
    params TEXT,  -- JSON: {since, topics, url, ...}
    status TEXT DEFAULT 'pending',  -- pending | running | done | failed
    projects_count INTEGER DEFAULT 0,
    started_at TEXT,
    finished_at TEXT
);
```

---

## 5. CLI 接口

```bash
# 数据层
1plus1 crawl trending --since=daily|weekly|monthly
1plus1 crawl topic "ai" "machine-learning" "web-framework" --limit=50
1plus1 crawl repo "https://github.com/owner/repo"

1plus1 index --all              # 索引所有未索引的项目
1plus1 index --since=2026-04-09 # 只索引某日期之后的

# 查询
1plus1 search "AI code review tool" --top=10 --language=python
1plus1 stats                       # 数据库统计（项目数、语言分布、趋势）
1plus1 db info                     # 数据库路径、版本、最后更新时间
```

## 6. MCP 工具接口

MCP Server 暴露以下工具给 Claude Code：

| 工具名 | 参数 | 返回 |
|---|---|---|
| `search_projects` | `query`(str), `k`(int), `language?`(str), `min_stars?`(int) | 匹配的项目卡片列表 |
| `project_detail` | `full_name`(str) | 单个项目的完整信息 |
| `db_status` | — | 数据库统计摘要 |

---

## 7. 错误处理

| 错误类型 | 处理策略 |
|---|---|
| GitHub API 速率限制 | 指数退避重试，记录到日志 |
| bge-m3 推理失败 | 降级为 description + topics 的短文本 embedding |
| 网络超时 | 单请求 30s 超时，重试 2 次 |
| 向量检索无结果 | 回退到 keyword 匹配（SQLite FTS5） |
| 数据库损坏 | 启动时做 integrity_check，失败提示修复 |

---

## 8. 目录结构

```
one_plus_one/
├── pyproject.toml
├── src/
│   └── one_plus_one/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py          # CLI 入口（click/typer）
│       ├── crawler/
│       │   ├── __init__.py
│       │   ├── github.py        # GitHub API 封装
│       │   ├── trending.py      # Trending 页面解析
│       │   └── models.py        # Project 数据模型
│       ├── indexer/
│       │   ├── __init__.py
│       │   ├── embedder.py      # bge-m3 embedding 封装
│       │   └── store.py         # SQLite + sqlite-vec 操作
│       ├── retriever/
│       │   ├── __init__.py
│       │   └── search.py        # 向量检索 + 过滤
│       └── mcp/
│           ├── __init__.py
│           └── server.py        # MCP server 实现
├── data/
│   └── .gitignore               # 不提交数据文件
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-10-one-plus-one-design.md
└── tests/
    ├── test_crawler.py
    ├── test_indexer.py
    └── test_retriever.py
```

---

## 9. 测试策略

| 层级 | 测试内容 | 方法 |
|---|---|---|
| Crawler | trending 解析、API 响应解析 | Mock HTTP 响应 |
| Indexer | embedding 生成、SQL 插入/去重 | 内存 SQLite |
| Retriever | 向量搜索准确性、过滤条件 | 已知数据集 |
| MCP | 工具接口协议、错误返回 | MCP SDK 测试工具 |

---

## 10. 演进路线

| 阶段 | 内容 | 复杂度 |
|---|---|---|
| **P0** | CLI 数据层（crawler + indexer + retriever）+ SQLite | 核心可用 |
| **P1** | MCP Server（暴露工具给 Claude Code） | 对话集成 |
| **P2** | Crawler Agent（定时任务 + 自动发现） | 自动化数据流 |
| **P3** | 质量评分模型（基于 stars 增速、贡献者活跃度） | 数据质量提升 |
| **P4** | 知识库扩展（非 GitHub 来源：HackerNews、ProductHunt） | 数据源扩展 |

**当前专注 P0**，结构预留 P1 接口。
