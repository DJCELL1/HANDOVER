"""
PDF builder for architectural hardware project handover sheets.
Produces a consistent, single-format PDF for every project.
"""

from fpdf import FPDF
from datetime import datetime

# ---- Colours (RGB) ----
NAVY = (28, 42, 64)
ACCENT = (196, 122, 42)   # muted amber, reads well on print
LIGHT = (242, 244, 247)
MIDGREY = (110, 120, 132)
LINEGREY = (210, 215, 222)
TEXT = (33, 37, 41)

STATUS_COLOURS = {
    "ordered": (39, 110, 71),
    "delivered": (39, 110, 71),
    "installed": (39, 110, 71),
    "complete": (39, 110, 71),
    "closed": (39, 110, 71),
    "partial": (176, 122, 18),
    "in progress": (176, 122, 18),
    "pending": (176, 122, 18),
    "on order": (176, 122, 18),
    "back order": (168, 50, 50),
    "outstanding": (168, 50, 50),
    "open": (168, 50, 50),
    "not ordered": (168, 50, 50),
    "not installed": (168, 50, 50),
    "issue": (168, 50, 50),
}


def _status_colour(val):
    if not val:
        return MIDGREY
    return STATUS_COLOURS.get(str(val).strip().lower(), MIDGREY)


class HandoverPDF(FPDF):
    def __init__(self, meta):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.meta = meta
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=15, top=15, right=15)
        self.set_title(f"Handover - {meta.get('project_name','')}")

    def header(self):
        if self.page_no() == 1:
            return  # cover-style block drawn manually on page 1
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*MIDGREY)
        self.cell(0, 6, self.meta.get("project_name", ""), align="L")
        self.cell(0, 6, "Project Handover Sheet", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINEGREY)
        self.set_line_width(0.3)
        self.line(15, self.get_y() + 1, 195, self.get_y() + 1)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MIDGREY)
        gen = datetime.now().strftime("%d %b %Y")
        self.cell(0, 5, f"Generated {gen}", align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R")

    # ---- building blocks ----
    def title_block(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 38, "F")
        self.set_fill_color(*ACCENT)
        self.rect(0, 38, 210, 2, "F")
        self.set_xy(15, 10)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 18)
        self.multi_cell(180, 8, self.meta.get("project_name", "Untitled Project"))
        self.set_x(15)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(210, 216, 226)
        self.cell(180, 6, "Project Handover Sheet - Architectural Hardware")
        self.set_xy(0, 48)
        self.set_text_color(*TEXT)

    def section(self, label):
        if self.get_y() > 250:
            self.add_page()
        self.ln(2)
        self.set_fill_color(*NAVY)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10.5)
        self.cell(0, 7, f"  {label.upper()}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*TEXT)
        self.ln(2)

    def kv_grid(self, pairs, cols=2):
        """pairs: list of (label, value). Lays out in `cols` columns."""
        self.set_font("Helvetica", "", 9.5)
        col_w = (180) / cols
        i = 0
        for label, value in pairs:
            if i % cols == 0 and i != 0:
                self.ln(7)
            x = 15 + (i % cols) * col_w
            self.set_xy(x, self.get_y())
            self.set_text_color(*MIDGREY)
            self.set_font("Helvetica", "B", 8)
            self.cell(col_w, 4, str(label).upper(), new_x="LEFT", new_y="NEXT")
            self.set_x(x)
            self.set_text_color(*TEXT)
            self.set_font("Helvetica", "", 10)
            self.multi_cell(col_w - 4, 5, self._safe(value), new_x="LEFT", new_y="TOP")
            i += 1
        self.ln(9)

    @staticmethod
    def _safe(text):
        """Replace unicode characters that Helvetica/latin-1 can't encode."""
        if not text:
            return "-"
        text = str(text)
        replacements = {
            "‘": "'", "’": "'",   # smart single quotes
            "“": '"', "”": '"',   # smart double quotes
            "–": "-", "—": "-",   # en/em dash
            "•": "-", "‣": "-",   # bullet points
            "…": "...",                # ellipsis
            " ": " ",                  # non-breaking space
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def para(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*TEXT)
        self.multi_cell(0, 5, self._safe(text))
        self.ln(2)

    def data_table(self, headings, rows, widths, status_col=None):
        """Render a table. widths are relative weights summing to ~180mm total."""
        if not rows:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*MIDGREY)
            self.cell(0, 6, "Nothing recorded.", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*TEXT)
            self.ln(2)
            return

        total = sum(widths)
        col_w = [w / total * 180 for w in widths]

        # header row
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*LIGHT)
        self.set_text_color(*NAVY)
        self.set_draw_color(*LINEGREY)
        self.set_line_width(0.2)
        for h, w in zip(headings, col_w):
            self.cell(w, 7, f" {h}", border="B", fill=True)
        self.ln(7)

        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*TEXT)
        fill = False
        for row in rows:
            # measure tallest cell for this row
            line_h = 4.6
            heights = []
            for val, w in zip(row, col_w):
                txt = self._safe(val)
                n = self._count_lines(txt, w - 2)
                heights.append(n * line_h)
            row_h = max(max(heights), 6)

            if self.get_y() + row_h > 275:
                self.add_page()
                self.set_font("Helvetica", "B", 8)
                self.set_fill_color(*LIGHT)
                self.set_text_color(*NAVY)
                for h, w in zip(headings, col_w):
                    self.cell(w, 7, f" {h}", border="B", fill=True)
                self.ln(7)
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*TEXT)

            y0 = self.get_y()
            x = 15
            if fill:
                self.set_fill_color(248, 249, 251)
                self.rect(x, y0, 180, row_h, "F")
            for idx, (val, w) in enumerate(zip(row, col_w)):
                txt = self._safe(val)
                self.set_xy(x, y0 + 1)
                if status_col is not None and idx == status_col:
                    self.set_text_color(*_status_colour(val))
                    self.set_font("Helvetica", "B", 8.5)
                else:
                    self.set_text_color(*TEXT)
                    self.set_font("Helvetica", "", 8.5)
                self.multi_cell(w - 2, line_h, f" {txt}", new_x="LEFT", new_y="TOP")
                x += w
            self.set_xy(15, y0 + row_h)
            self.set_draw_color(*LINEGREY)
            self.line(15, y0 + row_h, 195, y0 + row_h)
            fill = not fill
        self.ln(3)

    def _count_lines(self, txt, w):
        self.set_font("Helvetica", "", 8.5)
        words = txt.split()
        if not words:
            return 1
        lines, cur = 1, ""
        for word in words:
            test = (cur + " " + word).strip()
            if self.get_string_width(test) > w:
                lines += 1
                cur = word
            else:
                cur = test
        return lines


