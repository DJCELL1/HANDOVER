"""
Cin7 Omni API helpers for the handover app.
Fetches purchase orders, shipments and sales orders by Q number.
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


def _get(endpoint, params=None, timeout=20):
    base, auth = _client()
    url = f"{base}/{endpoint}"
    r = requests.get(url, params=params, auth=auth, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("Items", "items", "Data", "data",
                    "PurchaseOrders", "SaleOrders", "Purchases", "Shipments"):
            if key in data:
                return data[key]
    return data


def _search(endpoint, q, rows=250):
    """Try exact then LIKE match on reference field."""
    for where in (f"reference='{q}'", f"reference like '%{q}%'"):
        try:
            rows_data = _get(endpoint, params={"where": where, "rows": rows})
            if rows_data:
                return rows_data if isinstance(rows_data, list) else [rows_data]
        except Exception:
            pass
    return []


def fetch_purchase_orders(q_number):
    return _search("v1/PurchaseOrders", q_number.strip())


def fetch_shipments(q_number):
    """Goods received / supplier invoices — Cin7 Omni calls these 'Purchases'."""
    q = q_number.strip()
    for endpoint in ("v1/Purchases", "v1/StockAdjustments"):
        results = _search(endpoint, q)
        if results:
            return results
    return []


def fetch_sales_orders(q_number):
    """
    Match sales orders whose reference starts with the Q number.
    e.g. Q12345 matches Q12345, Q12345.S1, Q12345.S2 etc.
    """
    q = q_number.strip()
    results = []
    for where in (f"reference='{q}'", f"reference like '{q}%'"):
        try:
            rows = _get("v1/SaleOrders", params={"where": where, "rows": 250})
            if rows:
                data = rows if isinstance(rows, list) else [rows]
                # de-duplicate by id
                seen = {r.get("id") or r.get("orderNumber") for r in results}
                for r in data:
                    key = r.get("id") or r.get("orderNumber")
                    if key not in seen:
                        results.append(r)
                        seen.add(key)
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Line-level flatteners
# ---------------------------------------------------------------------------

def _get_lines(record):
    for key in ("lineItems", "LineItems", "lines", "Lines"):
        if record.get(key):
            return record[key]
    return []


def _short_date(val):
    if not val:
        return ""
    return str(val)[:10]


def po_lines(pos):
    """Return one row per PO line item."""
    rows = []
    for po in pos:
        po_num = po.get("orderNumber") or po.get("id") or ""
        ref = po.get("reference") or ""
        supplier = (po.get("supplier") or {}).get("name") or po.get("supplierName") or ""
        order_date = _short_date(po.get("createdDate") or po.get("orderDate") or po.get("date"))
        eta = _short_date(po.get("deliveryDate") or po.get("expectedDeliveryDate"))
        po_status = po.get("status") or ""
        lines = _get_lines(po)
        if not lines:
            rows.append({
                "PO Number": po_num,
                "Reference": ref,
                "Supplier": supplier,
                "Order Date": order_date,
                "ETA": eta,
                "SKU": "",
                "Description": "",
                "Qty Ordered": "",
                "Qty Received": "",
                "Outstanding": "",
                "Unit Price": "",
                "PO Status": po_status,
            })
        po_received = str(po_status).strip().lower() == "received"
        for ln in lines:
            qty_ord = ln.get("qty") or ln.get("quantity") or ln.get("Qty") or 0
            qty_rec = ln.get("qtyReceived") or ln.get("receivedQty") or ln.get("QtyReceived") or 0
            ln_status = str(ln.get("status") or "").strip().lower()
            line_received = ln_status == "received" or po_received
            try:
                outstanding = 0 if line_received else max(0, float(qty_ord) - float(qty_rec))
            except (TypeError, ValueError):
                outstanding = 0 if line_received else ""
            rows.append({
                "PO Number": po_num,
                "Reference": ref,
                "Supplier": supplier,
                "Order Date": order_date,
                "ETA": eta,
                "SKU": ln.get("sku") or ln.get("code") or ln.get("Code") or "",
                "Description": ln.get("name") or ln.get("description") or ln.get("productName") or "",
                "Qty Ordered": qty_ord,
                "Qty Received": qty_rec,
                "Outstanding": outstanding,
                "Unit Price": ln.get("price") or ln.get("unitPrice") or "",
                "PO Status": po_status,
            })
    return rows


def shipment_lines(ships):
    """Return one row per shipment line item."""
    rows = []
    for ship in ships:
        ref_num = ship.get("orderNumber") or ship.get("id") or ""
        ref = ship.get("reference") or ""
        supplier = (ship.get("supplier") or {}).get("name") or ship.get("supplierName") or ""
        date_recv = _short_date(ship.get("createdDate") or ship.get("date"))
        status = ship.get("status") or ""
        lines = _get_lines(ship)
        if not lines:
            rows.append({
                "Shipment #": ref_num, "Reference": ref, "Supplier": supplier,
                "Date Received": date_recv, "SKU": "", "Description": "",
                "Qty Received": "", "Status": status,
            })
        for ln in lines:
            rows.append({
                "Shipment #": ref_num,
                "Reference": ref,
                "Supplier": supplier,
                "Date Received": date_recv,
                "SKU": ln.get("sku") or ln.get("code") or ln.get("Code") or "",
                "Description": ln.get("name") or ln.get("description") or ln.get("productName") or "",
                "Qty Received": ln.get("qty") or ln.get("quantity") or 0,
                "Status": status,
            })
    return rows


def sales_order_lines(sos):
    """Return one row per sales order line item."""
    rows = []
    for so in sos:
        so_num = so.get("orderNumber") or so.get("id") or ""
        ref = so.get("reference") or ""
        customer = (so.get("customer") or {}).get("name") or so.get("customerName") or ""
        order_date = _short_date(so.get("createdDate") or so.get("orderDate") or so.get("date"))
        so_status = so.get("status") or ""
        lines = _get_lines(so)
        if not lines:
            rows.append({
                "SO Number": so_num, "Reference": ref, "Customer": customer,
                "Order Date": order_date, "SKU": "", "Description": "",
                "Qty": "", "Qty Fulfilled": "", "Outstanding": "", "SO Status": so_status,
            })
        for ln in lines:
            qty = ln.get("qty") or ln.get("quantity") or 0
            qty_ful = ln.get("qtyFulfilled") or ln.get("fulfilledQty") or ln.get("qtyShipped") or 0
            try:
                outstanding = max(0, float(qty) - float(qty_ful))
            except (TypeError, ValueError):
                outstanding = ""
            rows.append({
                "SO Number": so_num,
                "Reference": ref,
                "Customer": customer,
                "Order Date": order_date,
                "SKU": ln.get("sku") or ln.get("code") or ln.get("Code") or "",
                "Description": ln.get("name") or ln.get("description") or ln.get("productName") or "",
                "Qty": qty,
                "Qty Fulfilled": qty_ful,
                "Outstanding": outstanding,
                "SO Status": so_status,
            })
    return rows
