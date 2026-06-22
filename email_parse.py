"""
Email parsing helpers. Handles .eml, .msg (Outlook), and pasted text.
Returns a normalised dict: {date, from, to, subject, body}
"""

import email
from email import policy
from email.utils import parsedate_to_datetime
import io


def _clean(text):
    if not text:
        return ""
    # collapse excessive whitespace / quoted reply noise lightly
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = []
    blank = 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def parse_eml(file_bytes):
    msg = email.message_from_bytes(file_bytes, policy=policy.default)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    body += part.get_content()
                except Exception:
                    pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        body += _strip_html(part.get_content())
                    except Exception:
                        pass
    else:
        try:
            if msg.get_content_type() == "text/html":
                body = _strip_html(msg.get_content())
            else:
                body = msg.get_content()
        except Exception:
            body = ""

    date = ""
    try:
        if msg["Date"]:
            date = parsedate_to_datetime(msg["Date"]).strftime("%d %b %Y")
    except Exception:
        date = str(msg.get("Date", ""))

    return {
        "date": date,
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "subject": str(msg.get("Subject", "")),
        "body": _clean(body),
    }


def parse_msg(file_bytes):
    import extract_msg
    m = extract_msg.Message(io.BytesIO(file_bytes))
    date = ""
    try:
        if m.date:
            date = m.date.strftime("%d %b %Y")
    except Exception:
        date = str(m.date or "")
    return {
        "date": date,
        "from": str(m.sender or ""),
        "to": str(m.to or ""),
        "subject": str(m.subject or ""),
        "body": _clean(str(m.body or "")),
    }


def _strip_html(html):
    import re
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", "", html)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return text


def parse_upload(filename, file_bytes):
    name = (filename or "").lower()
    if name.endswith(".msg"):
        return parse_msg(file_bytes)
    # default treat as eml / mime
    return parse_eml(file_bytes)


def parse_pasted_text(text):
    """
    Try to extract From/Date/Subject/Body from raw pasted email text.
    Handles Outlook copy-paste which includes headers at the top.
    """
    import re

    lines = text.splitlines()

    result = {"date": "", "from": "", "to": "", "subject": "", "body": ""}

    # Patterns for Outlook-style pasted headers
    header_patterns = {
        "from": re.compile(r"^From:\s*(.+)$", re.IGNORECASE),
        "to": re.compile(r"^To:\s*(.+)$", re.IGNORECASE),
        "date": re.compile(r"^(?:Sent|Date):\s*(.+)$", re.IGNORECASE),
        "subject": re.compile(r"^Subject:\s*(.+)$", re.IGNORECASE),
    }

    body_start = 0
    in_headers = True
    found_any = False

    for i, line in enumerate(lines):
        if in_headers:
            matched = False
            for key, pat in header_patterns.items():
                m = pat.match(line.strip())
                if m:
                    result[key] = m.group(1).strip()
                    matched = True
                    found_any = True
                    break
            if not matched and found_any and line.strip() == "":
                body_start = i + 1
                in_headers = False
                break

    result["body"] = _clean("\n".join(lines[body_start:]))

    # Try to normalise the date
    if result["date"]:
        try:
            from email.utils import parsedate_to_datetime
            result["date"] = parsedate_to_datetime(result["date"]).strftime("%d %b %Y")
        except Exception:
            # Try common formats
            for fmt in ("%d/%m/%Y %I:%M %p", "%A, %d %B %Y %I:%M %p", "%d %B %Y"):
                try:
                    from datetime import datetime as dt
                    result["date"] = dt.strptime(result["date"].split(",")[-1].strip(), fmt).strftime("%d %b %Y")
                    break
                except Exception:
                    pass

    return result
