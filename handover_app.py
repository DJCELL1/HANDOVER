"""
Architectural Hardware - Project Handover Generator
Run with:  streamlit run handover_app.py

What it does:
- One project per job, every job uses the same handover format
- Drop in emails (.eml / .msg) or paste text, builds a correspondence log
- Optional: auto-draft the handover sections from the emails using Claude
  (set ANTHROPIC_API_KEY in your environment to enable)
- Edit every section in editable tables
- Download a consistent PDF handover sheet
- Projects save locally so you can come back and update them
"""

import streamlit as st
import json
import os
from datetime import datetime

from email_parse import parse_upload, parse_pasted_text
from handover_pdf import build_pdf
from ai_draft import ai_draft

PROJECTS_DIR = "projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

st.set_page_config(page_title="Hardware Handover Generator", layout="wide")

EMPTY = {
    "meta": {
        "project_name": "", "project_number": "", "client_builder": "",
        "site_address": "", "status_pct": "", "outgoing_pm": "",
        "incoming_pm": "", "handover_date": datetime.now().strftime("%d %b %Y"),
        "contract_ref": "",
    },
    "general_notes": "",
    "contacts": [],
    "schedule": {"revision": "", "total_openings": "", "total_line_items": "", "status": "", "notes": ""},
    "ordering": [],
    "deliveries": [],
    "installation": [],
    "site_requests": [],
    "variations": [],
    "actions": [],
    "financials": {"contract_value": "", "claimed_to_date": "", "retention": "", "variations_value": "", "notes": ""},
    "email_log": [],
    "_emails_full": [],
}


def new_project():
    return json.loads(json.dumps(EMPTY))


def safe_name(name):
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip()
    return keep.replace(" ", "_") or "project"


def save_project(data):
    fn = os.path.join(PROJECTS_DIR, safe_name(data["meta"]["project_name"]) + ".json")
    with open(fn, "w") as f:
        json.dump(data, f, indent=2)
    return fn


def list_projects():
    return sorted(f for f in os.listdir(PROJECTS_DIR) if f.endswith(".json"))


def load_project(fn):
    with open(os.path.join(PROJECTS_DIR, fn)) as f:
        d = json.load(f)
    base = new_project()
    for k, v in base.items():
        if k not in d:
            d[k] = v
    return d


if "proj" not in st.session_state:
    st.session_state.proj = new_project()
proj = st.session_state.proj

with st.sidebar:
    st.header("Projects")
    files = list_projects()
    pick = st.selectbox("Open saved project", ["- new project -"] + files)
    c1, c2 = st.columns(2)
    if c1.button("Load", use_container_width=True) and pick != "- new project -":
        st.session_state.proj = load_project(pick)
        st.rerun()
    if c2.button("New", use_container_width=True):
        st.session_state.proj = new_project()
        st.rerun()
    st.divider()
    if st.button("Save project", type="primary", use_container_width=True):
        if proj["meta"]["project_name"].strip():
            fn = save_project(proj)
            st.success(f"Saved {os.path.basename(fn)}")
        else:
            st.error("Add a project name first")
    st.caption("Projects save to ./projects as JSON. Same format every job.")

st.title("Architectural Hardware - Project Handover")

tabs = st.tabs(["1. Emails", "2. Project details", "3. Hardware & orders",
                "4. Site & actions", "5. Generate PDF"])

