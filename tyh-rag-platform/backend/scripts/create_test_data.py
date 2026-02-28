"""
测试数据生成脚本
创建测试用户、Q&A数据，为功能测试解除阻塞
"""
import httpx
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def get_client():
    return httpx.Client(base_url=BASE_URL, proxy=None, timeout=15.0)

def login(client, username="admin", password="admin123"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token") or data.get("data", {}).get("access_token")
    if not token:
        print(f"Login response: {data}")
        raise ValueError("Cannot find access_token in login response")
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"✅ Logged in as {username}")
    return token

def create_user(client, username, password, display_name, role, team_id="team-default"):
    try:
        resp = client.post("/users", json={
            "username": username,
            "password": password,
            "display_name": display_name,
            "role": role,
            "team_id": team_id,
        })
        if resp.status_code == 201:
            print(f"✅ Created user: {username} ({role})")
            return resp.json()
        elif resp.status_code == 400:
            print(f"⚠️  User {username}: {resp.text}")
            return None
        else:
            print(f"❌ Failed to create {username}: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating {username}: {e}")
        return None

def create_qa(client, question, answer):
    try:
        resp = client.post("/qa-pairs", json={"question": question, "answer": answer})
        if resp.status_code == 201:
            print(f"✅ Created Q&A: {question[:30]}...")
            return resp.json()
        else:
            print(f"❌ Failed to create Q&A: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating Q&A: {e}")
        return None

def main():
    client = get_client()
    
    # 1. Login as admin
    print("\n=== Step 1: Login ===")
    login(client)
    
    # 2. Create test users (with retry after errors)
    print("\n=== Step 2: Create Test Users ===")
    users_to_create = [
        ("user01", "admin123", "测试用户", "user", "team-default"),
        ("kb_admin", "admin123", "知识管理员", "kb_admin", "team-default"),
        ("user02", "admin123", "团队B用户", "user", "team-default"),
    ]
    
    for uname, pwd, dname, role, tid in users_to_create:
        result = create_user(client, uname, pwd, dname, role, tid)
        if result is None:
            # Re-create client in case connection was reset
            time.sleep(1)
            client = get_client()
            login(client)
    
    # 3. Verify users
    print("\n=== Step 3: Verify Users ===")
    try:
        resp = client.get("/users")
        users = resp.json()
        print(f"Total users: {users['total']}")
        for u in users['items']:
            print(f"  - {u['username']} ({u['role']}) team={u.get('team_name','N/A')} active={u['is_active']}")
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    
    # 4. Create Q&A data
    print("\n=== Step 4: Create Q&A Data ===")
    qa_data = [
        {"question": "退货流程是怎样的？", "answer": "退货流程如下：\n1. 登录账号，进入\"我的订单\"\n2. 找到需要退货的订单，点击\"申请退货\"\n3. 选择退货原因，填写说明\n4. 提交申请，等待审核（1-3个工作日）\n5. 审核通过后，按照指引寄回商品\n6. 收到退货后7个工作日内退款到原支付账户"},
        {"question": "产品保修期多久？", "answer": "产品保修期说明：\n- 电子产品：1年全国联保\n- 家具类：3年质保\n- 配件类：6个月保修\n保修期内非人为损坏可免费维修或更换。"},
        {"question": "如何联系客服？", "answer": "联系客服方式：\n1. 在线客服：工作日9:00-18:00\n2. 客服热线：400-123-4567\n3. 邮箱：support@example.com\n4. 微信公众号：搜索\"XX客服\""},
        {"question": "VIP会员有什么权益？", "answer": "VIP会员权益包括：\n1. 专属折扣：全场商品95折\n2. 优先发货：订单优先处理\n3. 专属客服：一对一服务\n4. 积分翻倍：购物积分2倍累计\n5. 生日礼包：生日月享特别优惠"},
        {"question": "发货时间是多久？", "answer": "发货时间说明：\n- 普通订单：下单后48小时内发货\n- VIP订单：下单后24小时内发货\n- 预售商品：按页面标注时间发货\n- 定制商品：7-15个工作日发货\n物流一般2-5天到达，偏远地区可能延长1-3天。"},
    ]
    
    for qa in qa_data:
        result = create_qa(client, qa["question"], qa["answer"])
        if result is None:
            time.sleep(1)
            client = get_client()
            login(client)
            create_qa(client, qa["question"], qa["answer"])
    
    # 5. Verify Q&A
    print("\n=== Step 5: Verify Q&A ===")
    try:
        resp = client.get("/qa-pairs")
        qa_list = resp.json()
        print(f"Total Q&A: {qa_list['total']}")
        for q in qa_list['items']:
            print(f"  - Q: {q['question'][:40]}... A: {q['answer'][:30]}...")
    except Exception as e:
        print(f"❌ Error listing Q&A: {e}")
    
    print("\n=== Done! ===")
    print("Test data generation complete!")

if __name__ == "__main__":
    main()

