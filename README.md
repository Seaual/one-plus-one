# 1+1>2

GitHub 项目灵感合成系统——给定一个想法或仓库 URL，从已有的流行项目中检索匹配项，组合成可行的项目方向。

> 1+1>2：两个已有项目结合，产出意想不到的新可能。

## 特性

- **语义检索**：用自然语言描述想法，系统自动找出最相关的 GitHub 项目
- **渐进式交互**：先给候选方向 → 选中后展开为完整提案
- **本地 Embedding**：使用 BAAI/bge-m3 模型，无需外部 API Key
- **双入口**：CLI 用于后台数据操作，MCP Server 集成 Claude Code 对话流
- **Hermes 架构**：主控 Agent 编排，技能工具各司其职

## 快速开始

### 安装

```bash
git clone https://github.com/<your-username>/one-plus-one.git
cd one-plus-one
pip install -e .
```

### 数据收集

```bash
# 抓取 GitHub Trending
oneplusone crawl-trending --since daily

# 按主题搜索
oneplusone crawl_topic "ai" "machine-learning" "web-framework" --limit 50

# 抓取单个仓库
oneplusone crawl_repo "https://github.com/owner/repo"

# 向量化索引
oneplusone index --all
```

### 语义搜索

```bash
oneplusone search "AI code review tool" --top 10
oneplusone search "machine learning" --language python --min-stars 1000
```

### 数据库统计

```bash
oneplusone stats
oneplusone db_info
```

## 集成 Claude Code (MCP)

在 `~/.claude/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "one-plus-one": {
      "command": "python",
      "args": ["-m", "one_plus_one.mcp_server"],
      "cwd": "/path/to/one-plus-one",
      "env": {
        "ONEPLUSONE_DB": "/path/to/one-plus-one/data/projects.db"
      }
    }
  }
}
```

重启 Claude Code 后即可使用 `search_projects`、`project_detail`、`db_status` 三个工具。

## 架构

```
Claude Code (Orchestrator Agent)
  ├── search_projects  (MCP Tool)
  ├── project_detail   (MCP Tool)
  └── db_status        (MCP Tool)
        │
        ▼
┌───────────────────────────┐
│       CLI / MCP           │  ← 使用层
├───────────────────────────┤
│  Crawler → Indexer →      │  ← 核心逻辑
│  Retriever                │
├───────────────────────────┤
│  SQLite + sqlite-vec      │  ← 数据层
└───────────────────────────┘
```

## 技术栈

| 组件 | 技术 |
|---|---|
| 语言 | Python 3.12+ |
| Embedding | BAAI/bge-m3 (sentence-transformers) |
| 向量检索 | sqlite-vec |
| 关系存储 | SQLite |
| CLI | typer |
| MCP | mcp (FastMCP) |
| 爬虫 | httpx + lxml |

## 环境变量

| 变量 | 说明 |
|---|---|
| `ONEPLUSONE_DB` | 数据库路径（默认 `data/projects.db`） |
| `GITHUB_TOKEN` | GitHub API Token（可选，提高速率限制） |

## 开发

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## 路线图

- [x] P0: CLI 数据层（crawler + indexer + retriever）
- [x] P1: MCP Server
- [ ] P2: 定时爬虫 Agent
- [ ] P3: 质量评分模型
- [ ] P4: 多数据源扩展（HackerNews, ProductHunt）