def _is_open(status):
    """True if a status word means the item is not yet resolved."""
    if not status:
        return True
    return str(status).strip().lower() in {
        "open", "pending", "outstanding", "back order", "not ordered",
        "not installed", "partial", "in progress", "on order", "issue", ""
    }


def build_pdf(data, out_path):
    meta = data.get("meta", {})
    pdf = HandoverPDF(meta)
    pdf.add_page()
    pdf.title_block()

    # --- Project overview ---
    pdf.section("Project Overview")
    pdf.kv_grid([
        ("Project Number", meta.get("project_number")),
        ("Status", meta.get("status_pct")),
        ("Client / Builder", meta.get("client_builder")),
        ("Site Address", meta.get("site_address")),
        ("Outgoing PM", meta.get("outgoing_pm")),
        ("Incoming PM", meta.get("incoming_pm")),
        ("Handover Date", meta.get("handover_date")),
        ("Contract Ref", meta.get("contract_ref")),
    ], cols=2)

    # --- Handover summary ---
    if data.get("general_notes"):
        pdf.section("Handover Summary")
        pdf.para(data["general_notes"])

    # ----------------------------------------------------------------
    # SECTION 1 — What's still left to install
    # ----------------------------------------------------------------
    all_install = data.get("installation", [])
    not_done = [i for i in all_install if _is_open(i.get("status"))]
    done_count = len(all_install) - len(not_done)

    pdf.section(f"What's Left To Install  ({len(not_done)} areas outstanding, {done_count} complete)")
    if not_done:
        pdf.data_table(
            ["Area / Door", "Items", "Status", "Notes"],
            [[i.get("area_door"), i.get("items"), i.get("status"), i.get("notes")]
             for i in not_done],
            widths=[30, 50, 24, 56],
            status_col=2,
        )
    else:
        pdf.para("All areas recorded as installed.")

    if done_count and not_done:
        pdf.para(f"Already installed ({done_count} areas):")
        done = [i for i in all_install if not _is_open(i.get("status"))]
        pdf.data_table(
            ["Area / Door", "Items", "Status", "Notes"],
            [[i.get("area_door"), i.get("items"), i.get("status"), i.get("notes")]
             for i in done],
            widths=[30, 50, 24, 56],
            status_col=2,
        )

    # ----------------------------------------------------------------
    # SECTION 2 — Supply issues (back orders, missing gear)
    # ----------------------------------------------------------------
    all_orders = data.get("ordering", [])
    supply_issues = [o for o in all_orders if _is_open(o.get("status"))]
    all_deliveries = data.get("deliveries", [])
    pending_deliveries = [d for d in all_deliveries if _is_open(d.get("status"))]

    pdf.section(f"Supply Issues  ({len(supply_issues)} items not yet complete)")
    if supply_issues:
        pdf.data_table(
            ["Item / Description", "Supplier", "PO Ref", "ETA", "Status"],
            [[o.get("description"), o.get("supplier"), o.get("po_ref"),
              o.get("eta"), o.get("status")]
             for o in supply_issues],
            widths=[52, 28, 22, 22, 26],
            status_col=4,
        )
    else:
        pdf.para("No outstanding supply issues.")

    if pending_deliveries:
        pdf.para("Deliveries still pending:")
        pdf.data_table(
            ["Item / Description", "Location", "Expected Date", "Status"],
            [[d.get("description"), d.get("location"), d.get("date"), d.get("status")]
             for d in pending_deliveries],
            widths=[60, 34, 22, 24],
            status_col=3,
        )

    # All orders (full picture, reference)
    if all_orders:
        pdf.para(f"All orders ({len(all_orders)} total):")
        pdf.data_table(
            ["Item / Description", "Supplier", "PO Ref", "ETA", "Status"],
            [[o.get("description"), o.get("supplier"), o.get("po_ref"),
              o.get("eta"), o.get("status")]
             for o in all_orders],
            widths=[52, 28, 22, 22, 26],
            status_col=4,
        )

    # ----------------------------------------------------------------
    # SECTION 3 — Install dates & schedule
    # ----------------------------------------------------------------
    sch = data.get("schedule", {})
    pdf.section("Install Dates & Schedule")
    pdf.kv_grid([
        ("Schedule Revision", sch.get("revision")),
        ("Total Openings / Doors", sch.get("total_openings")),
        ("Total Line Items", sch.get("total_line_items")),
        ("Schedule Status", sch.get("status")),
    ], cols=2)
    if sch.get("notes"):
        pdf.para(sch["notes"])

    # All deliveries (for date reference)
    if all_deliveries:
        pdf.para("Delivery dates:")
        pdf.data_table(
            ["Item / Description", "Location", "Date", "Status"],
            [[d.get("description"), d.get("location"), d.get("date"), d.get("status")]
             for d in all_deliveries],
            widths=[60, 34, 22, 24],
            status_col=3,
        )

    # ----------------------------------------------------------------
    # SECTION 4 — Outstanding actions
    # ----------------------------------------------------------------
    actions = data.get("actions", [])
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions_sorted = sorted(
        actions,
        key=lambda a: priority_order.get(str(a.get("priority", "")).lower(), 3)
    )
    pdf.section(f"Outstanding Actions  ({len(actions)} items)")
    if actions_sorted:
        pdf.data_table(
            ["Action", "Who", "Due", "Priority"],
            [[a.get("action"), a.get("owner"), a.get("due"), a.get("priority")]
             for a in actions_sorted],
            widths=[90, 30, 22, 18],
        )
    else:
        pdf.para("No outstanding actions recorded.")

    # ----------------------------------------------------------------
    # SECTION 5 — Site requests & variations
    # ----------------------------------------------------------------
    all_requests = data.get("site_requests", [])
    open_requests = [s for s in all_requests if _is_open(s.get("status"))]
    if all_requests:
        pdf.section(f"Site Requests  ({len(open_requests)} open)")
        pdf.data_table(
            ["Date", "Request / Query", "Raised By", "Status", "Action / Owner"],
            [[s.get("date"), s.get("request"), s.get("raised_by"),
              s.get("status"), s.get("action")]
             for s in all_requests],
            widths=[18, 58, 24, 20, 30],
            status_col=3,
        )

    all_vars = data.get("variations", [])
    open_vars = [v for v in all_vars if _is_open(v.get("status"))]
    if all_vars:
        pdf.section(f"Variations  ({len(open_vars)} pending)")
        pdf.data_table(
            ["Ref", "Description", "Value", "Status"],
            [[v.get("ref"), v.get("description"), v.get("value"), v.get("status")]
             for v in all_vars],
            widths=[18, 76, 26, 20],
            status_col=3,
        )

    # ----------------------------------------------------------------
    # SECTION 6 — Key contacts
    # ----------------------------------------------------------------
    pdf.section("Key Contacts")
    pdf.data_table(
        ["Role", "Name", "Company", "Email / Phone"],
        [[c.get("role"), c.get("name"), c.get("company"),
          " / ".join(x for x in [c.get("email"), c.get("phone")] if x)]
         for c in data.get("contacts", [])],
        widths=[24, 28, 32, 56],
    )

    # ----------------------------------------------------------------
    # SECTION 7 — Financials
    # ----------------------------------------------------------------
    fin = data.get("financials", {})
    if any(fin.get(k) for k in ("contract_value", "claimed_to_date", "retention", "variations_value", "notes")):
        pdf.section("Financial Summary")
        pdf.kv_grid([
            ("Contract Value", fin.get("contract_value")),
            ("Claimed To Date", fin.get("claimed_to_date")),
            ("Retention", fin.get("retention")),
            ("Variations Value", fin.get("variations_value")),
        ], cols=2)
        if fin.get("notes"):
            pdf.para(fin["notes"])

    # ----------------------------------------------------------------
    # SECTION 8 — Correspondence log (reference only)
    # ----------------------------------------------------------------
    if data.get("email_log"):
        pdf.section("Correspondence Log")
        pdf.data_table(
            ["Date", "From", "Subject", "Summary"],
            [[e.get("date"), e.get("from"), e.get("subject"), e.get("summary")]
             for e in data.get("email_log", [])],
            widths=[18, 28, 44, 50],
        )

    pdf.output(out_path)
    return out_path


