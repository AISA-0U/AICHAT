# agent.py
from openai import OpenAI
import json
from tools import TOOLS_SCHEMA, AVAILABLE_FUNCTIONS

# 初始化API客户端（你可以替换为你使用的模型API，比如DeepSeek, 阿里百炼, 智谱等）
client = OpenAI(
    api_key="sk-46f749049b464f2cb2777063d8fc96e2",  # 替换为你的 API_KEY
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 替换为对应的接口地址
)

MODEL_NAME = "qwen-plus"  # 替换为你的模型名称


def run_agent(messages):
    """
    智能体核心逻辑：处理对话并自动调度工具
    """
    # 限制最大工具调用循环次数，防止死循环
    max_iterations = 5

    for _ in range(max_iterations):
        # 1. 向大模型发送当前所有消息和可用的工具
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",  # 让模型自主决定是否调用工具
            temperature=0.7
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # 2. 判断模型是否想要调用工具
        if not tool_calls:
            # 如果不调用工具，直接返回模型的回复
            messages.append({"role": "assistant", "content": response_message.content})
            return response_message.content, messages

        # 3. 如果需要调用工具
        # 先将模型的“调用工具请求”存入历史记录
        assistant_message = {
            "role": "assistant",
            "content": response_message.content,
            "tool_calls":[
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in tool_calls
            ]
        }
        messages.append(assistant_message)

        # 遍历执行模型请求的所有工具
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = AVAILABLE_FUNCTIONS.get(function_name)

            if function_to_call:
                # 解析模型传过来的参数
                function_args = json.loads(tool_call.function.arguments)
                # 实际执行Python函数
                function_response = function_to_call(**function_args)

                # 4. 将工具执行的结果返回给大模型
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                })
            else:
                # 如果找不到该工具
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": "Error: Tool not found.",
                })

        # 执行完工具后，代码会进入下一次循环（将工具结果丢给AI进行下一步总结）

    return "已达到最大思考次数限制。", messages