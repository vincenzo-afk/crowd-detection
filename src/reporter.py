"""
Incident Report Generator — PDF and CSV exports.
"""

import os
import datetime
import csv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import REPORT_DIR


class ReportGenerator:
    def __init__(self, session_id: str):
        self.session_id = session_id
        os.makedirs(REPORT_DIR, exist_ok=True)

    def generate_pdf(self, timeline_text: str, metrics_summary: dict) -> str:
        """Generate a PDF incident report. Returns file path."""
        out = os.path.join(REPORT_DIR, f"incident_{self.session_id}.pdf")
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import cm

            doc = SimpleDocTemplate(out, pagesize=A4,
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("Title2", parent=styles["Title"],
                                          fontSize=20, textColor=colors.HexColor("#1a237e"))
            h2_style = ParagraphStyle("H2", parent=styles["Heading2"],
                                       textColor=colors.HexColor("#0d47a1"))
            body_style = styles["BodyText"]
            code_style = ParagraphStyle("Code", parent=styles["Code"],
                                         fontSize=8, leading=12)
            story = []
            story.append(Paragraph("CrowdSafe AI — Incident Report", title_style))
            story.append(Spacer(1, 0.4*cm))
            story.append(Paragraph(
                f"Session: {self.session_id} | "
                f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                body_style))
            story.append(Spacer(1, 0.5*cm))

            from src.llm_report import LLMReporter
            llm = LLMReporter()
            executive_summary = llm.generate_summary(timeline_text, metrics_summary)

            story.append(Paragraph("Executive Summary", h2_style))
            story.append(Paragraph(executive_summary, body_style))
            story.append(Spacer(1, 0.4*cm))

            story.append(Paragraph("Summary Metrics", h2_style))
            table_data = [["Metric", "Value"]] + [
                [k, str(v)] for k, v in metrics_summary.items()
            ]
            t = Table(table_data, colWidths=[8*cm, 8*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d47a1")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#e3f2fd")]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#bbdefb")),
                ("FONTSIZE", (0,0), (-1,-1), 10),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5*cm))

            story.append(Paragraph("Incident Timeline", h2_style))
            for line in timeline_text.split("\n"):
                story.append(Paragraph(line.replace(" ", "&nbsp;"), code_style))
            doc.build(story)
            print(f"[Report] PDF saved: {out}")
            return out
        except ImportError:
            print("[Report] reportlab not installed. Saving text report instead.")
            txt_out = out.replace(".pdf", ".txt")
            with open(txt_out, "w") as f:
                f.write(timeline_text)
            return txt_out
        except Exception as e:
            print(f"[Report] PDF error: {e}")
            return ""

    def export_csv(self, rows: list, headers: list) -> str:
        out = os.path.join(REPORT_DIR, f"metrics_{self.session_id}.csv")
        try:
            with open(out, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(rows)
            return out
        except Exception as e:
            print(f"[Report] CSV error: {e}")
            return ""
