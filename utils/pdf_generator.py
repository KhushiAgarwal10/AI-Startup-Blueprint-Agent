"""
utils/pdf_generator.py – Convert a markdown blueprint string to a
                          downloadable PDF using fpdf2.
"""

import re
import textwrap
from fpdf import FPDF, XPos, YPos


class BlueprintPDF(FPDF):
    """Custom FPDF subclass with branded header and footer."""

    def __init__(self, startup_name: str = "Startup Blueprint"):
        super().__init__()
        self.startup_name = startup_name
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_fill_color(30, 64, 175)   # deep blue
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 2)
        self.cell(210, 10, "Startup Blueprint Generator  |  Powered by IBM Granite",
                  align="C")
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _strip_markdown_inline(text: str) -> str:
    """Remove inline markdown (bold, italic, code) for plain-text PDF."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"`(.+?)`",       r"\1", text)
    text = re.sub(r"~~(.+?)~~",     r"\1", text)
    return text


def markdown_to_pdf(blueprint_md: str, startup_name: str = "My Startup") -> bytes:
    """
    Convert a markdown-formatted blueprint string to PDF bytes.

    Args:
        blueprint_md: Full blueprint text in markdown.
        startup_name: Used in the document title.

    Returns:
        Raw PDF bytes ready to send as a file download.
    """
    pdf = BlueprintPDF(startup_name=startup_name)
    pdf.add_page()

    # Title page block
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 64, 175)
    pdf.ln(6)
    pdf.multi_cell(0, 10, startup_name, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 8, "Complete Startup Blueprint", align="C")
    pdf.ln(4)
    pdf.set_draw_color(30, 64, 175)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    lines = blueprint_md.split("\n")
    for line in lines:
        raw = line.rstrip()

        # H2 section headings  (## Heading)
        if raw.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(30, 64, 175)
            pdf.set_fill_color(237, 242, 255)
            heading_text = _strip_markdown_inline(raw[3:])
            pdf.multi_cell(0, 8, heading_text, fill=True,
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        # H3 sub-headings  (### Heading)
        elif raw.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(55, 65, 81)
            pdf.multi_cell(0, 7, _strip_markdown_inline(raw[4:]),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

        # Horizontal rule
        elif raw.startswith("---") and len(raw.strip("-")) == 0:
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.3)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(2)

        # Bullet points
        elif raw.startswith("- ") or raw.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            text = _strip_markdown_inline(raw[2:])
            # Indent bullet
            pdf.set_x(20)
            pdf.multi_cell(0, 6, f"\u2022  {text}",
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Numbered list
        elif re.match(r"^\d+\.\s", raw):
            pdf.set_font("Helvetica", "", 10)
            text = _strip_markdown_inline(raw)
            pdf.set_x(20)
            pdf.multi_cell(0, 6, text,
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Bold-only line (acts as mini-heading)
        elif raw.startswith("**") and raw.endswith("**"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, _strip_markdown_inline(raw),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Empty line → small gap
        elif raw == "":
            pdf.ln(2)

        # Regular paragraph text
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            clean = _strip_markdown_inline(raw)
            # Wrap very long lines
            for chunk in textwrap.wrap(clean, width=110) or [""]:
                pdf.multi_cell(0, 6, chunk,
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
