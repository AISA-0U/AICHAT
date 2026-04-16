# tools.py
import pandas as pd
import json
import os
import subprocess
import tempfile
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

# 确保基础目录存在
os.makedirs("outputs", exist_ok=True)
os.makedirs("memory", exist_ok=True)
os.makedirs("workspace", exist_ok=True)  # 为文件系统和代码执行创建一个安全工作区

# Tavily 初始化
TAVILY_API_KEY = "tvly-your-tavily-api-key-here"
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


# ==========================================
# 1. 工具的具体实现函数 (Python逻辑)
# ==========================================

# 【1. 原有工具：搜索与导出】
def search_web(query: str) -> str:
    print(f"🔧 [执行工具] Tavily 搜索: {query}")
    try:
        response = tavily_client.search(query=query, search_depth="advanced", max_results=3)
        return json.dumps({"results": [{"title": r.get("title"), "content": r.get("content"), "url": r.get("url")} for r
                                       in response.get("results", [])]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def export_to_excel(data_list: list, filename: str) -> str:
    print(f"🔧 [执行工具] 生成Excel: {filename}.xlsx")
    try:
        filepath = f"outputs/{filename}.xlsx"
        pd.DataFrame(data_list).to_excel(filepath, index=False)
        return json.dumps({"status": "success", "filepath": filepath}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# 【2. 网络与Web交互：抓取网页】
def scrape_webpage(url: str) -> str:
    """读取并提取指定URL的纯文本内容"""
    print(f"🔧 [执行工具] 抓取网页内容: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # 提取纯文本，去除多余空白
        text = ' '.join(soup.stripped_strings)
        return json.dumps({"url": url, "content": text[:4000] + "...(截断)" if len(text) > 4000 else text},
                          ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"网页抓取失败: {str(e)}"}, ensure_ascii=False)


# 【3. 文件系统：读写文件】
def manage_file(action: str, filename: str, content: str = "") -> str:
    """在 workspace 目录下读取或写入文件"""
    print(f"🔧 [执行工具] 文件操作: {action} -> {filename}")
    # 安全限制：只能操作 workspace 目录下的文件
    safe_path = os.path.join("workspace", os.path.basename(filename))
    try:
        if action == "write":
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return json.dumps({"status": "success", "message": f"已成功写入文件: {safe_path}"}, ensure_ascii=False)
        elif action == "read":
            if not os.path.exists(safe_path):
                return json.dumps({"error": "文件不存在"}, ensure_ascii=False)
            with open(safe_path, 'r', encoding='utf-8') as f:
                return json.dumps({"content": f.read()}, ensure_ascii=False)
        else:
            return json.dumps({"error": "未知的文件操作指令"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# 【4. 代码执行：安全的Python沙盒执行】
# 【4. 代码执行：安全的Python沙盒执行 (修复Windows编码版)】
def execute_python_code(code: str) -> str:
    """在隔离的子进程中执行Python代码并获取输出"""
    print(f"🔧 [执行工具] 运行Python代码...")
    try:
        # 为了万无一失，我们在大模型生成的代码最顶部强行加上 utf-8 声明
        if not code.startswith("# -*- coding: utf-8 -*-"):
            code = "# -*- coding: utf-8 -*-\n" + code

        # 核心修复1：添加 encoding='utf-8' 强制写入 UTF-8 格式
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_script:
            temp_script.write(code)
            temp_path = temp_script.name

        # 核心修复2：subprocess.run 也要加上 encoding='utf-8'，防止终端输出中文时乱码
        result = subprocess.run(
            ['python', temp_path],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8'
        )

        # 清理临时文件
        os.remove(temp_path)

        output = result.stdout if result.returncode == 0 else result.stderr
        return json.dumps({"status": "success" if result.returncode == 0 else "error", "output": output[:2000]},
                          ensure_ascii=False)

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "代码执行超时（超过5秒）"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# 【5. 终端操作：执行系统命令 (带安全拦截机制)】
def execute_terminal_command(command: str) -> str:
    """执行 Shell 终端命令"""
    print(f"🔧 [执行工具] 终端命令请求: {command}")

    # 简单的危险命令拦截黑名单
    dangerous_keywords = ['rm -rf', 'format', 'mkfs', 'shutdown', 'reboot', 'del /f']
    if any(keyword in command for keyword in dangerous_keywords):
        return json.dumps({"error": "安全拦截：人工审批拒绝，禁止执行破坏性系统命令。"}, ensure_ascii=False)

    try:
        # 注意：真实生产环境中，此处应通过WebSocket或打断机制发送给前端等待人工点击“允许”
        # 当前通过黑名单机制模拟自动审批通过
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout if result.returncode == 0 else result.stderr
        return json.dumps({"output": output[:2000]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# 【6. 记忆管理：长期记忆的存取】
MEMORY_FILE = "memory/long_term_memory.json"


def manage_memory(action: str, key: str, value: str = "") -> str:
    """存储或检索跨会话的长期记忆"""
    print(f"🔧 [执行工具] 记忆系统: {action} -> {key}")

    # 初始化记忆文件
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory_db = json.load(f)

        if action == "save":
            memory_db[key] = value
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory_db, f, ensure_ascii=False, indent=2)
            return json.dumps({"status": "success", "message": f"记忆 '{key}' 已永久保存。"}, ensure_ascii=False)

        elif action == "retrieve":
            return json.dumps({"value": memory_db.get(key, "未找到相关记忆")}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ==========================================
# 2. 映射表
# ==========================================
AVAILABLE_FUNCTIONS = {
    "search_web": search_web,
    "export_to_excel": export_to_excel,
    "scrape_webpage": scrape_webpage,
    "manage_file": manage_file,
    "execute_python_code": execute_python_code,
    "execute_terminal_command": execute_terminal_command,
    "manage_memory": manage_memory
}

# ==========================================
# 3. 提供给大模型的工具描述 (JSON Schema)
# ==========================================
TOOLS_SCHEMA = [
    # 1. 搜索
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "专业互联网搜索引擎，用于获取最新新闻、未知知识、实时信息。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                "required": ["query"]
            }
        }
    },
    # 2. 抓取
    {
        "type": "function",
        "function": {
            "name": "scrape_webpage",
            "description": "当已知具体URL且需要阅读该网页详细内容时，调用此工具抓取网页文本。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "目标网页的完整URL"}},
                "required": ["url"]
            }
        }
    },
    # 3. 导出表格
    {
        "type": "function",
        "function": {
            "name": "export_to_excel",
            "description": "将结构化数据保存为Excel文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_list": {"type": "array", "items": {"type": "object"},
                                  "description": "由字典组成的数组，代表表格行"},
                    "filename": {"type": "string", "description": "文件名（不含.xlsx后缀）"}
                },
                "required": ["data_list", "filename"]
            }
        }
    },
    # 4. 文件系统
    {
        "type": "function",
        "function": {
            "name": "manage_file",
            "description": "读取或写入本地文件。所有文件都保存在工作区(workspace)中。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write"], "description": "读取(read)或写入(write)"},
                    "filename": {"type": "string", "description": "文件名，例如 'script.py' 或 'notes.txt'"},
                    "content": {"type": "string", "description": "写入文件时的文本内容。如果是读取则留空。"}
                },
                "required": ["action", "filename"]
            }
        }
    },
    # 5. 代码执行
    {
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "在沙箱环境中运行Python代码。可用于数学计算、数据处理、算法验证等。注意要使用 print() 才能得到输出结果。",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "要执行的合法Python代码字符串"}},
                "required": ["code"]
            }
        }
    },
    # 6. 终端命令
    {
        "type": "function",
        "function": {
            "name": "execute_terminal_command",
            "description": "执行操作系统终端命令(Shell/CMD)。可用于系统查询、安装依赖包(如 pip install)等。系统包含安全拦截机制。",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "需要执行的终端命令"}}
            }
        }
    },
    # 7. 记忆系统
    {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": "读写长期记忆。当用户让你'记住某事'，或你需要调用以前用户的偏好时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["save", "retrieve"],
                               "description": "存入(save)或读取(retrieve)"},
                    "key": {"type": "string", "description": "记忆的键名/主题，例如 'user_name' 或 'coding_preference'"},
                    "value": {"type": "string", "description": "存入记忆的具体内容。如果是读取(retrieve)则留空。"}
                },
                "required": ["action", "key"]
            }
        }
    }
]