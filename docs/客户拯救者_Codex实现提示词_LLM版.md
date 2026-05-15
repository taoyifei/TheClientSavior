# 给 Codex 的实现提示词：The Client Savior「客户拯救者」LLM 核心版

下面这段可以直接复制给 Codex，让它生成一个 **1 天可演示、CPU-only、LLM 为核心卖点** 的 Streamlit 项目。

---

你是一个资深 Python + Streamlit 工程师。请帮我实现一个智能体 Demo，名称是：

# The Client Savior｜客户拯救者

## 一、项目背景

这个 Demo 用于中国移动相关培训场景。目标是在一线人员处理投诉时，根据客户投诉内容和客户画像，快速匹配合适的套餐、宽带、终端、亲情网、保有政策，并由 LLM 生成个性化挽留话术。

运行环境是普通笔记本电脑：Ultra 9 CPU，无独立显卡。

**关键要求：LLM 必须是核心卖点。**

允许本地规则和模板兜底，但正常链路必须调用 LLM，并且页面上要明确展示：

- 使用的模型；
- LLM 调用耗时；
- LLM 是否成功；
- 是否启用了本地兜底。

不能出现点击后等待 1–2 分钟才出结果。正常目标是 3–8 秒返回，超过 8–10 秒自动兜底。

---

## 二、总体方案

请实现：

```text
Streamlit 页面
+ 本地 JSON 政策卡
+ 本地快速候选召回 Top 5
+ 云端 LLM 结构化分析与话术生成
+ 本地模板兜底
+ session_state 管理看板
```

不要本地运行大模型。不要使用 PyTorch、Transformers、Ollama、LangChain、FAISS、Milvus、Chroma。

---

## 三、技术栈要求

使用：

```text
Python 3.10+
Streamlit
OpenAI SDK
python-dotenv
标准库 json / re / time / hashlib / dataclasses / typing / os
```

`requirements.txt` 只需要：

```txt
streamlit
openai
python-dotenv
```

---

## 四、LLM 接入要求

使用 OpenAI-compatible 接口，默认按 Qwen / DashScope / 阿里云百炼配置。

`.env.example` 内容：

```bash
# Qwen / DashScope / 阿里云百炼 OpenAI-compatible API
DASHSCOPE_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
LLM_TIMEOUT=8
```

代码中读取环境变量：

```python
api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
model = os.getenv("LLM_MODEL", "qwen-turbo")
timeout = float(os.getenv("LLM_TIMEOUT", "8"))
```

调用方式使用 OpenAI SDK：

```python
from openai import OpenAI

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=timeout,
)

response = client.chat.completions.create(
    model=model,
    messages=[...],
    temperature=0.3,
    max_tokens=800,
)
```

必须实现：

1. API Key 缺失时不报错，转本地兜底；
2. 网络失败时转本地兜底；
3. LLM 超时时转本地兜底；
4. LLM 返回非 JSON 时也能尽量解析，解析失败则兜底；
5. 对同一输入做 hash 缓存，避免重复调用。

---

## 五、项目文件结构

请创建以下结构：

```text
client-savior/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── data/
│   ├── policies.json
│   └── demo_cases.json
└── src/
    ├── __init__.py
    ├── agent.py
    ├── matcher.py
    ├── llm_client.py
    ├── templates.py
    └── models.py
```

---

## 六、数据模型

在 `src/models.py` 中用 dataclass 或 TypedDict 定义：

```python
@dataclass
class CustomerProfile:
    monthly_fee: int
    customer_type: str
    tenure_years: float
    has_broadband: bool
    wants_device: bool
    family_mobile_count: int
    wants_port_out: bool

@dataclass
class PolicyMatch:
    policy_id: str
    title: str
    score: int
    reasons: list[str]
    policy: dict

@dataclass
class AgentResult:
    mode: str  # "llm" or "fallback"
    model: str
    elapsed_seconds: float
    customer_analysis: dict
    recommended_policies: list[dict]
    retention_script: dict
    internal_notes: list[str]
    local_matches: list[dict]
```

也可以使用字典，但代码必须清晰。

---

## 七、政策库 data/policies.json

请内置以下 10 张政策卡。字段必须包含：

`id`、`title`、`category`、`price`、`target`、`benefits`、`conditions`、`keywords`、`risk_notes`、`script_hint`。

