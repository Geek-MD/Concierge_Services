"""Attribute extraction module for Concierge Services.

Extracts billing attributes from email body using targeted field patterns.
Only the fields required before PDF analysis are extracted.

Extraction is modularised by service type so that each utility category
(water, gas, electricity, …) can use patterns tuned to its own email
format.  The main entry point is :func:`extract_attributes_from_email_body`,
which accepts an optional *service_type* argument (one of the
``SERVICE_TYPE_*`` constants defined in :mod:`const`).
"""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Any

from .const import (
    SERVICE_TYPE_ELECTRICITY,
    SERVICE_TYPE_GAS,
    SERVICE_TYPE_UNKNOWN,
    SERVICE_TYPE_WATER,
)

_LOGGER = logging.getLogger(__name__)


# Patterns for billing period dates (start and end)
DATE_PATTERNS = [
    r"([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
    r"([0-9]{1,2}\s+de\s+[a-zA-Z]+\s+de\s+[0-9]{4})",
    r"([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
]


def _strip_html(html: str) -> str:
    """Strip HTML tags and decode entities, returning only visible text."""
    class _TextExtractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self._parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self._parts.append(data)

        def get_text(self) -> str:
            return "\n".join(self._parts)

    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


# Label patterns that precede a total-amount value
_TOTAL_LABELS = re.compile(
    r"(?:total\s+a\s+pagar|monto\s+total|total\s+factura|importe\s+total"
    r"|total\s+cuenta|valor\s+a\s+pagar|total)[:\s]+",
    re.IGNORECASE,
)

# Label patterns that precede a customer/account number
# "de" is optional to match both "Número de Cliente:" and "Número Cliente:" (Metrogas)
_CUSTOMER_LABELS = re.compile(
    r"(?:n[úu]mero\s+(?:de\s+)?(?:cuenta|cliente)|n[°º]\s*(?:cuenta|cliente)"
    r"|cuenta\s+n[°º]?|cliente\s+n[°º]?|customer\s+(?:number|no\.?)|account\s+(?:number|no\.?))"
    r"[:\s]+",
    re.IGNORECASE,
)

# Label patterns that precede an address value
_ADDRESS_LABELS = re.compile(
    r"(?:direcci[oó]n(?:\s+de\s+suministro)?|domicilio|address)[:\s]+",
    re.IGNORECASE,
)

# Label pattern that precedes a payment due date
_DUE_DATE_LABELS = re.compile(
    r"fecha\s+de\s+vencimiento[:\s]+",
    re.IGNORECASE,
)

# Currency amount pattern (reused by _extract_total_amount)
_AMOUNT_RE = re.compile(
    r"\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)"
    r"|([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)\s*(?:CLP|USD|EUR|pesos?)",
    re.IGNORECASE,
)


def _extract_total_amount(text: str) -> str | None:
    """Return the total amount due found in *text*, or None."""
    for label_match in _TOTAL_LABELS.finditer(text):
        rest = text[label_match.end():]
        amount_match = _AMOUNT_RE.search(rest[:60])
        if amount_match:
            raw = (amount_match.group(1) or amount_match.group(2) or "").strip()
            if raw:
                return raw
    # Fallback: first currency amount in the whole text
    amount_match = _AMOUNT_RE.search(text)
    if amount_match:
        return (amount_match.group(1) or amount_match.group(2) or "").strip() or None
    return None


def _extract_customer_number(text: str) -> str | None:
    """Return the customer/account number found in *text*, or None."""
    for label_match in _CUSTOMER_LABELS.finditer(text):
        rest = text[label_match.end():]
        # Grab first sequence of digits (possibly formatted with dots/dashes)
        num_match = re.search(r"([0-9][0-9.\-]{0,19})", rest[:80])
        if num_match:
            return num_match.group(1).strip()
    return None


def _extract_address(text: str) -> str | None:
    """Return the service address found in *text*, or None."""
    for label_match in _ADDRESS_LABELS.finditer(text):
        rest = text[label_match.end():]
        # Take up to end-of-line, trimmed
        line_match = re.search(r"([^\n\r]{5,120})", rest)
        if line_match:
            value = re.sub(r"\s+", " ", line_match.group(1)).strip()
            if value:
                return value
    return None


def _extract_due_date(text: str) -> str | None:
    """Return the payment due date found in *text*, or None.

    Looks for a ``Fecha de vencimiento`` label (common on Chilean utility
    bills) and returns the date that immediately follows it.
    """
    for label_match in _DUE_DATE_LABELS.finditer(text):
        rest = text[label_match.end():]
        for pattern in DATE_PATTERNS:
            date_match = re.search(pattern, rest[:60], re.IGNORECASE)
            if date_match:
                return date_match.group(1).strip()
    return None


