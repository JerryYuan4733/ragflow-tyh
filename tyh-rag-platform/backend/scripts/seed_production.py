"""
初始知识库数据灌入脚本 (T-064)
创建5区域团队 + 管理员账号 + 基础Q&A
运行: python scripts/seed_production.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

import bcrypt


# ========== 团队 ==========
TEAMS = [
    {"id": "team-east", "name": "华东区", "code": "EAST", "region": "华东"},
    {"id": "team-south", "name": "华南区", "code": "SOUTH", "region": "华南"},
    {"id": "team-north", "name": "华北区", "code": "NORTH", "region": "华北"},
    {"id": "team-west", "name": "华西区", "code": "WEST", "region": "华西"},
    {"id": "team-central", "name": "华中区", "code": "CENTRAL", "region": "华中"},
    {"id": "team-hq", "name": "总部", "code": "HQ", "region": "总部"},
]

# ========== 管理员账号 ==========
def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

USERS = [
    {"id": str(uuid.uuid4()), "username": "admin", "display_name": "系统管理员",
     "password_hash": _hash("admin123"), "role": "it_admin", "team_id": "team-hq"},
    {"id": str(uuid.uuid4()), "username": "kb_east", "display_name": "华东知识管理员",
     "password_hash": _hash("kb123456"), "role": "kb_admin", "team_id": "team-east"},
    {"id": str(uuid.uuid4()), "username": "kb_south", "display_name": "华南知识管理员",
     "password_hash": _hash("kb123456"), "role": "kb_admin", "team_id": "team-south"},
    {"id": str(uuid.uuid4()), "username": "kb_north", "display_name": "华北知识管理员",
     "password_hash": _hash("kb123456"), "role": "kb_admin", "team_id": "team-north"},
    {"id": str(uuid.uuid4()), "username": "kb_west", "display_name": "华西知识管理员",
     "password_hash": _hash("kb123456"), "role": "kb_admin", "team_id": "team-west"},
    {"id": str(uuid.uuid4()), "username": "kb_central", "display_name": "华中知识管理员",
     "password_hash": _hash("kb123456"), "role": "kb_admin", "team_id": "team-central"},
]

# ========== 基础Q&A ==========
BASE_QA = [
    ("如何查询客户出货记录？",
     "登录ERP系统 → 销售管理 → 出货查询，输入客户编号或名称即可查看历史出货记录。"),
    ("退货流程是怎样的？",
     "1. 客户提出退货申请\n2. 业务员确认退货原因\n3. 品质部门检验\n4. 财务开立红字发票\n5. 仓库接收退货\n6. 系统更新库存"),
    ("如何申请价格折扣？",
     "填写《价格审批单》→ 业务主管审批 → 财务审批 → 总经理审批（>10%折扣）。审批通过后通知客户。"),
    ("出口到欧洲需要什么认证？",
     "主要认证：CE认证（强制）、REACH法规（化学品）、RoHS指令（电子电器）。具体要求因产品类别而异。"),
    ("新客户信用审核流程？",
     "1. 收集客户营业执照、财务报表\n2. 信用调查（邓白氏/天眼查）\n3. 设定初始信用额度\n4. 财务部审批\n5. 系统录入客户信息"),
    ("如何处理客户投诉？",
     "1. 接收投诉并登记\n2. 24小时内响应\n3. 调查原因\n4. 制定解决方案\n5. 执行方案并跟踪\n6. 回访确认满意度"),
    ("出口报关需要哪些文件？",
     "基本文件：商业发票、装箱单、报关单、合同、产地证。特殊产品可能需要：检验检疫证书、许可证等。"),
    ("如何查看团队业绩排名？",
     "登录知识库系统 → 管理台 → 数据概览，可查看团队整体业绩和个人排名数据。"),
]

# ========== SQL生成 ==========
def generate_sql():
    """生成INSERT SQL"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sqls = []

    # Teams
    sqls.append("-- 团队数据")
    for t in TEAMS:
        sqls.append(
            f"INSERT IGNORE INTO teams (id, name, code, region, created_at, updated_at) "
            f"VALUES ('{t['id']}', '{t['name']}', '{t['code']}', '{t['region']}', '{now}', '{now}');"
        )

    # Users
    sqls.append("\n-- 管理员账号")
    for u in USERS:
        sqls.append(
            f"INSERT IGNORE INTO users (id, username, display_name, password_hash, role, team_id, is_active, created_at, updated_at) "
            f"VALUES ('{u['id']}', '{u['username']}', '{u['display_name']}', "
            f"'{u['password_hash']}', '{u['role']}', '{u['team_id']}', 1, '{now}', '{now}');"
        )

    # Q&A
    sqls.append("\n-- 基础Q&A")
    for q, a in BASE_QA:
        qa_id = str(uuid.uuid4())
        sqls.append(
            f"INSERT INTO qa_meta (id, team_id, question, answer, question_summary, answer_summary, version, created_at, updated_at) "
            f"VALUES ('{qa_id}', 'team-hq', '{q}', '{a}', '{q[:200]}', '{a[:200]}', 1, '{now}', '{now}');"
        )

    # Announcement
    sqls.append("\n-- 欢迎公告")
    ann_id = str(uuid.uuid4())
    sqls.append(
        f"INSERT INTO announcements (id, title, content, is_active, created_by, created_at, updated_at) "
        f"VALUES ('{ann_id}', '🎉 AI知识库系统上线', "
        f"'欢迎使用AI知识库系统！如有任何问题，请联系IT管理员。', 1, "
        f"'{USERS[0]['id']}', '{now}', '{now}');"
    )

    return "\n".join(sqls)


if __name__ == "__main__":
    sql = generate_sql()
    print(sql)

    # 同时写入文件
    with open("seed_production.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print("\n✅ SQL已写入 seed_production.sql")
