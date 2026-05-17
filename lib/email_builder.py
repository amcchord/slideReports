"""
Helpers for building emailed report attachments under Postmark's 10 MB cap.

Postmark rejects any single API request whose JSON body exceeds 10 MB. Since
attachments are sent as base64-encoded JSON fields, large reports (especially
those with hundreds of agent screenshots) easily blow past this limit even
after image compression.

This module:
- Generates the report HTML with screenshot images shrunk to a sensible
  email-friendly size.
- Builds PDF/HTML attachments.
- Projects the size of the final Postmark JSON payload.
- If the first pass is too large, automatically retries with more aggressive
  image settings (smaller dimensions + lower JPEG quality).
- If both passes fail, raises ``EmailTooLargeError`` with a user-facing
  message that callers can surface in logs / API responses.
"""
import base64
import json
import logging
from typing import Any, Dict, List, Optional

from .pdf_service import PDFService

logger = logging.getLogger(__name__)


POSTMARK_MAX_BYTES = 10 * 1024 * 1024
# Leave headroom for headers, "From"/"To" metadata, and small base64 padding
# variations between local estimate and what Postmark sees server-side.
POSTMARK_SAFE_BYTES = 9_500_000

FIRST_PASS = {"image_max_width": 600, "image_jpeg_quality": 75}
SECOND_PASS = {"image_max_width": 320, "image_jpeg_quality": 55}


class EmailTooLargeError(Exception):
    """Raised when an emailed report exceeds Postmark's 10 MB limit even
    after aggressive image compression."""


def _project_payload_size(
    *,
    to_email: str,
    subject: str,
    text_body: Optional[str],
    html_body: Optional[str],
    attachments: List[Dict[str, str]],
    from_email: str = "noreply@slide.recipes",
) -> int:
    """
    Estimate the size of the JSON request body that ``EmailService`` will POST
    to Postmark. Mirrors the payload construction in
    ``lib/email_service.py`` so the projection matches reality.
    """
    payload: Dict[str, Any] = {
        "From": from_email,
        "To": to_email,
        "Subject": subject,
    }
    if html_body is not None:
        payload["HtmlBody"] = html_body
        if text_body is not None:
            payload["TextBody"] = text_body
    elif text_body is not None:
        payload["TextBody"] = text_body
    if attachments:
        payload["Attachments"] = attachments
    return len(json.dumps(payload).encode('utf-8'))


def _build_attachments_dict(
    *,
    pdf_content: Optional[bytes],
    pdf_filename: Optional[str],
    html_content: Optional[bytes],
    html_filename: Optional[str],
) -> List[Dict[str, str]]:
    """Build the Postmark "Attachments" list with base64-encoded content."""
    attachments: List[Dict[str, str]] = []
    if pdf_content is not None and pdf_filename is not None:
        attachments.append({
            "Name": pdf_filename,
            "Content": base64.b64encode(pdf_content).decode('utf-8'),
            "ContentType": "application/pdf",
        })
    if html_content is not None and html_filename is not None:
        attachments.append({
            "Name": html_filename,
            "Content": base64.b64encode(html_content).decode('utf-8'),
            "ContentType": "text/html",
        })
    return attachments


def _generate_pass(
    *,
    generator,
    template_html: str,
    start_date,
    end_date,
    data_sources,
    logo_url: str,
    client_id,
    ai_generator,
    attachment_format: str,
    date_str: str,
    base_filename: str,
    image_max_width: int,
    image_jpeg_quality: int,
) -> Dict[str, Any]:
    """Generate report HTML with image optimization, then build attachments."""
    html_content = generator.generate_report_with_base64_images(
        template_html,
        start_date,
        end_date,
        data_sources,
        logo_url=logo_url,
        client_id=client_id,
        ai_generator=ai_generator,
        optimize_images=True,
        image_max_width=image_max_width,
        image_jpeg_quality=image_jpeg_quality,
    )

    pdf_content: Optional[bytes] = None
    pdf_filename: Optional[str] = None
    html_attachment_content: Optional[bytes] = None
    html_attachment_filename: Optional[str] = None

    if attachment_format in ('pdf', 'both'):
        pdf_content = PDFService.html_to_pdf(html_content)
        pdf_filename = f"{base_filename}-{date_str}.pdf"

    if attachment_format in ('html', 'both'):
        html_attachment_content = html_content.encode('utf-8')
        html_attachment_filename = f"{base_filename}-{date_str}.html"

    return {
        'html_content': html_content,
        'pdf_content': pdf_content,
        'pdf_filename': pdf_filename,
        'html_attachment_content': html_attachment_content,
        'html_attachment_filename': html_attachment_filename,
    }


