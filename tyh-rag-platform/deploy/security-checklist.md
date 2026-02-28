# 安全检查矩阵 (T-063)
# 3角色 × 核心API 权限验证

## RBAC权限矩阵

| API路径 | user | kb_admin | it_admin | 说明 |
|---------|------|----------|----------|------|
| POST /auth/login | ✅ | ✅ | ✅ | 公开 |
| GET /auth/me | ✅ | ✅ | ✅ | 登录用户 |
| GET /users | ❌ | ❌ | ✅ | 仅IT管理员 |
| POST /users | ❌ | ❌ | ✅ | 仅IT管理员 |
| PUT /users/:id | ❌ | ❌ | ✅ | 仅IT管理员 |
| GET /chat/sessions | ✅ | ✅ | ✅ | 登录用户(本人) |
| POST /chat/sessions | ✅ | ✅ | ✅ | 登录用户 |
| POST /chat/sessions/:id/messages | ✅ | ✅ | ✅ | 登录用户 |
| POST /documents | ❌ | ✅ | ✅ | KB管理员+ |
| GET /documents | ✅ | ✅ | ✅ | 团队隔离 |
| PUT /documents/:id | ❌ | ✅ | ✅ | KB管理员+ |
| DELETE /documents/:id | ❌ | ✅ | ✅ | KB管理员+ |
| POST /qa-pairs | ❌ | ✅ | ✅ | KB管理员+ |
| GET /qa-pairs | ✅ | ✅ | ✅ | 团队隔离 |
| PUT /qa-pairs/:id | ❌ | ✅ | ✅ | KB管理员+ |
| DELETE /qa-pairs/:id | ❌ | ✅ | ✅ | KB管理员+ |
| POST /feedbacks | ✅ | ✅ | ✅ | 登录用户 |
| GET /tickets | ❌ | ✅ | ✅ | KB管理员+ |
| PUT /tickets/:id/assign | ❌ | ✅ | ✅ | KB管理员+ |
| GET /favorites | ✅ | ✅ | ✅ | 登录用户(本人) |
| GET /notifications | ✅ | ✅ | ✅ | 登录用户(本人) |
| GET /stats/* | ❌ | ✅ | ✅ | KB管理员+ |
| GET /settings/chat-config | ❌ | ✅(只读) | ✅(读写) | 角色差异 |
| PUT /settings/chat-config | ❌ | ❌ | ✅ | 仅IT管理员 |
| GET /announcements/active | ✅ | ✅ | ✅ | 登录用户 |
| POST /announcements | ❌ | ✅ | ✅ | KB管理员+ |

## 团队数据隔离验证

- [ ] 用户A(团队1)不能看到团队2的文档
- [ ] 用户A(团队1)不能看到团队2的Q&A
- [ ] 会话消息仅本人可见
- [ ] 收藏仅本人可见

## 敏感过滤验证

- [ ] 竞品关键词回答被拦截替换
- [ ] 虚假政策正则匹配被拦截
- [ ] 过滤后安全提示返回正确

## JWT安全验证

- [ ] 无token返回401
- [ ] 过期token返回401
- [ ] 篡改token返回401
- [ ] 角色不足返回403
