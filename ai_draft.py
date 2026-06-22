"""
AI drafting. Uses Claude to turn parsed emails into a complete handover sheet.
Requires ANTHROPIC_API_KEY in the environment and the `anthropic` package.
"""

import json

SCHEMA = """
Return ONLY valid JSON, no preamble, no markdown fences. Use this exact shape:
{
  "meta": {
    "project_name": "",
    "project_number": "",
    "client_builder": "",
    "site_address": "",
    "status_pct": "",
    "outgoing_pm": "",
    "incoming_pm": "",
    "contract_ref": ""
  },
  "general_notes": "plain-language summary: what is this project, current status, main risks, what the incoming PM needs to know first",
  "schedule": {"revision": "", "total_openings": "", "total_line_items": "", "status": "", "notes": ""},
  "contacts": [{"role":"","name":"","company":"","email":"","phone":""}],
  "ordering": [{"description":"","supplier":"","po_ref":"","order_date":"","eta":"","status":""}],
  "deliveries": [{"description":"","location":"","date":"","status":""}],
  "installation": [{"area_door":"","items":"","status":"","notes":""}],
  "site_requests": [{"date":"","request":"","raised_by":"","status":"","action":""}],
  "variations": [{"ref":"","description":"","value":"","status":""}],
  "actions": [{"action":"","owner":"","due":"","priority":"High/Medium/Low"}],
  "financials": {"contract_value":"","claimed_to_date":"","retention":"","variations_value":"","notes":""},
  "email_log": [{"date":"","from":"","subject":"","summary":"one line factual summary"}]
}

Rules:
- Status words must be one of: Ordered, Delivered, Installed, Complete, Pending, Partial, In progress, On order, Back order, Outstanding, Open, Not ordered, Not installed.
- Only include rows you can support from the emails. Leave fields blank if unknown.
- Do NOT invent PO numbers, dollar values, or dates not present in the emails.
- Extract every person mentioned with their role, company, email and phone if visible.
- Extract every product, supplier, order, delivery and installation item mentioned.
- For actions: capture anything that is unresolved, promised, or needs follow-up.
- For meta: infer project name, number, address, client/builder and PM names from email signatures and content.
- Keep summaries short and factual.
"""


def ai_draft(emails, meta):
    import anthropic
    client = anthropic.Anthropic()

    corpus = []
    for e in emails:
        corpus.append(
            f"---\nDATE: {e.get('date')}\nFROM: {e.get('from')}\nTO: {e.get('to')}\n"
            f"SUBJECT: {e.get('subject')}\nBODY:\n{e.get('body','')[:5000]}\n")
    corpus = "\n".join(corpus)[:150000]

    prompt = (
        "You are preparing a project handover sheet for an architectural door hardware company "
        "in construction. Read all the emails below and extract EVERYTHING needed to hand over "
        "this project to a new project manager. Fill in as much as possible — the goal is that "
        "the incoming PM should not need to read the emails themselves.\n\n"
        f"Known project info (may be incomplete): "
        f"Name: {meta.get('project_name','')}  Number: {meta.get('project_number','')}\n\n"
        f"EMAILS:\n{corpus}\n\n{SCHEMA}"
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text.removeprefix("json").strip()
        if "```" in text:
            text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)