```json
[
  {
    "id": "P01",
    "title": "39元新潮玩乐享卡 200G",
    "category": "流量/低资费",
    "price": "39元/月",
    "target": "流量不够、资费敏感、新入网或低档客户",
    "benefits": ["170G通用流量", "30G定向流量", "100分钟语音", "办理当天立即生效"],
    "conditions": ["首次充值100元及以上", "优惠期24个月", "24个月后恢复原套餐资费"],
    "keywords": ["流量", "不够", "太贵", "上网", "刷视频", "低价", "39"],
    "risk_notes": ["需提醒优惠期和到期资费", "是否可办以系统办理结果为准"],
    "script_hint": "突出低月租和大流量，适合先解决流量不足和资费敏感。"
  },
  {
    "id": "P02",
    "title": "59元畅玩卡 280G",
    "category": "流量/升档",
    "price": "59元/月",
    "target": "流量重度使用、愿意小幅升档客户",
    "benefits": ["250G通用流量", "30G定向流量", "100分钟语音", "可叠加亲情网优惠"],
    "conditions": ["首次充值100元及以上", "优惠期24个月", "24个月后恢复原套餐资费"],
    "keywords": ["流量", "不够", "视频", "直播", "上网慢", "59", "大流量"],
    "risk_notes": ["需说明优惠期", "亲情网是否添加副号需客户确认"],
    "script_hint": "适合流量诉求强的客户，用小幅升档换明显流量提升。"
  },
  {
    "id": "P03",
    "title": "129元全家享套餐 + 宽带 + 1元升千兆",
    "category": "家庭/宽带",
    "price": "前24个月约72元/月起，按实际办理为准",
    "target": "家庭用户、宽带需求、希望手机和宽带一起解决的客户",
    "benefits": ["手机套餐权益", "宽带", "可1元升级千兆", "适合家庭融合"],
    "conditions": ["以系统办理结果为准", "宽带区域和初装费规则需确认", "开户可能自动同订短剧包"],
    "keywords": ["宽带", "家里", "孩子", "上网课", "家庭", "千兆", "网速", "129"],
    "risk_notes": ["宽带覆盖和初装费需提前核实", "短剧包等附加业务需说明"],
    "script_hint": "适合把投诉从单点网络问题转为家庭融合方案，突出一揽子解决。"
  },
  {
    "id": "P04",
    "title": "1000元充送无忧包",
    "category": "高套保有/返费",
    "price": "一次性充值1000元，配套398.98元无忧包",
    "target": "199元及以上套餐、网龄5年以上、高价值或高危客户",
    "benefits": ["充值1000元话费", "赠送1000元话费", "赠费分10个月返还", "适合老客户保有"],
    "conditions": ["承诺使用199+套餐12个月", "每个号码限办理一次", "需符合系统目标客户"],
    "keywords": ["老客户", "199", "贵", "携转", "离网", "返费", "优惠", "保有"],
    "risk_notes": ["需客户接受一次性充值和无忧包", "具体资格以系统办理结果为准"],
    "script_hint": "适合高价值客户投诉贵或想携转，重点讲老客户返费和权益。"
  },
  {
    "id": "P05",
    "title": "600元充送无忧包",
    "category": "高套保有/返费",
    "price": "一次性充值600元，配套298.98元无忧包",
    "target": "119元及以上、网龄较长、有集团属性或高危客户",
    "benefits": ["充值600元话费", "赠送600元话费", "赠费分10个月返还", "适合中高套保有"],
    "conditions": ["承诺使用119+套餐12个月", "每个号码限办理一次", "需符合系统目标客户"],
    "keywords": ["119", "老客户", "集团", "贵", "携转", "返费", "优惠"],
    "risk_notes": ["需说明充值和无忧包扣费", "具体资格以系统办理结果为准"],
    "script_hint": "适合119+客户，表达为老客户专属返费和权益补偿。"
  },
  {
    "id": "P06",
    "title": "升档翻倍流量合约",
    "category": "升档/流量扩容",
    "price": "按升档套餐档位确定",
    "target": "低档客户流量不够，愿意升档换更多流量或语音权益",
    "benefits": ["升档指定套餐送24个月流量或语音", "例如39升59可获得更多流量", "适合流量投诉挽留"],
    "conditions": ["合约期24个月", "优惠期内取消可能有赔付", "具体翻倍权益以系统分配为准"],
    "keywords": ["升档", "流量", "不够", "翻倍", "合约", "套餐", "语音"],
    "risk_notes": ["必须说明合约期和取消赔付", "随机分配权益需以系统为准"],
    "script_hint": "适合把客户从低档套餐引导到更合适档位，但要讲清合约。"
  },
  {
    "id": "P07",
    "title": "全国亲情网",
    "category": "家庭/黏性",
    "price": "入套客户可减免基础功能费，超出成员按规则收费",
    "target": "家庭成员多、亲友通话多、希望提升家庭黏性的客户",
    "benefits": ["全国移动号码互打", "支持520-560专属短号", "1个主号+3个副号", "本地主副号可享流量优惠"],
    "conditions": ["主副号和成员数量需确认", "超出成员可能按1元/月/人收费"],
    "keywords": ["家人", "家庭", "亲情", "通话", "副号", "短号", "成员"],
    "risk_notes": ["需确认主号、副号和统付关系", "成员超出时需提醒收费"],
    "script_hint": "适合作为主套餐之外的辅助挽留，提高家庭关系黏性。"
  },
  {
    "id": "P08",
    "title": "199+宽带/FTTR组网方案",
    "category": "宽带/高套",
    "price": "按199+主套及宽带/FTTR规则办理",
    "target": "199+客户、宽带质量差、全屋WiFi覆盖诉求强的客户",
    "benefits": ["2000M或1000M宽带", "FTTR全光组网体验", "全屋高品质WiFi覆盖", "适合多设备家庭"],
    "conditions": ["需确认地址覆盖", "可能涉及调测费", "以实际安装现场情况为准"],
    "keywords": ["宽带", "WiFi", "网速", "覆盖", "FTTR", "卡顿", "199", "全屋"],
    "risk_notes": ["地址覆盖和调测费需核实", "FTTR设备和合约规则需说明"],
    "script_hint": "适合网络质量投诉，强调从宽带和组网角度彻底改善体验。"
  },
  {
    "id": "P09",
    "title": "金牛客户宽带新装优惠",
    "category": "重点客群/宽带",
    "price": "宽带新装免初装费，话费返还按规则执行",
    "target": "重点客群、想新装宽带、对初装费敏感的客户",
    "benefits": ["宽带新装免初装费", "办理全家享宽带套餐可获连续24个月话费返还", "可与升档扩容一起办理"],
    "conditions": ["是否金牛客户需系统标签确认", "返还规则以系统为准"],
    "keywords": ["金牛", "宽带", "初装费", "新装", "返还", "重点客户"],
    "risk_notes": ["需先查客户标签", "返费和初装费以系统确认为准"],
    "script_hint": "适合重点客户宽带投诉或新装需求，突出免初装费和长期返还。"
  },
  {
    "id": "P10",
    "title": "终端金币 / AI手机 / 顺差购机方案",
    "category": "终端/换机",
    "price": "按套餐、合约期、信用分和机型确定",
    "target": "想换机、对手机价格敏感、可接受合约或预存的客户",
    "benefits": ["购机直降或终端抵扣", "5G金币", "AI手机权益包", "部分方案支持顺差和流量"],
    "conditions": ["需确认信用分/芝麻分/网龄", "需确认是否有互斥合约", "机型和货源需符合要求"],
    "keywords": ["手机", "换机", "购机", "终端", "金币", "AI手机", "分期", "直降"],
    "risk_notes": ["必须核查互斥合约和机卡合一要求", "合约期、预存、低消要向客户讲清"],
    "script_hint": "适合客户想换机或被竞品终端优惠吸引时，用终端补贴做挽留。"
  }
]
```

