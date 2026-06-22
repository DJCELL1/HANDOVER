"""
Optional AI drafting. Uses Claude to turn parsed emails into draft handover
sections. Requires ANTHROPIC_API_KEY in the environment and the `anthropic`
package installed.
"""

import json

SCHEMA = """
Return ONLY valid JSON, no preamble, no markdown fences. Use this exact shape:
{
  "general_notes": "short plain-language handover summary, status and main risks",
  "schedule": {"revision": "", "total_openings": "", "total_line_items": "", "status": "", "notes": ""},
  "contacts": [{"role":"","name":"","company":"","email":"","phone":""}],
  "ordering": [{"description":"","supplier":"","po_ref":"","order_date":"","eta":"","status":""}],
  "deliveries": [{"description":"","location":"","date":"","status":""}],
  "installation": [{"area_door":"","items":"","status":"","notes":""}],
  "site_requests": [{"date":"","request":"","raised_by":"","status":"","action":""}],
  "variations": [{"ref":"","description":"","value":"","status":""}],
  "actions": [{"action":"","owner":"","due":"","priority":""}],
  "email_log": [{"date":"","from":"","subject":"","summary":"one line summary"}]
}
Status words should be one of: Ordered, Delivered, Installed, Complete, Pending, Partial,
In progress, On order, Back order, Outstanding, Open, Not ordered, Not installed.
Only include rows you can actually support from the emails. Leave fields blank if unknown.
Keep summaries short and factual. Do not invent PO numbers, values or dates.
"""


def ai_draft(emails, meta):
    import anthropic
    client = anthropic.Anthropic()

    corpus = []
    for e in emails:
        corpus.append(
            f"---\nDATE: {e.get('date')}\nFROM: {e.get('from')}\n"
            f"SUBJECT: {e.get('subject')}\nBODY:\n{e.get('body','')[:4000]}\n")
    corpus = "\n".join(corpus)[:120000]

    prompt = (
        "You are preparing a project handover sheet for architectural door hardware "
        "in construction. Read the emails below and extract the handover information.\n\n"
        f"Project: {meta.get('project_name','')} ({meta.get('project_number','')})\n\n"
        f"EMAILS:\n{corpus}\n\n{SCHEMA}"
    )

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text else text
        text = text.removeprefix("json").strip()
        text = text.rsplit("```", 1)[0].strip() if text.endswith("```") else text
    return json.loads(text)
