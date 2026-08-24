"""提示词模板：简历写作专家角色设定与各类任务的用户消息构建。"""

import json

# ---------- 通用优秀要点示例（few-shot，供风格参考） ----------
EXCELLENT_BULLETS = """\
【优秀要点示例（仅作风格参考，请勿照抄）】
- 主导订单系统重构，通过缓存与异步化将核心接口 QPS 从 2k 提升至 8k，线上故障率下降 40%
- 搭建 Prometheus + Grafana 监控体系，告警响应时间缩短至 5 分钟内
- 从 0 到 1 搭建智能客服机器人，日均处理 10 万次对话，首响延迟 < 200ms
"""

SYSTEM_RESUME_EXPERT = f"""\
你是一位拥有 15 年经验的资深简历写作专家与职业顾问，精通国内各行业（互联网、产品、运营、金融、制造、科研等）的简历规范与
招聘方筛选逻辑。你的任务是：根据求职者提供的原始经历与目标岗位描述（JD），输出专业、量化、有说服力的中文简历内容。

必须遵守的规则：
1. 只基于用户提供的真实经历改写，严禁编造不存在的公司、职位、项目、数据或成果；数字只能来自原文或明确标注的合理推断。
2. 采用 STAR 法则组织要点：每条工作/项目经历提炼 3~5 条要点，以"行动 + 结果"为主，优先用数字量化。
3. 主动呼应目标 JD 中的关键词与岗位要求，把最相关的经历写得更突出。
4. 语言精炼专业，避免空话套话（如"吃苦耐劳""学习能力强"），不使用第一人称"我"。
5. 输出严格 JSON（不要 Markdown 代码块、不要任何多余文字），字段结构完全遵循用户消息中的说明。

{EXCELLENT_BULLETS}
"""

SYSTEM_MODULE_POLISH = f"""\
你是资深简历写作专家。请对用户提供的指定模块内容进行专业润色，用于投递用户给出的目标岗位。

规则：
1. 忠实于原文事实，不编造；原文有数字就强化数字，没有数字不要凭空捏造。
2. 结果导向，突出贡献与影响；语言精炼、专业，避免空话套话与第一人称"我"。
3. 经历/项目/教育描述部分：每条要点以 "- " 开头、单独一行；其他模块直接输出文本。
4. 只输出润色后的内容，不要任何解释、前言或 Markdown 标记。

{EXCELLENT_BULLETS}
"""

SYSTEM_JD_ANALYSIS = """\
你是资深招聘顾问与简历优化专家。请分析用户提供的岗位描述（JD），并结合用户已有经历，输出严格 JSON（不要 Markdown 代码块、不要任何多余文字），结构如下：
{"keywords": ["岗位核心关键词/硬性要求，8~15 个"],
 "highlights": ["JD 中最值得在简历中突出的 3~5 个点"],
 "suggestions": ["针对该 JD 的简历修改建议 3~5 条"],
 "match_score": 0到100的整数，根据用户经历与 JD 的契合度估算}
"""

SYSTEM_STAR_INTEGRATE = f"""\
你是资深简历写作专家。用户按 STAR 四要素（情境 Situation / 任务 Task / 行动 Action / 结果 Result）填写了一段经历素材，请将其整合为 3~5 条精炼要点，用于简历。

规则：
1. 只整合用户提供的素材，不得编造新的事实或数据；结果要素缺失时可用"提升了效率""缩短了周期"这类定性描述，但不要凭空给出具体数字。
2. 要点以"行动 + 结果"为主，语言精炼专业，避免空话与第一人称"我"。
3. 每条要点以 "- " 开头、单独一行；只输出要点，不要任何解释。

{EXCELLENT_BULLETS}
"""

