GLM_CONFIG = {
    # 智谱开放平台的 API Key 环境变量名；真实 key 用 export 设置，不要写进代码。
    "key_env": "BIGMODEL_API_KEY",
    # 如果你用 IDE 直接运行、不会设置环境变量，可以临时把 key 填在这里。
    "api_key": "af435370ce2f44e5abd348e2aad68168.7YkIUVZMP4rRyVGX",
    # GLM-5.2 的 HTTP 对话接口地址。
    "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    # 要调用的模型名称。
    "model": "glm-5.2",
    # 控制回答发散程度；越低越稳定。
    "temperature": 0.7,
    # 单次回答最多生成的 token 数。
    "max_tokens": 1024,
    # False 表示一次性返回完整结果；True 表示流式返回。
    "stream": False,
    # 每个 Agent 最多等待模型返回的秒数；学习 demo 里短一点，避免看起来卡住。
    "timeout": 15,
}

AGENT_ROLES = [
    {
        "name": "产品",
        "role": "拆清楚用户想要什么，给出最小可交付范围。",
    },
    {
        "name": "设计",
        "role": "把需求整理成清晰的页面结构和文案排版。",
    },
    {
        "name": "开发",
        "role": "说明最小实现路径，只保留必须代码。",
    },
    {
        "name": "测试",
        "role": "列出最少验收点，确认功能能跑通。",
    },
]


def usage_message() -> str:
    return "config.py 只放配置。要看 agent 创建和调度流程，请运行 main.py。"


if __name__ == "__main__":
    print(usage_message())