---

## 八、demo_cases.json

请内置 4 条演示案例，方便现场一键填充。

```json
[
  {
    "name": "流量不够且想携转",
    "complaint": "客户说这个月流量又不够用了，刷视频老是提醒超量，套餐还贵，再这样就考虑换别家了。",
    "profile": {
      "monthly_fee": 39,
      "customer_type": "存量",
      "tenure_years": 2,
      "has_broadband": false,
      "wants_device": false,
      "family_mobile_count": 1,
      "wants_port_out": true
    }
  },
  {
    "name": "家庭宽带慢",
    "complaint": "家里宽带晚上特别卡，孩子上网课经常断，WiFi 到卧室就没信号，感觉这个宽带没法用了。",
    "profile": {
      "monthly_fee": 129,
      "customer_type": "家庭用户",
      "tenure_years": 3,
      "has_broadband": true,
      "wants_device": false,
      "family_mobile_count": 4,
      "wants_port_out": false
    }
  },
  {
    "name": "老客户觉得不公平",
    "complaint": "我用了移动这么多年，套餐每个月一百多，感觉新用户优惠比老用户多，我准备携号转网了。",
    "profile": {
      "monthly_fee": 119,
      "customer_type": "高套",
      "tenure_years": 6,
      "has_broadband": false,
      "wants_device": false,
      "family_mobile_count": 2,
      "wants_port_out": true
    }
  },
  {
    "name": "想换手机",
    "complaint": "我现在手机太旧了，其他运营商说可以便宜买新手机，你们这边有没有购机优惠？没有我就转过去。",
    "profile": {
      "monthly_fee": 89,
      "customer_type": "存量",
      "tenure_years": 4,
      "has_broadband": false,
      "wants_device": true,
      "family_mobile_count": 1,
      "wants_port_out": true
    }
  }
]
```