SYSTEM_SCORE = """\
你是资深招聘官与简历评审专家。请从招聘方的角度评审用户提供的简历与目标岗位（JD）的匹配度，输出严格 JSON（不要 Markdown 代码块、不要任何多余文字）：
{"overall_score": 0到100的整数,
 "dimensions": [{"name": "维度名", "score": 0到100的整数, "comment": "一句话点评"}],
 "strengths": ["3~5 条优点"],
 "suggestions": ["按重要性排序的改进建议 3~6 条"]}
维度建议包含：内容完整性、量化程度、JD 匹配度、语言表达。评分要严格、有区分度，避免全部都是 90 分以上。
"""


def _jd_or_generic(user_data: dict) -> str:
    jd = (user_data.get("jd") or "").strip()
    return jd or "（未提供，按通用简历标准优化）"


# ---------- 分步生成：各模块的消息构建 ----------

def build_summary_message(user_data: dict) -> str:
    """第 1 步：职业简介。"""
    return (
        "请根据以下求职者信息与目标 JD，撰写 3~4 句【职业简介】（summary）。"
        "要求：突出经验年限、核心能力与代表成果，并呼应目标岗位的关键词；"
        "只使用用户提供的信息，不编造；不使用第一人称；直接输出简介文本，不要任何解释或 Markdown 标记。\n\n"
        "【求职者信息】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{_jd_or_generic(user_data)}\n"
    )


def build_entry_bullets_message(kind: str, entry: dict, context: dict) -> str:
    """工作/项目经历单条要点打磨。kind: experience | project | education。"""
    jd = (context.get("jd") or "").strip()
    labels = {
        "experience": "工作经历",
        "project": "项目经历",
        "education": "教育经历",
    }
    label = labels.get(kind, kind)
    star = entry.get("star") or {}
    star_text = ""
    filled = [v for v in star.values() if str(v or "").strip()]
    if filled:
        star_text = (
            "\n【用户按 STAR 填写的素材（须基于此整合，不得编造素材外的内容）】\n"
            f"情境：{star.get('situation') or '（未填）'}\n"
            f"任务：{star.get('task') or '（未填）'}\n"
            f"行动：{star.get('action') or '（未填）'}\n"
            f"结果：{star.get('result') or '（未填）'}\n"
        )
    return (
        "请为以下【" + label + "】条目打磨 3~5 条要点：以「行动 + 结果」为主，优先用数字量化，"
        "主动呼应目标 JD 关键词；只使用该条目提供的信息，不编造。"
        "每条要点以 \"- \" 开头、单独一行；只输出要点，不要任何解释。\n\n"
        f"【该条目信息】\n{json.dumps(entry, ensure_ascii=False, indent=2)}{star_text}\n\n"
        f"【目标 JD】\n{jd or '（未提供，按通用标准）'}\n"
    )


def build_skills_message(user_data: dict) -> str:
    """技能清单提炼。"""
    return (
        "请根据以下求职者信息与目标 JD，整理一份【技能清单】。"
        "要求：保留用户已填技能（可重新分组与措辞优化），并结合 JD 中明确要求的技能补充 2~4 项"
        "（仅限用户经历中体现的技能，严禁编造）；每行一项，直接输出，不要任何解释或 Markdown 标记。\n\n"
        "【求职者信息】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{_jd_or_generic(user_data)}\n"
    )


def build_self_message(user_data: dict) -> str:
    """自我评价。"""
    return (
        "请根据以下求职者信息与目标 JD，撰写 2~3 句【自我评价】。"
        "要求：突出职业态度与核心优势，呼应目标岗位；不使用第一人称；"
        "直接输出文本，不要任何解释或 Markdown 标记。\n\n"
        "【求职者信息】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{_jd_or_generic(user_data)}\n"
    )


# ---------- 模块润色 ----------