def _extract_dates(text: str) -> dict[str, str]:
    """Extract billing period start and end dates from *text*."""
    dates: dict[str, str] = {}
    _DATE_KEYS = ["billing_period_start", "billing_period_end"]

    for pattern in DATE_PATTERNS:
        for i, match in enumerate(re.finditer(pattern, text, re.IGNORECASE)):
            if i >= len(_DATE_KEYS):
                break
            key = _DATE_KEYS[i]
            if key not in dates:
                dates[key] = match.group(1).strip()

    return dates


# ---------------------------------------------------------------------------
# Water-service extractor (reference implementation: Aguas Andinas)
# ---------------------------------------------------------------------------
# Consumption in cubic metres (m³ / M3)
_WATER_CONSUMPTION_RE = re.compile(
    r"([0-9]+(?:[.,][0-9]+)?)\s*m[³3]",
    re.IGNORECASE,
)
# Labels that precede meter-reading values
_WATER_READING_LABELS = re.compile(
    r"lectura\s+(?:anterior|actual|medidor)[:\s]+",
    re.IGNORECASE,
)
# Label for water meter number
_WATER_METER_LABELS = re.compile(
    r"(?:n[úu]mero\s+de\s+medidor|medidor\s+n[°º]?)[:\s]+",
    re.IGNORECASE,
)


def _extract_water_attributes(text: str) -> dict[str, Any]:
    """Extract water-service-specific attributes.

    Currently tuned for Aguas Andinas email format.
    Additional water companies can be supported by extending the patterns above.

    Extracted fields (all optional):
        ``consumption_m3``   – volume consumed in m³
        ``meter_reading``    – meter reading value(s) found after a reading label
        ``meter_number``     – water meter identifier
    """
    attrs: dict[str, Any] = {}

    # Consumption volume
    consumption_match = _WATER_CONSUMPTION_RE.search(text)
    if consumption_match:
        attrs["consumption_m3"] = consumption_match.group(1).strip()

    # Meter readings (anterior / actual)
    readings: list[str] = []
    for label_match in _WATER_READING_LABELS.finditer(text):
        rest = text[label_match.end():]
        val_match = re.search(r"([0-9][0-9.,]{0,15})", rest[:60])
        if val_match:
            readings.append(val_match.group(1).strip())
    if readings:
        attrs["meter_reading"] = readings[0] if len(readings) == 1 else readings

    # Meter number
    for label_match in _WATER_METER_LABELS.finditer(text):
        rest = text[label_match.end():]
        num_match = re.search(r"([A-Za-z0-9][-A-Za-z0-9]{1,19})", rest[:60])
        if num_match:
            attrs["meter_number"] = num_match.group(1).strip()
            break

    return attrs


# ---------------------------------------------------------------------------
# Gas-service extractor (tuned for Metrogas; reference email: Jan 2026)
# ---------------------------------------------------------------------------
# Consumption in cubic metres — label-based only.
# NOTE: Metrogas does NOT include consumption in the email body; it is only
# present in the PDF attachment.  The label-based pattern is kept for gas
# companies that do include it in their email.
_GAS_CONSUMPTION_RE = re.compile(
    r"([0-9]+(?:[.,][0-9]+)?)\s*m[³3]",
    re.IGNORECASE,
)
_GAS_CONSUMPTION_LABELS = re.compile(
    r"(?:consumo\s+(?:de\s+)?gas|consumo|volumen\s+consumido)[:\s]+",
    re.IGNORECASE,
)
# Metropuntos loyalty-points label (Metrogas-specific)
_GAS_METROPUNTOS_LABELS = re.compile(
    r"metropuntos[:\s]+",
    re.IGNORECASE,
)
# Plain number pattern for "Total a pagar" — Metrogas omits the $ sign,
# e.g. "Total a pagar: 12.013" (Chilean thousands separator is '.').
_GAS_PLAIN_AMOUNT_RE = re.compile(
    r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)",
)


