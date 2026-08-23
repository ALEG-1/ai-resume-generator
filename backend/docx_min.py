"""内置的轻量 .docx 生成器（仅用标准库 zipfile），未安装 python-docx 时兜底。

生成的是符合 OOXML 规范的 Word 文档（微软雅黑字体、居中标题、圆点要点）。
"""

import io
import zipfile
from xml.sax.saxutils import escape

from .export import _contact_line, _sections

_FONT = "微软雅黑"


def _p(text: str, bold: bool = False, size: int = 21, center: bool = False, bullet: bool = False) -> str:
    """生成一个段落 XML。size 单位：半磅（21 = 10.5pt，28 = 14pt，44 = 22pt）。"""
    if bullet:
        text = "• " + text
    rpr = f'<w:rPr><w:rFonts w:ascii="{_FONT}" w:eastAsia="{_FONT}" w:hAnsi="{_FONT}"/>'
    if bold:
        rpr += "<w:b/>"
    rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    run = f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    ppr = '<w:pPr><w:jc w:val="center"/></w:pPr>' if center else ""
    return f"<w:p>{ppr}{run}</w:p>"


def build_docx_bytes(resume: dict) -> bytes:
    b = resume.get("basic", {})
    body = [""]

    body.append(_p(b.get("name") or "姓名", bold=True, size=44, center=True))
    contact = _contact_line(b)
    if contact:
        body.append(_p(contact, center=True, size=21))
    target = (b.get("target") or "").strip()
    if target:
        body.append(_p(f"求职意向：{target}", center=True, size=21))

    for title, rows in _sections(resume):
        if not rows:
            continue
        body.append(_p(title, bold=True, size=28))
        for head, bullets in rows:
            if head:
                body.append(_p(head, bold=True, size=22))
            for bl in bullets:
                body.append(_p(bl, bullet=True, size=21))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}</w:body></w:document>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )

    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr>'
        f'<w:rFonts w:ascii="{_FONT}" w:eastAsia="{_FONT}" w:hAnsi="{_FONT}"/>'
        '<w:sz w:val="21"/><w:szCs w:val="21"/>'
        "</w:rPr></w:rPrDefault></w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        "</w:styles>"
    )

    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>简历</dc:title>"
        "</cp:coreProperties>"
    )

    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>ResumeGenerator</Application>"
        "</Properties>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
        z.writestr("word/styles.xml", styles)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    return buf.getvalue()
