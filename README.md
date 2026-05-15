# The Client Savior｜客户拯救者

The Client Savior 是一个面向中国移动培训场景的一天可演示 Streamlit MVP。项目使用本地 JSON 政策库做快速候选召回，默认调用 OpenAI-compatible 云端模型生成客户分析、推荐理由和挽留话术；当 API Key 缺失、网络异常或超时时，自动切换本地模板兜底。

## 设计边界

- 不使用本地大模型。
- 不使用向量数据库。
- 不使用 LangChain、LlamaIndex、PyTorch、Transformers。
- 不在运行时解析 Word 或 Excel。
- 不连接真实 CRM/BOSS 系统。
- 办理资格、合约、优惠期、预存、初装费、调测费均以系统办理结果为准。

## 启动步骤

### 一键建立环境（Windows PowerShell）

推荐现场演示前直接运行：

```powershell
cd "D:\Github\The Client Savior"
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_lan.ps1

```

脚本会自动：

- 优先选择 Python 3.11，其次 3.12/3.10；
- 创建或复用 `.venv`；
- 安装 `requirements.txt`；
- 如果 `.env` 不存在，则从 `.env.example` 复制一份；
- 运行 `python scripts/smoke_test.py` 冒烟测试。

如果你想删除旧虚拟环境并重建：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1 -Recreate
```

如果要指定 Python 路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1 -Python "D:\miniconda\envs\carbon\python.exe" -Recreate
```

### 手动启动

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 配置 API Key：

复制 `.env.example` 为 `.env`，填写 `DASHSCOPE_API_KEY`。

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

3. 运行冒烟测试：

```bash
python scripts/smoke_test.py
```

4. 启动页面：

```bash
streamlit run app.py
```

使用项目虚拟环境直接启动：

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### 局域网访问

如果需要让同一 Wi-Fi / 局域网内的其他人访问，使用局域网启动脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_lan.ps1
```

脚本会监听 `0.0.0.0:8501`，并打印可访问地址，例如：

```text
http://192.168.1.250:8501
```

同局域网的人在浏览器打开这个地址即可。如果打不开，通常是 Windows 防火墙拦截了入站连接，需要允许 Python/Streamlit 通过防火墙，或用管理员 PowerShell 添加端口规则：

```powershell
New-NetFirewallRule -DisplayName "The Client Savior Streamlit 8501" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8501
```

## LLM 配置

默认使用 Qwen / DashScope / 阿里云百炼 OpenAI-compatible API：

```env
DASHSCOPE_API_KEY=替换成你的阿里云百炼或 DashScope API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-flash
LLM_TIMEOUT=6
LLM_MAX_TOKENS=800
```

也可以使用 `OPENAI_API_KEY` 作为备用 Key。未配置 API Key 时，系统不会崩溃，会自动使用本地模板兜底。

`.env` 已加入 `.gitignore`，不要提交真实 Key。

费用安全提醒：建议在阿里云百炼控制台开启“免费额度用完即停”功能。额度耗尽后接口会返回 `AllocationQuota.FreeTierOnly` 错误，项目会按 LLM 调用失败处理并切换到本地模板兜底，避免继续产生调用费用。

## 文件结构

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── data/
│   ├── policies.json
│   └── demo_cases.json
├── scripts/
│   ├── setup_env.ps1
│   └── smoke_test.py
└── src/
    ├── __init__.py
    ├── agent.py
    ├── matcher.py
    ├── llm_client.py
    ├── templates.py
    └── models.py
```

## 演示说明

页面包含三个 Tab：

- AI 投诉处理：选择演示案例或手动输入投诉和客户画像，一键生成挽留方案。
- 管理看板：统计本次演示的处理数量、风险客户、生成模式、投诉类型和推荐政策次数。
- 政策库：查看 `data/policies.json` 中的所有政策卡，支持搜索和分类筛选。