def build_email_attachments(
    *,
    generator,
    template_html: str,
    start_date,
    end_date,
    data_sources,
    logo_url: str,
    client_id,
    ai_generator,
    attachment_format: str,
    date_str: str,
    to_email: str,
    subject: str,
    text_body: Optional[str] = None,
    html_body: Optional[str] = None,
    base_filename: str = 'slide-backup-report',
) -> Dict[str, Any]:
    """
    Build PDF/HTML attachments for an emailed report, automatically shrinking
    screenshot images and falling back to a more aggressive second pass when
    the projected Postmark payload is over the safe size.

    Args:
        generator: ``ReportGenerator`` instance.
        template_html: The Jinja2 template HTML to render.
        start_date / end_date: Reporting period (UTC).
        data_sources: List of data sources passed to the generator.
        logo_url: Logo URL/path passed to the generator.
        client_id: Optional client filter passed to the generator.
        ai_generator: Optional AI generator for executive summaries.
        attachment_format: ``'pdf'``, ``'html'``, or ``'both'``.
        date_str: Date string used in attachment filenames (e.g. ``2025-05-17``).
        to_email / subject / text_body / html_body: Used for payload size
            projection (must match what the caller will send to ``EmailService``).
        base_filename: Filename prefix for the attachments.

    Returns:
        Dict with keys:
            ``pdf_content``, ``pdf_filename``,
            ``html_attachment_content``, ``html_attachment_filename``,
            ``html_content`` (the rendered HTML, for callers that want it),
            ``pass_used`` (``'first'`` or ``'second'``),
            ``projected_payload_bytes`` (int).

    Raises:
        EmailTooLargeError: If even the second pass exceeds the Postmark
            10 MB limit.
    """
    # First pass: gentle compression, preserves most visual quality.
    result = _generate_pass(
        generator=generator,
        template_html=template_html,
        start_date=start_date,
        end_date=end_date,
        data_sources=data_sources,
        logo_url=logo_url,
        client_id=client_id,
        ai_generator=ai_generator,
        attachment_format=attachment_format,
        date_str=date_str,
        base_filename=base_filename,
        image_max_width=FIRST_PASS['image_max_width'],
        image_jpeg_quality=FIRST_PASS['image_jpeg_quality'],
    )

    attachments = _build_attachments_dict(
        pdf_content=result['pdf_content'],
        pdf_filename=result['pdf_filename'],
        html_content=result['html_attachment_content'],
        html_filename=result['html_attachment_filename'],
    )
    projected = _project_payload_size(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachments=attachments,
    )
    logger.info(
        "Email payload first-pass projected size: %.2f MB (%d bytes)",
        projected / (1024 * 1024), projected,
    )

    if projected <= POSTMARK_SAFE_BYTES:
        result['pass_used'] = 'first'
        result['projected_payload_bytes'] = projected
        return result

    # Second pass: aggressive shrink for extreme cases (500+ agents, etc.)
    logger.warning(
        "Email payload %.2f MB exceeds safe size %.2f MB; retrying with "
        "more aggressive image compression (max_width=%d, quality=%d)",
        projected / (1024 * 1024),
        POSTMARK_SAFE_BYTES / (1024 * 1024),
        SECOND_PASS['image_max_width'],
        SECOND_PASS['image_jpeg_quality'],
    )

    result = _generate_pass(
        generator=generator,
        template_html=template_html,
        start_date=start_date,
        end_date=end_date,
        data_sources=data_sources,
        logo_url=logo_url,
        client_id=client_id,
        ai_generator=ai_generator,
        attachment_format=attachment_format,
        date_str=date_str,
        base_filename=base_filename,
        image_max_width=SECOND_PASS['image_max_width'],
        image_jpeg_quality=SECOND_PASS['image_jpeg_quality'],
    )

    attachments = _build_attachments_dict(
        pdf_content=result['pdf_content'],
        pdf_filename=result['pdf_filename'],
        html_content=result['html_attachment_content'],
        html_filename=result['html_attachment_filename'],
    )
    projected = _project_payload_size(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachments=attachments,
    )
    logger.info(
        "Email payload second-pass projected size: %.2f MB (%d bytes)",
        projected / (1024 * 1024), projected,
    )

    if projected > POSTMARK_SAFE_BYTES:
        raise EmailTooLargeError(
            "Report exceeds the 10 MB email size limit even after image "
            f"compression (projected {projected / (1024 * 1024):.1f} MB). "
            "Try a narrower date range, a template with fewer screenshots, "
            "or filter the report by a single client."
        )

    result['pass_used'] = 'second'
    result['projected_payload_bytes'] = projected
    return result
