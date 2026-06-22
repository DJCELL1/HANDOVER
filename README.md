# Architectural Hardware - Project Handover Generator

A small Streamlit app that turns a pile of project emails into a consistent PDF
handover sheet. One format for every job.

## What it does

- One project per job, all jobs use the identical handover format
- Drop in emails (.eml or .msg), it builds a correspondence log
- Fill in the handover sections in editable tables (orders, deliveries, install,
  site requests, variations, actions, financials)
- Optional auto-draft: Claude reads the emails and pre-fills the sections for you
- Download a clean PDF per project
- Projects save locally so you can update them later

## Setup (one time)

You need Python 3.9+. From a terminal in this folder:

    pip install -r requirements.txt

## Run it

    streamlit run handover_app.py

It opens in your browser. Work through the 5 tabs, then hit Build PDF.

## Files

- handover_app.py   the Streamlit app
- handover_pdf.py   builds the PDF (edit this to change layout/colours)
- email_parse.py    reads .eml and .msg files
- ai_draft.py       optional Claude auto-draft
- projects/         saved projects (JSON) and generated PDFs land here

## Getting emails out as files

- Outlook desktop: select emails, drag to a Windows folder to get .msg, or
  File > Save As > .msg. You can multi-select and drag a whole batch.
- Gmail: open an email, the three dots menu, Download message (.eml).
- Outlook web: open email, three dots, Save / Download.

You can also paste an email in by hand under the Emails tab.

## Auto-draft (optional)

If you want Claude to pre-fill the sections from the emails, set your API key
before launching:

Windows (PowerShell):

    $env:ANTHROPIC_API_KEY="your-key-here"
    streamlit run handover_app.py

Mac/Linux:

    export ANTHROPIC_API_KEY="your-key-here"
    streamlit run handover_app.py

Without a key the app works fine, you just fill everything in yourself. Either
way, review every section before you build the PDF. The draft is a starting
point, not gospel.

## Changing the look

Colours and layout live in handover_pdf.py at the top (NAVY, ACCENT etc). The
status colour coding is in STATUS_COLOURS. Add your own status words there if you
use different ones.
