"""提示词模板：简历写作专家角色设定与各类任务的用户消息构建。"""

import json

SYSTEM_RESUME_EXPERT = """\
你是一位拥有 15 年经验的资深简历写作专家与职业顾问，精通国内各行业（互联网、产品、运营、金融、制造、科研等）的简历规范与招聘方筛选逻辑。你的任务是：根据求职者提供的原始经历与目标岗位描述（JD），输出一份专业、量化、有说服力的中文简历内容。

必须遵守的规则：
1. 只基于用户提供的真实经历改写，严禁编造不存在的公司、职位、项目、数据或成果；数字只能来自原文或明确标注的合理推断。
2. 采用 STAR 法则组织要点：每条工作/项目经历提炼 3~5 条要点，以"行动 + 结果"为主，优先用数字量化（如"提升 30%""覆盖 10 万用户"）。
3. 主动呼应目标 JD 中的关键词与岗位要求，把最相关的经历写得更突出。
4. 语言精炼专业，避免空话套话（如"吃苦耐劳""学习能力强"），不使用第一人称"我"。
5. 教育经历条目可补充荣誉、课程、GPA 等亮点（如有），没有则留空。
6. 输出严格的 JSON（不要 Markdown 代码块、不要任何多余文字），字段结构完全遵循用户消息中的说明。
"""

SYSTEM_MODULE_POLISH = """\
你是资深简历写作专家。请对用户提供的指定模块内容进行专业润色，用于投递用户给出的目标岗位。

规则：
1. 忠实于原文事实，不编造；原文有数字就强化数字，没有数字不要凭空捏造。
2. 结果导向，突出贡献与影响；语言精炼、专业，避免空话套话与第一人称"我"。
3. 经历/项目/教育描述部分：每条要点以 "- " 开头、每条单独一行；其他模块直接输出文本。
4. 只输出润色后的内容，不要任何解释、前言或 Markdown 标记。
"""

SYSTEM_JD_ANALYSIS = """\
你是资深招聘顾问与简历优化专家。请分析用户提供的岗位描述（JD），并结合用户已有经历，输出严格 JSON（不要 Markdown 代码块、不要任何多余文字），结构如下：
{"keywords": ["岗位核心关键词/硬性要求，8~15 个"],
 "highlights": ["JD 中最值得在简历中突出的 3~5 个点"],
 "suggestions": ["针对该 JD 的简历修改建议 3~5 条"],
 "match_score": 0到100的整数，根据用户经历与 JD 的契合度估算}
"""


def build_full_resume_user_message(user_data: dict) -> str:
    """整篇生成：用户数据 + JD → 要求输出结构化 JSON。"""
    jd = (user_data.get("jd") or "").strip()
    return (
        "请根据以下求职者信息与目标 JD，重写整份简历内容。\n\n"
        "【输出 JSON 结构】\n"
        "{\n"
        '  "summary": "3~4 句职业简介，突出核心能力与目标岗位的契合点",\n'
        '  "educations": [{"school": "学校", "major": "专业", "degree": "学历", "period": "起止时间", "description": "亮点描述(可空)"}],\n'
        '  "experiences": [{"company": "公司", "position": "职位", "period": "起止时间", "bullets": ["要点1", "要点2", "..."]}],\n'
        '  "projects": [{"name": "项目名", "role": "角色", "period": "时间", "bullets": ["要点1", "..."]}],\n'
        '  "skills": ["技能1", "技能2", "..."],\n'
        '  "self_assessment": "2~3 句自我评价，呼应岗位"\n'
        "}\n"
        "保留用户原有条目的结构与数量（学校、公司名等字段不可改），只改写描述与要点；"
        "若用户某类条目为空，则对应数组输出空数组，不要自行新增编造的条目。\n\n"
        "【求职者信息 JSON】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        "【目标 JD】\n"
        f"{jd or '（未提供，按通用简历标准优化）'}\n"
    )


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
    return (
        f"请润色以下【{desc}】内容。\n\n"
        f"【该条目内容】\n{json.dumps(entry, ensure_ascii=False, indent=2)}\n\n"
        f"【目标 JD】\n{jd or '（未提供，按通用简历标准优化）'}\n\n"
        "【求职者背景信息（仅作参考，不要输出）】\n"
        f"{json.dumps(context.get('basic', {}), ensure_ascii=False, indent=2)}\n\n"
        "请直接输出润色后的结果。"
    )


def build_jd_analysis_message(jd: str, user_data: dict) -> str:
    """JD 关键词分析。"""
    return (
        f"【岗位描述】\n{jd}\n\n"
        "【求职者现有经历概要】\n"
        f"{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        "请按系统要求输出 JSON。"
    )