with tabs[0]:
    st.subheader("Add emails for this job")

    st.info(
        "**Outlook users — drag-and-drop from Outlook does not work in a browser.**\n\n"
        "Use one of these methods instead:\n"
        "- **Paste email text** (easiest): open the email in Outlook, select all (Ctrl+A), copy (Ctrl+C), then paste below.\n"
        "- **Save as .msg file**: drag the email from Outlook onto your Desktop or a folder, then upload it here.\n"
        "- **Save as .eml file**: File → Save As → choose a folder, then upload the .eml file here."
    )

    tab_upload, tab_paste = st.tabs(["Upload file (.msg / .eml)", "Paste email text"])

    with tab_upload:
        up = st.file_uploader("Upload emails", type=["eml", "msg"], accept_multiple_files=True)
        if up and st.button(f"Parse {len(up)} email(s)"):
            added = 0
            for f in up:
                try:
                    parsed = parse_upload(f.name, f.read())
                    proj["_emails_full"].append(parsed)
                    proj["email_log"].append({"date": parsed["date"], "from": parsed["from"],
                                              "subject": parsed["subject"], "summary": ""})
                    added += 1
                except Exception as e:
                    st.warning(f"Could not parse {f.name}: {e}")
            st.success(f"Added {added} email(s). Now click **Fill in handover from emails** below.")

    with tab_paste:
        st.caption(
            "In Outlook: open the email, press Ctrl+A then Ctrl+C, and paste here. "
            "From/Date/Subject will be detected automatically if present."
        )
        pb = st.text_area("Paste full email text here", height=220, key="paste_body")
        if st.button("Parse & add pasted email"):
            if pb.strip():
                parsed = parse_pasted_text(pb)
                st.markdown("**Detected fields — correct if needed before adding:**")
                c1, c2 = st.columns(2)
                parsed["from"] = c1.text_input("From", parsed["from"], key="p_from")
                parsed["date"] = c2.text_input("Date", parsed["date"], key="p_date")
                parsed["subject"] = st.text_input("Subject", parsed["subject"], key="p_subj")
                if st.button("Confirm & add", key="paste_confirm"):
                    proj["_emails_full"].append(parsed)
                    proj["email_log"].append({"date": parsed["date"], "from": parsed["from"],
                                              "subject": parsed["subject"], "summary": ""})
                    st.success("Email added. Now click **Fill in handover from emails** below.")
                    st.rerun()
            else:
                st.warning("Paste some email text first.")

    st.divider()
    st.markdown("**Correspondence log** (edit summaries here, this goes on the PDF)")
    if proj["email_log"]:
        proj["email_log"] = st.data_editor(
            proj["email_log"], num_rows="dynamic", use_container_width=True, key="emlog",
            column_config={"date": "Date", "from": "From", "subject": "Subject", "summary": "Summary"})
    else:
        st.info("No emails yet.")

    if proj["_emails_full"]:
        with st.expander(f"View full text of {len(proj['_emails_full'])} parsed email(s)"):
            for e in proj["_emails_full"]:
                st.markdown(f"**{e['subject']}** - {e['from']} - {e['date']}")
                st.text(e["body"][:3000])
                st.divider()

    st.divider()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning(
            "**Auto-fill is not enabled.** To have Claude read your emails and fill in the "
            "entire handover automatically, add your `ANTHROPIC_API_KEY` in the app settings "
            "(Streamlit Cloud → App → Settings → Secrets)."
        )
    else:
        n = len(proj["_emails_full"])
        st.markdown("### Step 2 — Fill in the handover from your emails")
        st.caption(
            "Claude will read all your emails and fill in project details, contacts, orders, "
            "deliveries, installation status, actions, and more. You review and correct after."
        )
        if st.button(
            f"Fill in handover from {n} email(s)" if n else "Fill in handover from emails",
            type="primary",
            disabled=n == 0,
        ):
            with st.spinner("Reading emails and filling in the handover — this takes 20-30 seconds..."):
                try:
                    draft = ai_draft(proj["_emails_full"], proj["meta"])

                    # Apply meta fields (only overwrite blanks unless we have something better)
                    if draft.get("meta"):
                        for k, v in draft["meta"].items():
                            if v and not proj["meta"].get(k):
                                proj["meta"][k] = v

                    # Apply all sections
                    for k in ["ordering", "deliveries", "installation", "site_requests",
                               "variations", "actions", "contacts"]:
                        if draft.get(k):
                            proj[k] = draft[k]
                    if draft.get("general_notes"):
                        proj["general_notes"] = draft["general_notes"]
                    if draft.get("email_log"):
                        proj["email_log"] = draft["email_log"]
                    if draft.get("schedule"):
                        proj["schedule"].update({k: v for k, v in draft["schedule"].items() if v})
                    if draft.get("financials"):
                        proj["financials"].update({k: v for k, v in draft["financials"].items() if v})

                    st.success("Done! Check every tab — correct anything that looks wrong, then save and generate the PDF.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Auto-fill failed: {e}")

with tabs[1]:
    st.subheader("Project overview")
    m = proj["meta"]
    c1, c2 = st.columns(2)
    m["project_name"] = c1.text_input("Project name", m["project_name"])
    m["project_number"] = c2.text_input("Project number", m["project_number"])
    m["client_builder"] = c1.text_input("Client / builder", m["client_builder"])
    m["site_address"] = c2.text_input("Site address", m["site_address"])
    m["status_pct"] = c1.text_input("Status (eg 65% - install underway)", m["status_pct"])
    m["contract_ref"] = c2.text_input("Contract ref", m["contract_ref"])
    m["outgoing_pm"] = c1.text_input("Outgoing PM", m["outgoing_pm"])
    m["incoming_pm"] = c2.text_input("Incoming PM", m["incoming_pm"])
    m["handover_date"] = c1.text_input("Handover date", m["handover_date"])
    st.divider()
    st.subheader("Handover summary")
    proj["general_notes"] = st.text_area(
        "Plain-language summary. Status, main risks, what the incoming PM needs first.",
        proj["general_notes"], height=130)
    st.divider()
    st.subheader("Key contacts")
    proj["contacts"] = st.data_editor(
        proj["contacts"], num_rows="dynamic", use_container_width=True, key="contacts",
        column_config={"role": "Role", "name": "Name", "company": "Company",
                       "email": "Email", "phone": "Phone"})

