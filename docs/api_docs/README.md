# RAGFlow API 文档目录

> 本目录包含RAGFlow的API接口文档

## 文档索引

| 文档 | 说明 | 更新日期 |
|------|------|----------|
| [HTTP API接口文档](./2026-02-25-HTTP-API接口文档.md) | RESTful API完整参考 | 2026-02-25 |

---

## 快速开始

### 认证

所有API请求需要携带API Key：

```http
Authorization: Bearer <YOUR_API_KEY>
```

### 基础URL

```
http://{host}:{port}/api/v1
```

### 核心API模块

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| **数据集** | `/datasets` | 知识库管理 |
| **文档** | `/datasets/{id}/documents` | 文档上传和管理 |
| **分块** | `/datasets/{id}/documents/{id}/chunks` | 分块管理和检索 |
| **Chat** | `/chats` | Chat助手管理 |
| **会话** | `/chats/{id}/sessions` | 对话会话管理 |
| **Agent** | `/agents` | Agent工作流 |
| **文件** | `/file` | 文件管理系统 |
| **记忆** | `/memories` | 记忆系统 |

---

## 常用示例

### 创建数据集并上传文档

```bash
# 1. 创建数据集
curl -X POST 'http://localhost/api/v1/datasets' \
  -H 'Authorization: Bearer <API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "我的知识库"}'

# 2. 上传文档
curl -X POST 'http://localhost/api/v1/datasets/{dataset_id}/documents' \
  -H 'Authorization: Bearer <API_KEY>' \
  -F 'file=@document.pdf'

# 3. 解析文档
curl -X POST 'http://localhost/api/v1/datasets/{dataset_id}/documents/{doc_id}/run' \
  -H 'Authorization: Bearer <API_KEY>'
```

### 创建Chat助手并对话

```bash
# 1. 创建Chat助手
curl -X POST 'http://localhost/api/v1/chats' \
  -H 'Authorization: Bearer <API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "产品助手",
    "dataset_ids": ["dataset_id"]
  }'

# 2. 对话
curl -X POST 'http://localhost/api/v1/chats/{chat_id}/completions' \
  -H 'Authorization: Bearer <API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "什么是RAGFlow？",
    "stream": true
  }'
```

### 使用OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="<YOUR_API_KEY>",
    base_url="http://localhost/api/v1/chats_openai/{chat_id}"
)

response = client.chat.completions.create(
    model="model",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

---

## 相关资源

- [官方API文档](https://ragflow.io/docs/http_api_reference)
- [Python SDK](https://github.com/infiniflow/ragflow/tree/main/sdk/python)
- [系统架构文档](../architecture/)
