"""导出 Markdown / Word(.docx) 简历文件。

Word 导出优先使用 python-docx（排版更规范）；未安装时自动降级为
内置的轻量 docx 生成器（docx_min.py，仅用标准库）。
"""


def _split_bullets(text: str):
    """把多行描述拆成要点列表，去掉行首的 - • · 等符号。"""
    out = []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-•·　 ").strip()
        if line:
            out.append(line)
    return out


def _contact_line(basic: dict) -> str:
    parts = []
    for k in ("phone", "email", "city", "links"):
        v = (basic.get(k) or "").strip()
        if v:
            parts.append(v)
    return " | ".join(parts)


def _sections(resume: dict):
    """按标准顺序产出 (标题, [(主标题行, 要点列表), ...]) 序列。"""
    summary = (resume.get("summary") or "").strip()
    if summary:
        yield "职业简介", [(summary, [])]
    for title, key, head_keys in (
        ("工作经历", "experiences", ("company", "position")),
        ("项目经历", "projects", ("name", "role")),
        ("教育经历", "educations", ("school", "major", "degree")),
    ):
        items = resume.get(key) or []
        if not items:
            continue
        rows = []
        for it in items:
            head = " ".join(
                x for x in [it.get(k) or "" for k in head_keys] + [it.get("period") or ""] if x
            )
            rows.append((head, _split_bullets(it.get("description") or "")))
        yield title, rows
    skills = (resume.get("skills") or "").strip()
    if skills:
        yield "技能特长", [("", [s.lstrip("-•·　 ").strip() for s in skills.splitlines() if s.strip()])]
    sa = (resume.get("self_assessment") or "").strip()
    if sa:
        yield "自我评价", [(sa, [])]


def build_markdown(resume: dict) -> str:
    b = resume.get("basic", {})
    lines = [f"# {b.get('name') or '姓名'}"]
    contact = _contact_line(b)
    if contact:
        lines.append(contact)
    target = (b.get("target") or "").strip()
    if target:
        lines.append(f"\n> 求职意向：{target}")
    lines.append("")
    for title, rows in _sections(resume):
        lines.append(f"## {title}")
        lines.append("")
        for head, bullets in rows:
            if head:
                lines.append(f"**{head}**")
            for bl in bullets:
                lines.append(f"- {bl}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_docx_bytes(resume: dict) -> bytes:
    """生成 .docx 文件字节：优先 python-docx，缺失时用内置轻量生成器。"""
    try:
        from . import docx_py
        return docx_py.build_docx_bytes(resume)
    except ImportError:
        from . import docx_min
        return docx_min.build_docx_bytes(resume)