with tabs[2]:
    st.subheader("Hardware schedule status")
    s = proj["schedule"]
    c1, c2 = st.columns(2)
    s["revision"] = c1.text_input("Schedule revision", s["revision"])
    s["status"] = c2.text_input("Schedule status", s["status"])
    s["total_openings"] = c1.text_input("Total openings / doors", s["total_openings"])
    s["total_line_items"] = c2.text_input("Total line items", s["total_line_items"])
    s["notes"] = st.text_area("Schedule notes", s["notes"], height=80)
    st.divider()
    st.subheader("Ordering & procurement")
    st.caption("Status words colour-code on the PDF: ordered/delivered/installed = green, "
               "pending/partial/in progress = amber, back order/outstanding/open = red.")
    proj["ordering"] = st.data_editor(
        proj["ordering"], num_rows="dynamic", use_container_width=True, key="ordering",
        column_config={"description": "Item / description", "supplier": "Supplier",
                       "po_ref": "PO ref", "order_date": "Order date", "eta": "ETA", "status": "Status"})
    st.divider()
    st.subheader("Deliveries")
    proj["deliveries"] = st.data_editor(
        proj["deliveries"], num_rows="dynamic", use_container_width=True, key="deliveries",
        column_config={"description": "Item / description", "location": "Location",
                       "date": "Date", "status": "Status"})
    st.divider()
    st.subheader("Installation status")
    proj["installation"] = st.data_editor(
        proj["installation"], num_rows="dynamic", use_container_width=True, key="install",
        column_config={"area_door": "Area / door", "items": "Items",
                       "status": "Status", "notes": "Notes"})

with tabs[3]:
    st.subheader("Site requests & queries")
    proj["site_requests"] = st.data_editor(
        proj["site_requests"], num_rows="dynamic", use_container_width=True, key="sitereq",
        column_config={"date": "Date", "request": "Request / query", "raised_by": "Raised by",
                       "status": "Status", "action": "Action / owner"})
    st.divider()
    st.subheader("Variations")
    proj["variations"] = st.data_editor(
        proj["variations"], num_rows="dynamic", use_container_width=True, key="vars",
        column_config={"ref": "Ref", "description": "Description", "value": "Value", "status": "Status"})
    st.divider()
    st.subheader("Outstanding actions & risks")
    proj["actions"] = st.data_editor(
        proj["actions"], num_rows="dynamic", use_container_width=True, key="actions",
        column_config={"action": "Action", "owner": "Owner", "due": "Due", "priority": "Priority"})
    st.divider()
    st.subheader("Financial summary (optional)")
    f = proj["financials"]
    c1, c2 = st.columns(2)
    f["contract_value"] = c1.text_input("Contract value", f["contract_value"])
    f["claimed_to_date"] = c2.text_input("Claimed to date", f["claimed_to_date"])
    f["retention"] = c1.text_input("Retention", f["retention"])
    f["variations_value"] = c2.text_input("Variations value", f["variations_value"])
    f["notes"] = st.text_area("Financial notes", f["notes"], height=70)

with tabs[4]:
    st.subheader("Generate the handover PDF")
    name = proj["meta"]["project_name"].strip()
    if not name:
        st.warning("Add a project name in tab 2 first.")
    else:
        st.write(f"Ready to build the handover sheet for **{name}**.")
        if st.button("Build PDF", type="primary"):
            data = {k: v for k, v in proj.items() if not k.startswith("_")}
            tmp = os.path.join(PROJECTS_DIR, safe_name(name) + "_handover.pdf")
            build_pdf(data, tmp)
            with open(tmp, "rb") as fh:
                st.session_state.pdf_bytes = fh.read()
                st.session_state.pdf_name = safe_name(name) + "_handover.pdf"
            st.success("Built. Download below.")
        if st.session_state.get("pdf_bytes"):
            st.download_button("Download handover PDF", st.session_state.pdf_bytes,
                               file_name=st.session_state.pdf_name,
                               mime="application/pdf", type="primary")
