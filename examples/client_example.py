"""
================================================================================
客户端示例 - 展示如何与SelfEvolvingAI API交互
================================================================================
"""

import json
import urllib.request


BASE_URL = "http://localhost:8000"


def api_get(path: str) -> dict:
    """GET请求"""
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def api_post(path: str, data: dict) -> dict:
    """POST请求"""
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def api_post_stream(path: str, data: dict):
    """流式POST请求"""
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method='POST',
    )
    with urllib.request.urlopen(req) as resp:
        buffer = ""
        while True:
            chunk = resp.read(1024)
            if not chunk:
                break
            buffer += chunk.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line.startswith('data: ') and line != 'data: [DONE]':
                    try:
                        data = json.loads(line[6:])
                        content = data.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass


def main():
    print("=" * 60)
    print("SelfEvolvingAI 客户端示例")
    print("=" * 60)

    # 1. 查看API信息
    print("\n--- API信息 ---")
    info = api_get("/")
    print(f"名称: {info['name']}")
    print(f"版本: {info['version']}")
    print(f"模块: {info['modules']}")

    # 2. 查看系统状态
    print("\n--- 系统状态 ---")
    status = api_get("/api/status")
    print(f"版本: {status['version']}")
    print(f"模块: {status['modules_loaded']}")
    print(f"交互: {status['total_interactions']}")

    # 3. 健康检查
    print("\n--- 健康检查 ---")
    health = api_get("/api/health")
    print(f"状态: {health['status']}")

    # 4. 查看LLM提供商
    print("\n--- LLM提供商 ---")
    providers = api_get("/api/providers")
    print(f"可用: {providers['available_providers']}")
    print(f"默认: {providers['default_provider']}")

    # 5. 普通聊天
    print("\n--- 普通聊天 ---")
    response = api_post("/api/chat", {"message": "你好，自我进化AI！"})
    print(f"回复: {response['response'][:100]}")
    print(f"模型: {response.get('model', 'N/A')}")
    print(f"置信度: {response['confidence']:.2f}")

    # 6. 流式聊天
    print("\n--- 流式聊天 ---")
    print("回复: ", end="", flush=True)
    for chunk in api_post_stream("/api/chat/stream", {
        "message": "用3句话介绍什么是自我进化AI",
    }):
        print(chunk, end="", flush=True)
    print()

    # 7. 学习知识
    print("\n--- 学习知识 ---")
    result = api_post("/api/learn", {
        "content": "Python是一种解释型、面向对象的高级编程语言",
    })
    print(f"学习结果: {result}")

    # 8. 设定目标
    print("\n--- 设定目标 ---")
    result = api_post("/api/goal", {
        "title": "学习机器学习",
        "description": "掌握机器学习基础知识和实践",
    })
    print(f"目标: {result}")

    # 9. 触发进化
    print("\n--- 触发进化 ---")
    result = api_post("/api/evolve", {})
    print(f"代数: {result['generation']}")
    print(f"改进: {result['improvements']}")

    print("\n" + "=" * 60)
    print("示例完成!")


if __name__ == "__main__":
    main()