---

## 九、matcher.py 要求

实现本地候选召回，不要复杂模型。

函数：

```python
def match_policies(complaint: str, profile: CustomerProfile, policies: list[dict], top_k: int = 5) -> list[PolicyMatch]:
    ...
```

打分逻辑：

- 投诉文本命中政策 keywords：每个关键词 +8；
- 投诉包含“携转、离网、换别家、不用了”：保有类政策 +25；
- 当前套餐 <= 39 且政策为流量/低资费/升档类：+20；
- 当前套餐 >= 119 且政策为高套保有/返费/宽带类：+20；
- has_broadband 为 True 或投诉包含“宽带/WiFi/网速/卡顿”：宽带类 +25；
- wants_device 为 True 或投诉包含“手机/换机/购机”：终端类 +30；
- family_mobile_count >= 3：家庭/亲情网/全家享 +20；
- tenure_years >= 5：老客户/保有/返费类 +15；
- 风险高时：保有/返费类 +15。

每个匹配结果要包含 reasons，例如：

```python
["命中关键词：流量、不够", "客户明确有离网风险", "当前套餐较低，适合大流量或升档方案"]
```

---

## 十、llm_client.py 要求

实现以下函数：

```python
def is_llm_configured() -> bool:
    ...

def generate_with_llm(
    complaint: str,
    profile: dict,
    candidate_policies: list[dict],
) -> dict:
    ...
```

### 10.1 LLM Prompt

System Prompt：

```text
你是中国移动一线投诉挽留专家，也是一个严谨的 AI 助手。
你的任务是根据客户投诉、客户画像和候选政策，生成可执行的挽留方案。
要求：
1. 不要编造政策，不要使用候选政策之外的产品；
2. 涉及办理资格、合约、首充、预存、调测费、优惠期时，必须提醒“以系统办理结果为准”；
3. 语气要像一线客服，先安抚，再解释，再引导办理；
4. 输出必须是 JSON，不要 Markdown，不要多余解释。
```

User Prompt 模板：

```text
客户投诉：
{complaint}

客户画像：
{profile_json}

候选政策 Top 5：
{candidate_policies_json}

请输出如下 JSON：
{
  "customer_analysis": {
    "complaint_type": "流量不足/资费争议/宽带质量/换机需求/离网风险/其他",
    "emotion": "平稳/不满/强烈不满",
    "risk_level": "低/中/高",
    "key_needs": ["..."],
    "summary": "..."
  },
  "recommended_policies": [
    {
      "policy_id": "Pxx",
      "rank": 1,
      "reason": "为什么推荐该政策",
      "talking_point": "面向客户的一句话卖点"
    }
  ],
  "retention_script": {
    "opening": "安抚开场，不超过80字",
    "solution": "结合推荐政策说明解决方案，不超过180字",
    "risk_disclosure": "办理提醒，不超过120字",
    "next_step": "下一步引导，不超过80字"
  },
  "internal_notes": ["给一线人员看的办理提醒"]
}
```

### 10.2 JSON 解析

LLM 可能返回带 ```json 的内容，请实现稳健解析：

- 去掉 ```json / ```；
- 找到第一个 `{` 和最后一个 `}`；
- `json.loads`；
- 解析失败时抛出异常给 agent 兜底。

### 10.3 缓存

用 `st.session_state` 或模块级字典缓存。Key 为：

```python
hashlib.md5((complaint + json.dumps(profile, ensure_ascii=False, sort_keys=True) + candidate_ids).encode("utf-8")).hexdigest()
```

缓存结果中保留：

- result；
- elapsed_seconds；
- model；
- cached=True/False。

---

## 十一、templates.py 要求

实现本地兜底函数：

```python
def build_fallback_result(complaint: str, profile: dict, matches: list[PolicyMatch]) -> dict:
    ...
