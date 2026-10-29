"""Convert REPORT.md into a formatted PDF (title page + body) with reportlab.

usage: .venv/bin/pip install reportlab && .venv/bin/python scripts/md2pdf.py REPORT.md REPORT.pdf
(uses the Arial / Courier New fonts that ship with macOS)
"""
import re
import sys
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

SUP = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", SUP + "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", SUP + "Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", SUP + "Arial Italic.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", SUP + "Arial Bold Italic.ttf"))
pdfmetrics.registerFont(TTFont("ArialUni", SUP + "Arial Unicode.ttf"))
pdfmetrics.registerFont(TTFont("Mono", SUP + "Courier New.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic",
                              boldItalic="Arial-BoldItalic")

INK = colors.HexColor("#1f2937")
ACCENT = colors.HexColor("#1e3a8a")
MUTED = colors.HexColor("#6b7280")
RULE = colors.HexColor("#d1d5db")
HEAD_BG = colors.HexColor("#e8edf7")
CODE_BG = colors.HexColor("#f3f4f6")

body = ParagraphStyle("body", fontName="Arial", fontSize=10, leading=14.2, textColor=INK, spaceAfter=6)
cell = ParagraphStyle("cell", parent=body, fontSize=8.6, leading=11, spaceAfter=0)
cell_head = ParagraphStyle("cellh", parent=cell, fontName="Arial-Bold", textColor=ACCENT)
h2 = ParagraphStyle("h2", fontName="Arial-Bold", fontSize=14.5, leading=18, textColor=ACCENT, spaceBefore=14,
                    spaceAfter=7)
h3 = ParagraphStyle("h3", fontName="Arial-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=9,
                    spaceAfter=4)
code = ParagraphStyle("code", fontName="Mono", fontSize=8.6, leading=11.5, textColor=INK, backColor=CODE_BG,
                      borderPadding=(6, 6, 6, 6), spaceBefore=4, spaceAfter=10, leftIndent=6, rightIndent=6)
title = ParagraphStyle("title", fontName="Arial-Bold", fontSize=26, leading=32, textColor=ACCENT,
                       alignment=TA_CENTER, spaceAfter=10)
subtitle = ParagraphStyle("subtitle", fontName="Arial", fontSize=13, leading=18, textColor=MUTED,
                          alignment=TA_CENTER, spaceAfter=4)
center = ParagraphStyle("center", parent=body, alignment=TA_CENTER)


def inline(text):
    """Markdown inline syntax -> reportlab mini-HTML."""
    t = escape(text)
    t = re.sub(r"`([^`]+)`", r'<font name="Mono" size="8.8">\1</font>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"(https?://[^\s<)]+)", r'<link href="\1" color="#1e3a8a">\1</link>', t)
    return t.replace("→", '<font name="ArialUni">→</font>').replace("≥", '<font name="ArialUni">≥</font>')


def table(rows, width):
    header, data = rows[0], rows[1:]
    n = len(header)
    # wide tables get a smaller font so they fit the page width
    size = 8.6 if n <= 7 else 7.2
    c_style = ParagraphStyle("c", parent=cell, fontSize=size, leading=size * 1.28)
    h_style = ParagraphStyle("ch", parent=cell_head, fontSize=size, leading=size * 1.28)
    # column widths proportional to the longest text in each column, clamped
    lens = [max(len(re.sub(r"[*`]", "", r[i])) if i < len(r) else 0 for r in rows) for i in range(n)]
    lens = [min(max(l, 6), 60) for l in lens]
    widths = [width * l / sum(lens) for l in lens]
    # never narrower than the longest single word in the column (avoids "Ro/utin/g" breaks)
    words = [max((pdfmetrics.stringWidth(w, "Arial-Bold", size) for r in rows if i < len(r)
                  for w in re.sub(r"[*`]", "", r[i]).split()), default=20) + 9 for i in range(n)]
    if sum(words) > width:  # cannot honour every word width: shrink proportionally
        words = [w * width / sum(words) for w in words]
    for _ in range(5):
        short = [i for i in range(n) if widths[i] < words[i]]
        if not short:
            break
        need = sum(words[i] - widths[i] for i in short)
        for i in short:
            widths[i] = words[i]
        spare = [i for i in range(n) if i not in short and widths[i] > words[i]]
        total_spare = sum(widths[i] - words[i] for i in spare) or 1
        for i in spare:
            widths[i] -= need * (widths[i] - words[i]) / total_spare
    cells = [[Paragraph(inline(c), h_style) for c in header]]
    cells += [[Paragraph(inline(r[i]) if i < len(r) else "", c_style) for i in range(n)] for r in data]
    tb = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [tb, Spacer(1, 8)]


def bullets(items, ordered):
    """items: list of (text, [subitems])."""
    out = []
    for text, subs in items:
        parts = [Paragraph(inline(text), ParagraphStyle("li", parent=body, spaceAfter=2))]
        if subs:
            parts.append(ListFlowable(
                [ListItem(Paragraph(inline(s), ParagraphStyle("li2", parent=body, spaceAfter=1)), leftIndent=12)
                 for s in subs], bulletType="bullet", start="◦", leftIndent=12, bulletFontName="ArialUni",
                bulletFontSize=9))
        out.append(ListItem(parts, leftIndent=14))
    kw = dict(bulletType="1", bulletFormat="%s.") if ordered else dict(bulletType="bullet", start="•")
    return [ListFlowable(out, leftIndent=14, bulletFontName="Arial", bulletFontSize=9.5, **kw), Spacer(1, 4)]


def parse(md, width):
    """Return (title_text, team_rows, repo_lines, body_flowables)."""
    lines = md.splitlines()
    title_text, team, front, story = "", [], [], []
    i, in_front = 0, True
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            title_text = ln[2:].strip()
            i += 1
            continue
        if ln.startswith("## "):
            in_front = False
        if in_front:
            if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i + 1]):
                i += 2
                while i < len(lines) and lines[i].startswith("|"):
                    team.append([c.strip() for c in lines[i].strip("|").split("|")])
                    i += 1
                continue
            if ln.strip() and not ln.startswith("**Team"):
                front.append(ln.strip())
            i += 1
            continue

        if ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:]), h2))
        elif ln.startswith("### "):
            story.append(Paragraph(inline(ln[4:]), h3))
        elif ln.startswith("```"):
            buf = []
            i += 1
            while not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            story.append(Preformatted("\n".join(buf), code))
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| :]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            story.extend(table(rows, width))
            continue
        elif re.match(r"^(\* |\d+\. )", ln):
            ordered = bool(re.match(r"^\d+\. ", ln))
            items = []
            while i < len(lines) and (re.match(r"^(\* |\d+\. )", lines[i]) or re.match(r"^\s{2,}\* ", lines[i])):
                cur = lines[i]
                if re.match(r"^\s{2,}\* ", cur):
                    items[-1][1].append(cur.strip()[2:])
                else:
                    items.append((re.sub(r"^(\* |\d+\. )", "", cur), []))
                i += 1
            story.extend(bullets(items, ordered))
            continue
        elif ln.strip():
            para = [ln.strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||\* |\d+\. |```)", lines[i + 1]):
                i += 1
                para.append(lines[i].strip())
            story.append(Paragraph(inline(" ".join(para)), body))
        i += 1
    return title_text, team, front, story


def main(src, dst):
    md = open(src, encoding="utf-8").read()
    margin = 20 * mm
    width = A4[0] - 2 * margin
    title_text, team, front, story = parse(md, width)
    name, _, sub = title_text.partition(":")

    def on_page(canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setFont("Arial", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin, 12 * mm, "Multi-Agent Academic Helpdesk: Evaluation Report")
        canvas.drawRightString(A4[0] - margin, 12 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.line(margin, 15 * mm, A4[0] - margin, 15 * mm)
        canvas.restoreState()

    cover = [Spacer(1, 55 * mm), Paragraph(inline(name.strip()), title),
             Paragraph(inline(sub.strip() or ""), subtitle),
             Paragraph("Google ADK · Ollama · ChromaDB RAG", subtitle), Spacer(1, 18 * mm),
             Paragraph("<b>Team members</b>", ParagraphStyle("tm", parent=center, fontSize=11.5, textColor=ACCENT))]
    tm = Table([[Paragraph(inline(a), ParagraphStyle("tn", parent=body, fontSize=11)),
                 Paragraph(inline(b), ParagraphStyle("tr", parent=body, fontSize=11, fontName="Mono"))]
                for a, b in team], colWidths=[70 * mm, 35 * mm], hAlign="CENTER")
    tm.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    cover += [Spacer(1, 4), tm, Spacer(1, 20 * mm)]
    cover += [Paragraph(inline(f), ParagraphStyle("fr", parent=center, fontSize=9, textColor=MUTED)) for f in front]
    cover += [Spacer(1, 4), Paragraph(date.today().strftime("%B %Y"),
                                      ParagraphStyle("dt", parent=center, fontSize=9, textColor=MUTED)),
              PageBreak()]

    # keep each heading with the flowable that follows it
    merged, j = [], 0
    while j < len(story):
        f = story[j]
        if isinstance(f, Paragraph) and f.style.name in ("h2", "h3") and j + 1 < len(story):
            merged.append(KeepTogether([f, story[j + 1]]))
            j += 2
        else:
            merged.append(f)
            j += 1

    doc = SimpleDocTemplate(dst, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=18 * mm,
                            bottomMargin=22 * mm, title="Multi-Agent Academic Helpdesk: Evaluation Report",
                            author="B. Arin Patel, B. Siddardha, A. D. Bhojwani, K. S. Dayma")
    doc.build(cover + merged, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