def _extract_gas_attributes(text: str) -> dict[str, Any]:
    """Extract gas-service-specific attributes.

    Tuned for Metrogas (reference email: January 2026).  Key observations:
    - The HTML-only email carries folio, customer number, address, billing
      period, total due, due date, and Metropuntos loyalty balance.
    - Gas consumption (m³) is **not** included in the email — only in the PDF.
    - ``Total a pagar`` has no ``$`` prefix (e.g. ``12.013``).
    - Customer label is ``Número Cliente:`` (no ``de`` — handled in the
      shared ``_CUSTOMER_LABELS`` pattern).
    - ``Metropuntos`` is a Metrogas loyalty-programme balance.

    Extracted fields (all optional):
        ``total_amount``  – total amount due (plain number; overrides generic)
        ``metropuntos``   – Metrogas loyalty points balance
        ``consumption_m3``– gas consumed in m³ (label-based only, for issuers
                            that include it in the email body)
    """
    attrs: dict[str, Any] = {}

    # Total a pagar — Metrogas uses a plain number without a $ prefix.
    # This overrides the generic extractor result (which would return nothing
    # for plain numbers).  We reuse _TOTAL_LABELS for the label match so that
    # the search window is anchored to the correct part of the text.
    for label_match in _TOTAL_LABELS.finditer(text):
        rest = text[label_match.end():]
        val_match = _GAS_PLAIN_AMOUNT_RE.search(rest[:60])
        if val_match:
            raw = val_match.group(1).strip()
            if raw:
                attrs["total_amount"] = raw
                break

    # Gas consumption (m³) — label-based only; bare m³ fallback omitted to
    # avoid false positives in HTML that contains no consumption data.
    for label_match in _GAS_CONSUMPTION_LABELS.finditer(text):
        rest = text[label_match.end():]
        val_match = _GAS_CONSUMPTION_RE.search(rest[:80])
        if val_match:
            attrs["consumption_m3"] = val_match.group(1).strip()
            break

    # Metropuntos (Metrogas loyalty programme)
    for label_match in _GAS_METROPUNTOS_LABELS.finditer(text):
        rest = text[label_match.end():]
        pts_match = re.search(r"([0-9]+)", rest[:20])
        if pts_match:
            attrs["metropuntos"] = pts_match.group(1).strip()
            break

    return attrs


# ---------------------------------------------------------------------------
# Electricity-service extractor (skeleton — patterns to be refined with real emails)
# ---------------------------------------------------------------------------
_ELEC_CONSUMPTION_RE = re.compile(
    r"([0-9]+(?:[.,][0-9]+)?)\s*kWh",
    re.IGNORECASE,
)
_ELEC_CONSUMPTION_LABELS = re.compile(
    r"(?:consumo|energ[íi]a\s+consumida)[:\s]+",
    re.IGNORECASE,
)
_ELEC_POWER_LABELS = re.compile(
    r"(?:potencia\s+contratada|potencia)[:\s]+",
    re.IGNORECASE,
)


def _extract_electricity_attributes(text: str) -> dict[str, Any]:
    """Extract electricity-service-specific attributes.

    This is a skeleton extractor.  Patterns will be refined once real
    electricity company email samples are available.

    Extracted fields (all optional):
        ``consumption_kwh``       – energy consumed in kWh
        ``contracted_power_kw``   – contracted power in kW (if present)
    """
    attrs: dict[str, Any] = {}

    # Energy consumption — label-preceded first, then bare kWh value
    for label_match in _ELEC_CONSUMPTION_LABELS.finditer(text):
        rest = text[label_match.end():]
        val_match = _ELEC_CONSUMPTION_RE.search(rest[:80])
        if val_match:
            attrs["consumption_kwh"] = val_match.group(1).strip()
            break
    if "consumption_kwh" not in attrs:
        val_match = _ELEC_CONSUMPTION_RE.search(text)
        if val_match:
            attrs["consumption_kwh"] = val_match.group(1).strip()

    # Contracted power (kW)
    for label_match in _ELEC_POWER_LABELS.finditer(text):
        rest = text[label_match.end():]
        kw_match = re.search(
            r"([0-9]+(?:[.,][0-9]+)?)\s*kW(?!h)",
            rest[:60],
            re.IGNORECASE,
        )
        if kw_match:
            attrs["contracted_power_kw"] = kw_match.group(1).strip()
            break

    return attrs


# ---------------------------------------------------------------------------
# Routing helper
# ---------------------------------------------------------------------------

def _extract_type_specific_attributes(text: str, service_type: str) -> dict[str, Any]:
    """Dispatch to the extractor for *service_type* and return its results."""
    if service_type == SERVICE_TYPE_WATER:
        return _extract_water_attributes(text)
    if service_type == SERVICE_TYPE_GAS:
        return _extract_gas_attributes(text)
    if service_type == SERVICE_TYPE_ELECTRICITY:
        return _extract_electricity_attributes(text)
    return {}