if __name__ == "__main__":
    sample = {
        "meta": {
            "project_name": "City Rail Link - Mt Eden Station",
            "project_number": "CRL-2024-118",
            "client_builder": "Link Alliance",
            "site_address": "Mt Eden Rd, Auckland",
            "status_pct": "65% - install underway",
            "outgoing_pm": "Sel",
            "incoming_pm": "Reshal",
            "handover_date": "23 Jun 2026",
            "contract_ref": "C39",
        },
        "general_notes": "Install underway on levels 1-2. Claim C39 lodged and awaiting certification. "
                         "Main risk is the back-ordered electric strikes from Allegion, ETA mid-July. "
                         "Site has flagged two door swing changes that need a schedule revision.",
        "contacts": [
            {"role": "Site Manager", "name": "John Reti", "company": "Link Alliance",
             "email": "j.reti@linkalliance.co.nz", "phone": "021 555 0192"},
            {"role": "Supplier", "name": "Allegion Orders", "company": "Allegion",
             "email": "orders@allegion.co.nz", "phone": ""},
        ],
        "schedule": {"revision": "Rev 6", "total_openings": "212", "total_line_items": "1,184",
                     "status": "Current - 2 changes pending",
                     "notes": "Rev 7 needed once L1 swing changes confirmed by site."},
        "ordering": [
            {"description": "Lockwood mortice locks (212no)", "supplier": "Allegion", "po_ref": "PO-4471",
             "order_date": "12 Mar 26", "eta": "Delivered", "status": "Ordered"},
            {"description": "Electric strikes 24V (44no)", "supplier": "Allegion", "po_ref": "PO-4490",
             "order_date": "02 Apr 26", "eta": "15 Jul 26", "status": "Back order"},
            {"description": "Door closers TS93 (180no)", "supplier": "Dormakaba", "po_ref": "PO-4502",
             "order_date": "18 Apr 26", "eta": "Delivered", "status": "Ordered"},
        ],
        "deliveries": [
            {"description": "Mortice locks + furniture", "location": "Site container", "date": "20 May 26", "status": "Delivered"},
            {"description": "Electric strikes", "location": "Awaiting", "date": "TBC", "status": "Pending"},
        ],
        "installation": [
            {"area_door": "L1 D101-145", "items": "Locks, closers, furniture", "status": "Installed", "notes": "Signed off"},
            {"area_door": "L2 D201-260", "items": "Locks, closers", "status": "In progress", "notes": "Closers pending adjust"},
            {"area_door": "L1 Access doors", "items": "Electric strikes", "status": "Not installed", "notes": "Awaiting back order"},
        ],
        "site_requests": [
            {"date": "11 Jun 26", "request": "Change D118 + D119 to outward swing, revise hardware",
             "raised_by": "J Reti", "status": "Open", "action": "Revise schedule - Sel"},
            {"date": "05 Jun 26", "request": "Confirm finish on level 2 pulls (SSS vs PSS)",
             "raised_by": "J Reti", "status": "Closed", "action": "Confirmed SSS"},
        ],
        "variations": [
            {"ref": "VO-07", "description": "Additional 6no doors to plant room", "value": "$8,420", "status": "Pending"},
            {"ref": "VO-05", "description": "Upgrade to fire-rated closers L1", "value": "$3,110", "status": "Complete"},
        ],
        "actions": [
            {"action": "Chase Allegion on electric strike ETA", "owner": "Reshal", "due": "30 Jun", "priority": "High"},
            {"action": "Issue Rev 7 schedule after swing confirmation", "owner": "Sel", "due": "27 Jun", "priority": "High"},
            {"action": "Follow up C39 certification", "owner": "Reshal", "due": "04 Jul", "priority": "Medium"},
        ],
        "financials": {"contract_value": "$486,000", "claimed_to_date": "$310,000",
                       "retention": "$24,300", "variations_value": "$11,530",
                       "notes": "Claim C39 covers up to end May. C40 due end June."},
        "email_log": [
            {"date": "11 Jun 26", "from": "J Reti", "subject": "Door swing changes L1",
             "summary": "Site requesting D118/119 swing reversed. Needs schedule revision."},
            {"date": "02 Apr 26", "from": "Allegion", "subject": "PO-4490 confirmation",
             "summary": "Electric strikes on back order, ETA mid July."},
        ],
    }
    build_pdf(sample, "/home/claude/handover/sample_output.pdf")
    print("PDF written")
