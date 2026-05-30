import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from typing import List


def export_leads_to_excel(leads: List[dict], output: io.BytesIO):
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads Report"

    headers = [
        "ID", "Company Name", "Website", "Phone", "Email",
        "Contact Person", "Position", "Industry", "Company Size",
        "Location", "Source", "Score", "Status", "Validation Status",
        "Email Subject", "Email Draft", "Checked", "Sent At",
        "Created At", "Updated At",
    ]

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    score_fills = {
        "high": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        "medium": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        "low": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    }

    for row_idx, lead in enumerate(leads, 2):
        ws.cell(row=row_idx, column=1, value=lead.get("id"))
        ws.cell(row=row_idx, column=2, value=lead.get("company_name"))
        ws.cell(row=row_idx, column=3, value=lead.get("website"))
        ws.cell(row=row_idx, column=4, value=lead.get("phone"))
        ws.cell(row=row_idx, column=5, value=lead.get("email"))
        ws.cell(row=row_idx, column=6, value=lead.get("contact_person"))
        ws.cell(row=row_idx, column=7, value=lead.get("position"))
        ws.cell(row=row_idx, column=8, value=lead.get("industry"))
        ws.cell(row=row_idx, column=9, value=lead.get("company_size"))
        ws.cell(row=row_idx, column=10, value=lead.get("location"))
        ws.cell(row=row_idx, column=11, value=lead.get("source"))
        ws.cell(row=row_idx, column=12, value=lead.get("score"))
        ws.cell(row=row_idx, column=13, value=lead.get("status"))
        ws.cell(row=row_idx, column=14, value=lead.get("validation_status"))
        ws.cell(row=row_idx, column=15, value=lead.get("email_subject"))
        ws.cell(row=row_idx, column=16, value=lead.get("email_draft", "")[:200])
        ws.cell(row=row_idx, column=17, value="Yes" if lead.get("checked") else "No")
        ws.cell(row=row_idx, column=18, value=lead.get("sent_at"))
        ws.cell(row=row_idx, column=19, value=lead.get("created_at"))
        ws.cell(row=row_idx, column=20, value=lead.get("updated_at"))

        score = lead.get("score", 0)
        score_cell = ws.cell(row=row_idx, column=12)
        if score >= 75:
            score_cell.fill = score_fills["high"]
        elif score >= 50:
            score_cell.fill = score_fills["medium"]
        else:
            score_cell.fill = score_fills["low"]

        for col in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col).border = thin_border

    column_widths = [6, 30, 25, 18, 30, 25, 20, 20, 12, 20, 15, 8, 15, 15, 30, 50, 8, 20, 20, 20]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width

    ws.auto_filter.ref = f"A1:T{len(leads) + 1}"
    ws.freeze_panes = "A2"

    wb.save(output)