def build_module_polish_message(module: str, entry: dict, context: dict) -> str:
    """模块润色：单个条目/字段 + 背景 + JD。"""
    jd = (context.get("jd") or "").strip()
    desc = {
        "summary": "职业简介（summary）",
        "self_assessment": "自我评价（self_assessment）",
        "skills": "技能清单（skills，输出时用换行分隔各项）",
        "education": "教育经历条目（要点以 - 开头、每条一行，3~5 条）",
        "experience": "工作经历条目（要点以 - 开头、每条一行，3~5 条）",
        "project": "项目经历条目（要点以 - 开头、每条一行，3~5 条）",
    }.get(module, module)

    star = entry.get("star") or {}
    star_text = ""
    if any(str(v or "").strip() for v in star.values()):
        star_text = (
            "\n【用户按 STAR 填写的素材（须基于此整合，不得编造素材外的内容）】\n"
            f"情境：{star.get('situation') or '（未填）'}\n"
            f"任务：{star.get('task') or '（未填）'}\n"
            f"行动：{star.get('action') or '（未填）'}\n"
            f"结果：{star.get('result') or '（未填）'}\n"
        )
    return (
        f"请润色以下【{desc}】内容。\n\n"
        f"【该条目内容】\n{json.dumps(entry, ensure_ascii=False, indent=2)}{star_text}\n\n"
        f"【目标 JD】\n{jd or '（未提供，按通用简历标准优化）'}\n\n"
        "【求职者背景信息（仅作参考，不要输出）】\n"
        f"{json.dumps(context.get('basic', {}), ensure_ascii=False, indent=2)}\n\n"
        "请直接输出润色后的结果。"
    )


def build_star_integrate_message(entry: dict, context: dict) -> str:
    """STAR 四要素整合为要点。"""
    jd = (context.get("jd") or "").strip()
    star = entry.get("star") or {}
    return (
        "【该经历条目信息】\n"
        f"{json.dumps(entry, ensure_ascii=False, indent=2)}\n"
        "【STAR 素材】\n"
        f"情境：{star.get('situation') or '（未填）'}\n"
        f"任务：{star.get('task') or '（未填）'}\n"
        f"行动：{star.get('action') or '（未填）'}\n"
        f"结果：{star.get('result') or '（未填）'}\n\n"
        f"【目标 JD】\n{jd or '（未提供，按通用标准）'}\n\n"
        "请按系统要求输出整合后的要点。"
    )


# ---------- JD 分析 / 评分 ----------

def build_jd_analysis_message(jd: str, user_data: dict) -> str:
    """JD 关键词分析。"""
    return (
        f"【岗位描述】\n{jd}\n\n"
        "【求职者现有经历概要】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        "请按系统要求输出 JSON。"
    )


def build_score_message(resume: dict, jd: str) -> str:
    """简历评分。"""
    return (
        "【简历内容】\n"
        f"{json.dumps(resume, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{jd or '（未提供，按通用岗位标准评审）'}\n\n"
        "请按系统要求输出 JSON。"
    )


# ---------- 保留：整篇一次性生成（旧模式，已由分步生成取代，供参考/回滚） ----------

def build_full_resume_user_message(user_data: dict) -> str:
    """整篇生成：用户数据 + JD → 要求输出结构化 JSON。"""
    return (
        "请根据以下求职者信息与目标 JD，重写整份简历内容。\n\n"
        "【输出 JSON 结构】\n"
        "{\n"
        '  "summary": "3~4 句职业简介，突出核心能力与目标岗位的契合点",\n'
        '  "educations": [{"school": "学校", "major": "专业", "degree": "学历", '
        '"period": "起止时间", "description": "亮点描述(可空)"}],\n'
        '  "experiences": [{"company": "公司", "position": "职位", "period": "起止时间", "bullets": ["要点1", "要点2", "..."]}],\n'
        '  "projects": [{"name": "项目名", "role": "角色", "period": "时间", "bullets": ["要点1", "..."]}],\n'
        '  "skills": ["技能1", "技能2", "..."],\n'
        '  "self_assessment": "2~3 句自我评价，呼应岗位"\n'
        "}\n"
        "保留用户原有条目的结构与数量（学校、公司名等字段不可改），只改写描述与要点；"
        "若用户某类条目为空，则对应数组输出空数组，不要自行新增编造的条目。\n\n"
        "【求职者信息 JSON】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{_jd_or_generic(user_data)}\n"
    )