```

兜底结果必须和 LLM 输出结构一致：

```python
{
  "customer_analysis": {...},
  "recommended_policies": [...],
  "retention_script": {...},
  "internal_notes": [...]
}
```

但页面上必须显示：

```text
模式：本地模板兜底，LLM 未成功返回
```

不要冒充 LLM。

---

## 十二、agent.py 要求

实现一个轻量智能体编排类，不要引入 Agent 框架。

```python
class ClientSaviorAgent:
    def __init__(self, policies: list[dict]):
        self.policies = policies

    def run(self, complaint: str, profile: CustomerProfile, use_llm: bool = True) -> AgentResult:
        # 1. 本地召回 top 5
        # 2. 如果 use_llm 且 API Key 存在，则调用 LLM
        # 3. LLM 成功：mode = "llm"
        # 4. LLM 失败：mode = "fallback"
        # 5. 返回统一 AgentResult
```

注意：即使页面上有“启用 LLM”开关，默认也必须开启。因为 LLM 是核心卖点。

---

## 十三、app.py 页面要求

使用 Streamlit 实现 3 个 Tab。

### 13.1 页面顶部

标题：

```text
The Client Savior｜客户拯救者
```

副标题：

```text
投诉秒变留人机会，政策套餐自动配对！
```

侧边栏显示：

- LLM 状态：已配置 / 未配置；
- 当前模型；
- Base URL；
- 超时时间；
- LLM 成功次数；
- 兜底次数。

### 13.2 Tab 1：AI 投诉处理

输入区：

- 文本框：投诉内容；
- 当前套餐月租：number_input，默认 39；
- 客户类型：selectbox；
- 网龄年数：number_input，默认 2；
- 是否有宽带：checkbox；
- 是否有换机需求：checkbox；
- 家庭移动号码数：number_input；
- 是否明确想离网：checkbox；
- 选择演示案例：selectbox + 一键填充按钮；
- 按钮：`生成 AI 挽留方案`。

输出区：

1. 使用 `st.success` 或 `st.warning` 显示模式：
   - `LLM 智能生成`；
   - `本地模板兜底`。

2. 展示 LLM 调用信息：
   - 模型；
   - 耗时；
   - 是否缓存；
   - 本地候选召回耗时可以不展示。

3. 展示客户分析：
   - 投诉类型；
   - 情绪；
   - 风险等级；
   - 关键诉求；
   - 摘要。

4. 展示推荐政策 Top 3：
   - 用 `st.expander` 或卡片；
   - 显示 LLM 推荐理由；
   - 显示本地匹配分和本地匹配原因；
   - 显示权益、条件、风险提醒。

5. 展示挽留话术：
   - 安抚开场；
   - 方案介绍；
   - 风险说明；
   - 下一步引导。

6. 展示内部提醒。

### 13.3 Tab 2：管理看板

用 `st.session_state` 统计：

- total_cases；
- high_risk_cases；
- llm_success_count；
- fallback_count；
- avg_elapsed_seconds；
- complaint_type_counter；
- policy_counter。

显示：

- st.metric；
- st.bar_chart；
- 明细表。

### 13.4 Tab 3：政策库

- 搜索框；
- 分类筛选；
- 展示所有政策卡；
- 每张卡展示：适用场景、权益、办理条件、风险提醒、话术提示。

---

## 十四、README.md 要求

README 写清楚：

```bash
pip install -r requirements.txt
cp .env.example .env
# 填写 DASHSCOPE_API_KEY
streamlit run app.py
```

并说明：

- 有 API Key：使用 LLM 生成智能方案；
- 无 API Key：自动本地模板兜底；
- 本项目为培训 Demo，不连接真实 CRM/BOSS 系统；
- 办理资格与最终政策以业务系统为准。

---

## 十五、实现细节约束

请严格遵守：

1. 不要安装重型依赖；
2. 不要使用本地大模型；
3. 不要在运行时解析 docx/xlsx；
4. 不要写复杂前后端分离；
5. 不要做数据库；
6. 不要写登录系统；
7. 不要虚构政策卡以外的政策；
8. LLM 失败必须兜底；
9. 页面必须突出 LLM 是核心：显示模型、耗时、AI 生成标签；
10. 每次生成结果要更新管理看板。

---

## 十六、验收标准

生成的项目必须满足：

- 执行 `streamlit run app.py` 可启动；
- 无 API Key 时也能完整操作；
- 有 API Key 时默认调用 LLM；
- LLM 成功时页面显示 `LLM 智能生成`；
- LLM 失败时页面显示 `本地模板兜底`；
- 单次等待超过 8–10 秒自动兜底；
- 生成结果包含客户分析、Top 3 政策、话术、内部提醒；
- 管理看板能统计本次演示结果；
- 政策库页面可搜索和查看。

请直接输出完整项目代码文件，不要只给思路。
