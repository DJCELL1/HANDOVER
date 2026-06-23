"""
Cin7 Omni API helpers for the handover app.
Fetches purchase orders and shipments by Q number (reference field).
Uses the same auth pattern as the pm7-to-cin7-importer app.
"""

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth


def _client():
    cin7 = st.secrets["cin7"]
    base = cin7["base_url"].rstrip("/")
    auth = HTTPBasicAuth(cin7["api_username"], cin7["api_key"])
    return base, auth


def _get(endpoint, params=None, timeout=15):
    base, auth = _client()
    url = f"{base}/{endpoint}"
    r = requests.get(url, params=params, auth=auth, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    # Cin7 Omni wraps results differently depending on endpoint
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # try common wrapper keys
        for key in ("Items", "items", "Data", "data", "PurchaseOrders", "Shipments"):
            if key in data:
                return data[key]
    return data


def fetch_purchase_orders(q_number):
    """
    Return all purchase orders whose reference contains the Q number.
    Tries exact match first, then a broader search.
    """
    q = q_number.strip()
    results = []

    # Try reference field exact
    try:
        rows = _get("v1/PurchaseOrders", params={"where": f"reference='{q}'", "rows": 250})
        if rows:
            results.extend(rows if isinstance(rows, list) else [rows])
    except Exception:
        pass

    # If nothing, try order number contains search
    if not results:
        try:
            rows = _get("v1/PurchaseOrders", params={"where": f"reference like '%{q}%'", "rows": 250})
            if rows:
                results.extend(rows if isinstance(rows, list) else [rows])
        except Exception:
            pass

    return results


def fetch_shipments(q_number):
    """
    Return all stock receives / shipments whose reference contains the Q number.
    Cin7 Omni calls these 'Purchases' (supplier invoices / goods received).
    """
    q = q_number.strip()
    results = []

    for endpoint in ("v1/Purchases", "v1/StockAdjustments"):
        try:
            rows = _get(endpoint, params={"where": f"reference like '%{q}%'", "rows": 250})
            if rows:
                results.extend(rows if isinstance(rows, list) else [rows])
                break
        except Exception:
            continue

    return results


def summarise_po(po):
    """Flatten a PO dict into the columns we care about for the handover."""
    lines = po.get("lineItems") or po.get("LineItems") or po.get("lines") or []
    total_qty = sum(
        (ln.get("qty") or ln.get("quantity") or ln.get("Qty") or 0)
        for ln in lines
    )
    received_qty = sum(
        (ln.get("qtyReceived") or ln.get("receivedQty") or 0)
        for ln in lines
    )
    return {
        "PO Number": po.get("orderNumber") or po.get("id") or "",
        "Reference": po.get("reference") or "",
        "Supplier": (po.get("supplier") or {}).get("name") or po.get("supplierName") or "",
        "Date": po.get("createdDate") or po.get("orderDate") or po.get("date") or "",
        "Expected Date": po.get("deliveryDate") or po.get("expectedDeliveryDate") or "",
        "Status": po.get("status") or "",
        "Total Lines": len(lines),
        "Qty Ordered": total_qty,
        "Qty Received": received_qty,
        "Outstanding": max(0, total_qty - received_qty),
    }


def summarise_shipment(ship):
    """Flatten a shipment/purchase dict into handover columns."""
    lines = ship.get("lineItems") or ship.get("LineItems") or ship.get("lines") or []
    total_qty = sum(
        (ln.get("qty") or ln.get("quantity") or 0)
        for ln in lines
    )
    return {
        "Shipment / Ref": ship.get("orderNumber") or ship.get("id") or "",
        "Reference": ship.get("reference") or "",
        "Supplier": (ship.get("supplier") or {}).get("name") or ship.get("supplierName") or "",
        "Date Received": ship.get("createdDate") or ship.get("date") or "",
        "Status": ship.get("status") or "",
        "Lines": len(lines),
        "Qty Received": total_qty,
    }