def extract_attributes_from_email_body(
    subject: str, body: str, service_type: str = SERVICE_TYPE_UNKNOWN
) -> dict[str, Any]:
    """Extract billing attributes from email subject and body.

    Extracts exactly the fields needed before PDF analysis:
    folio, billing_period_start, billing_period_end,
    total_amount, customer_number, address.

    When *service_type* is provided, additional type-specific attributes
    are extracted (e.g. ``consumption_m3`` for water services,
    ``consumption_kwh`` for electricity services).

    Args:
        subject:      Email subject line (decoded).
        body:         Plain-text email body.
        service_type: One of the SERVICE_TYPE_* constants (default: ``unknown``).

    Returns:
        Dictionary with extracted attributes.
    """
    attributes: dict[str, Any] = {}

    try:
        # Folio — from subject line (confirmed later against PDF)
        subject_attrs = _extract_from_subject(subject)
        attributes.update(subject_attrs)

        # Combine subject + body for field search; cap for performance
        combined = f"{subject}\n\n{body}"
        if len(combined) > 15000:
            combined = combined[:15000]

        # Billing period dates
        dates = _extract_dates(combined)
        attributes.update(dates)

        # Total amount
        total = _extract_total_amount(combined)
        if total:
            attributes["total_amount"] = total

        # Customer / account number
        customer = _extract_customer_number(combined)
        if customer:
            attributes["customer_number"] = customer

        # Service address
        address = _extract_address(combined)
        if address:
            attributes["address"] = address

        # Payment due date
        due_date = _extract_due_date(combined)
        if due_date:
            attributes["due_date"] = due_date

        # Service-type-specific attributes (consumption, meter readings, etc.)
        type_attrs = _extract_type_specific_attributes(combined, service_type)
        attributes.update(type_attrs)

    except Exception as err:
        _LOGGER.debug("Error extracting attributes: %s", err)

    return attributes



def _extract_from_subject(subject: str) -> dict[str, str]:
    """
    Extract specific attributes from email subject line.
    
    Subject lines often contain key identifiers in a compact format.
    """
    attrs: dict[str, str] = {}
    
    # Extract folio/invoice numbers from subject
    folio_patterns = [
        r"folio[:\s]*([0-9]{6,})",
        r"nro\.?\s+([0-9]{6,})",           # "Nro. 0000000061778648" (Metrogas)
        r"n[úu]mero[:\s]*([0-9]{6,})",
        r"boleta[:\s]*([0-9]{6,})",
        r"factura[:\s]*([0-9]{6,})",
    ]
    
    for pattern in folio_patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            attrs["folio"] = match.group(1)
            break
    
    # Extract RUT from subject if present
    rut_pattern = r"([0-9]{1,2}\.[0-9]{3}\.[0-9]{3}-[0-9kK])"
    match = re.search(rut_pattern, subject)
    if match:
        attrs["rut_from_subject"] = match.group(1)
    
    return attrs


def extract_attributes_from_email(msg: Any) -> dict[str, Any]:
    """
    Extract attributes directly from an email message object.
    
    Args:
        msg: email.message.Message object
    
    Returns:
        Dictionary with extracted attributes
    """
    from email.header import decode_header
    
    # Decode subject
    subject_header = msg.get("Subject", "")
    decoded_fragments = decode_header(subject_header)
    subject_parts = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            subject_parts.append(fragment.decode(encoding or "utf-8", errors="ignore"))
        else:
            subject_parts.append(fragment)
    subject = "".join(subject_parts)
    
    # Extract body
    body = ""
    try:
        if msg.is_multipart():
            plain_parts: list[str] = []
            html_parts: list[str] = []

            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text = payload.decode(charset, errors="ignore")  # type: ignore[union-attr]
                        if content_type == "text/plain":
                            plain_parts.append(text)
                        elif content_type == "text/html":
                            html_parts.append(text)
                except Exception:
                    pass

            if plain_parts:
                body = " ".join(plain_parts)
            elif html_parts:
                body = _strip_html(" ".join(html_parts))
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    raw = payload.decode(charset, errors="ignore")  # type: ignore[union-attr]
                    body = _strip_html(raw) if msg.get_content_type() == "text/html" else raw
            except Exception:
                pass
    except Exception as err:
        _LOGGER.debug("Error extracting body for attribute extraction: %s", err)
    
    return extract_attributes_from_email_body(subject, body)

