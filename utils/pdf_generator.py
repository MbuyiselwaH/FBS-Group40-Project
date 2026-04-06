'''from datetime import datetime
import io


# ── Colour palette ─────────────────────────────────────────────────────────────
_NAVY   = (26/255,  58/255,  92/255)
_GOLD   = (232/255, 160/255, 32/255)
_LIGHT  = (248/255, 250/255, 252/255)
_MUTED  = (148/255, 163/255, 184/255)
_BORDER = (226/255, 232/255, 240/255)
_GREEN  = (52/255,  211/255, 153/255)
_AMBER  = (251/255, 191/255, 36/255)
_RED    = (248/255, 113/255, 113/255)
_PURPLE = (167/255, 139/255, 250/255)
_WHITE  = (1, 1, 1)
_DARK   = (71/255,  85/255, 105/255)


def _status_colour(status):
    return {
        'approved': _GREEN,
        'rejected': _RED,
        'pending':  _AMBER,
        'paid':     _PURPLE,
    }.get(status, _MUTED)


# ── PDF builder ────────────────────────────────────────────────────────────────

def generate_pdf_bytes(booking, app_url=''):
    """
    Build a booking-confirmation PDF and return raw bytes.

    This uses reportlab's canvas API directly — no HTML-to-PDF conversion,
    no weasyprint, no Chrome — so output is always a valid PDF regardless
    of server environment.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib import colors

    PAGE_W, PAGE_H = A4
    MARGIN = 18 * mm

    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'Booking Confirmation #{booking.id:05d}')
    c.setAuthor('DUT Campus Facility Booking System')
    c.setSubject(booking.title)

    # ── Drawing helpers ──────────────────────────────────────────────────────

    def filled_rect(x, y, w, h, fill, stroke=None):
        c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke)
            c.rect(x, y, w, h, fill=1, stroke=1)
        else:
            c.rect(x, y, w, h, fill=1, stroke=0)

    def text_at(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawString(x, y, str(txt))

    def right_text(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawRightString(x, y, str(txt))

    def centred_text(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawCentredString(x, y, str(txt))

    def hline(y_pos, colour=_BORDER, width=0.5):
        c.setStrokeColorRGB(*colour)
        c.setLineWidth(width)
        c.line(MARGIN, y_pos, PAGE_W - MARGIN, y_pos)

    def card(x, y, w, h):
        filled_rect(x, y, w, h, _LIGHT, _BORDER)

    def section_label(x, y_pos, txt):
        c.setFont('Helvetica-Bold', 6.5)
        c.setFillColorRGB(*_MUTED)
        c.drawString(x, y_pos, txt.upper())

    # ── HEADER ───────────────────────────────────────────────────────────────
    HEADER_H = 52 * mm
    filled_rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, _NAVY)

    c.setFont('Helvetica-Bold', 13)
    c.setFillColorRGB(*_WHITE)
    c.drawString(MARGIN, PAGE_H - 16 * mm, 'Campus Facility Booking System')

    c.setFont('Helvetica', 7.5)
    c.setFillColorRGB(*_MUTED)
    c.drawString(MARGIN, PAGE_H - 22 * mm, 'Durban University of Technology')

    right_text(PAGE_W - MARGIN, PAGE_H - 14 * mm,
               f'#{booking.id:05d}', 'Helvetica-Bold', 22, _GOLD)
    right_text(PAGE_W - MARGIN, PAGE_H - 20 * mm,
               'REF NO.', size=6.5, colour=_MUTED)

    # Status badge
    status_label  = 'PAID' if booking.status == 'paid' else booking.status.upper()
    badge_w, badge_h = 28 * mm, 6.5 * mm
    badge_x = MARGIN
    badge_y = PAGE_H - HEADER_H + 10 * mm
    filled_rect(badge_x, badge_y, badge_w, badge_h, _status_colour(booking.status))
    centred_text(badge_x + badge_w / 2, badge_y + 2 * mm,
                 status_label, 'Helvetica-Bold', 7.5, _WHITE)

    gen_str = f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC"
    right_text(PAGE_W - MARGIN, badge_y + 2 * mm, gen_str, size=6.5, colour=_MUTED)

    y = PAGE_H - HEADER_H - 6 * mm

    # ── KEY INFO CARDS (2 x 2) ───────────────────────────────────────────────
    CARD_W = (PAGE_W - 2 * MARGIN - 4 * mm) / 2
    CARD_H = 20 * mm

    campus_str = (f' · {booking.facility.campus}' if booking.facility.campus else '')
    cards = [
        ('DATE',      booking.booking_date.strftime('%d %B %Y'),
                      booking.booking_date.strftime('%A')),
        ('TIME SLOT', f"{booking.start_time.strftime('%H:%M')} \u2013 {booking.end_time.strftime('%H:%M')}",
                      f'{booking.duration_hours:.1f} hours'),
        ('FACILITY',  booking.facility.name,
                      f'{booking.facility.location}{campus_str}'),
        ('ATTENDEES', str(booking.attendees),
                      f'Capacity: {booking.facility.capacity}'),
    ]

    for i, (label, main, sub) in enumerate(cards):
        col = i % 2
        row = i // 2
        cx  = MARGIN + col * (CARD_W + 4 * mm)
        cy  = (y - CARD_H) - row * (CARD_H + 3 * mm)
        card(cx, cy, CARD_W, CARD_H)
        section_label(cx + 3 * mm, cy + CARD_H - 5 * mm, label)
        text_at(cx + 3 * mm, cy + CARD_H - 10.5 * mm, main,
                'Helvetica-Bold', 9.5, _NAVY)
        text_at(cx + 3 * mm, cy + 3.5 * mm, sub, size=7.5, colour=_MUTED)

    y -= (CARD_H + 3 * mm) * 2 + 10 * mm

    # ── BOOKING DETAILS TABLE ────────────────────────────────────────────────
    hline(y + 4 * mm)
    section_label(MARGIN, y + 1 * mm, 'Booking Details')
    y -= 5 * mm

    id_str  = booking.user.student_number or booking.user.email
    org_str = f' \u2013 {booking.user.organisation}' if booking.user.organisation else ''

    detail_rows = [
        ('Booking Title', booking.title),
        ('Booked By',     booking.user.full_name),
        ('ID / Number',   id_str),
        ('Role',          f'{booking.user.role.title()}{org_str}'),
        ('Submitted',     booking.created_at.strftime('%d %b %Y at %H:%M')),
    ]
    if booking.is_recurring and booking.recurrence_pattern:
        end = (f' until {booking.recurrence_end_date.strftime("%d %b %Y")}'
               if booking.recurrence_end_date else '')
        detail_rows.append(('Recurrence', f'{booking.recurrence_pattern.title()}{end}'))
    if booking.admin_notes:
        detail_rows.append(('Admin Notes', booking.admin_notes))
    if booking.amount_paid:
        detail_rows.append(('Amount Paid', f'R{float(booking.amount_paid):.2f}'))
    if booking.is_attended and booking.attended_at:
        detail_rows.append(('Attended', booking.attended_at.strftime('%d %b %Y at %H:%M')))

    ROW_H = 7 * mm
    for label, value in detail_rows:
        text_at(MARGIN,              y, label, size=8, colour=_MUTED)
        text_at(MARGIN + 45 * mm,   y, value, 'Helvetica-Bold', 8, _NAVY)
        y -= ROW_H
        hline(y + 1.5 * mm, colour=(235/255, 238/255, 243/255), width=0.3)

    y -= 4 * mm

    # ── REASON ──────────────────────────────────────────────────────────────
    hline(y + 3 * mm)
    section_label(MARGIN, y, 'Reason for Booking')
    y -= 5 * mm

    reason_style = ParagraphStyle(
        'reason',
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
    )
    reason_para = Paragraph(booking.reason, reason_style)
    reason_w    = PAGE_W - 2 * MARGIN - 6 * mm
    _rw, rh     = reason_para.wrap(reason_w, 9999)
    box_h       = rh + 6 * mm

    card(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h)
    filled_rect(MARGIN, y - box_h, 2 * mm, box_h, _GOLD)
    reason_para.drawOn(c, MARGIN + 4 * mm, y - box_h + 3 * mm)
    y -= box_h + 5 * mm

    # ── QR CODE ──────────────────────────────────────────────────────────────
    if booking.qr_token:
        try:
            from utils.qr_generator import generate_qr_png
            base_url = (app_url or 'http://127.0.0.1:5000').rstrip('/')
            qr_url   = f'{base_url}/checkin/{booking.qr_token}'
            qr_bytes = generate_qr_png(qr_url, box_size=6, border=2)
            QR_SIZE  = 32 * mm
            qr_img   = ImageReader(io.BytesIO(qr_bytes))
            box_h    = QR_SIZE + 10 * mm

            card(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h)
            c.drawImage(qr_img,
                        MARGIN + 4 * mm,
                        y - box_h + (box_h - QR_SIZE) / 2,
                        width=QR_SIZE, height=QR_SIZE,
                        preserveAspectRatio=True, mask='auto')

            tx = MARGIN + QR_SIZE + 10 * mm
            ty = y - 9 * mm
            text_at(tx, ty, 'Check-in QR Code', 'Helvetica-Bold', 9, _NAVY)
            text_at(tx, ty - 5  * mm,
                    'Present this document to the facility attendant on arrival.',
                    size=7.5, colour=_DARK)
            text_at(tx, ty - 9  * mm,
                    'They will scan this QR code to confirm your attendance.',
                    size=7.5, colour=_DARK)
            text_at(tx, ty - 13.5 * mm,
                    f'Token: {booking.qr_token[:36]}...',
                    size=6, colour=_MUTED)
            y -= box_h + 4 * mm
        except Exception:
            pass  # non-fatal — PDF is still valid without QR

    # ── FOOTER ───────────────────────────────────────────────────────────────
    footer_h = 12 * mm
    filled_rect(0, 0, PAGE_W, footer_h, _LIGHT)
    hline(footer_h, colour=_BORDER, width=0.5)
    centred_text(PAGE_W / 2, footer_h - 4 * mm,
                 'Campus Facility Booking System  \u00b7  Durban University of Technology',
                 size=6.5, colour=_MUTED)
    centred_text(PAGE_W / 2, footer_h - 8 * mm,
                 f'Official confirmation document  \u00b7  CBS-{booking.id:05d}',
                 size=6, colour=_MUTED)

    c.showPage()
    c.save()
    return buf.getvalue()


def try_generate_pdf_bytes(booking):
    """Convenience wrapper for the /download-pdf route. Returns bytes or None."""
    try:
        return generate_pdf_bytes(booking)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'PDF generation failed: {e}')
        return None


# ── Browser confirmation page (print/save route — unchanged) ───────────────────

def generate_confirmation_html(booking, base_url='http://127.0.0.1:5000'):
    """Return a printable HTML page for the /bookings/<id>/confirmation route."""
    generated_at = datetime.utcnow().strftime('%d %B %Y at %H:%M UTC')

    qr_html = ''
    if booking.qr_token:
        try:
            from utils.qr_generator import generate_qr_base64
            qr_url        = f'{base_url}/checkin/{booking.qr_token}'
            qr_b64        = generate_qr_base64(qr_url, box_size=8)
            token_preview = booking.qr_token[:32] + '...'
            qr_html = (
                '<div style="padding:20px 44px 0;page-break-inside:avoid">'
                '<div style="display:flex;align-items:center;gap:24px;background:#f8fafc;'
                'border:1px solid #e2e8f0;border-radius:12px;padding:18px 22px">'
                '<div style="flex-shrink:0">'
                f'<img src="{qr_b64}" alt="Check-in QR" '
                'style="width:130px;height:130px;border:2px solid #1a3a5c;'
                'border-radius:8px;padding:4px;background:#fff">'
                '</div><div>'
                '<div style="font-weight:700;color:#1a3a5c;font-size:.95rem;margin-bottom:6px">'
                'Check-in QR Code</div>'
                '<div style="font-size:.78rem;color:#475569;line-height:1.7">'
                'Present this document to the facility attendant on arrival.<br>'
                'They will scan this QR code to confirm your attendance.<br>'
                f'<span style="font-family:monospace;font-size:.68rem;color:#94a3b8">'
                f'Token: {token_preview}</span></div></div></div></div>'
            )
        except Exception:
            pass

    rs = 'color:#888;font-size:.85rem;padding:8px 0;border-bottom:1px solid #f1f5f9;width:160px'
    vs = 'color:#1a3a5c;font-weight:600;font-size:.85rem;padding:8px 0;border-bottom:1px solid #f1f5f9'

    extra_rows = ''
    if booking.is_recurring and booking.recurrence_pattern:
        end = (f' until {booking.recurrence_end_date.strftime("%d %b %Y")}'
               if booking.recurrence_end_date else '')
        extra_rows += f'<tr><td style="{rs}">Recurrence</td><td style="{vs}">{booking.recurrence_pattern.title()}{end}</td></tr>'
    if booking.admin_notes:
        extra_rows += f'<tr><td style="{rs}">Admin Notes</td><td style="{vs}">{booking.admin_notes}</td></tr>'
    if booking.amount_paid:
        extra_rows += (f'<tr><td style="{rs}">Amount Paid</td>'
                       f'<td style="color:#5b21b6;font-weight:700;font-size:.85rem;'
                       f'padding:8px 0;border-bottom:1px solid #f1f5f9">'
                       f'R{float(booking.amount_paid):.2f}</td></tr>')
    if booking.is_attended:
        extra_rows += (f'<tr><td style="{rs}">Attended</td>'
                       f'<td style="color:#065f46;font-weight:700;font-size:.85rem;'
                       f'padding:8px 0;border-bottom:1px solid #f1f5f9">'
                       f'&#10003; {booking.attended_at.strftime("%d %b %Y at %H:%M")}</td></tr>')

    equipment_html = ''
    if booking.facility.equipment_list:
        tags = ''.join(
            f'<span style="display:inline-block;background:#f0f4ff;color:#1a3a5c;'
            f'font-size:.72rem;padding:3px 10px;border-radius:6px;margin:3px 2px 3px 0">'
            f'&#10003; {eq}</span>'
            for eq in booking.facility.equipment_list
        )
        equipment_html = (
            '<div style="margin:20px 44px 0">'
            '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.12em;color:#94a3b8;margin-bottom:8px;font-family:monospace">'
            'Equipment &amp; Resources</div>' + tags + '</div>'
        )

    status_colour = {'approved': '#34d399', 'rejected': '#f87171',
                     'pending': '#fbbf24', 'paid': '#a78bfa'}.get(booking.status, '#94a3b8')
    status_label  = 'PAID' if booking.status == 'paid' else booking.status.upper()
    campus_str    = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    id_str        = booking.user.student_number or booking.user.email
    org_str       = (' &mdash; ' + booking.user.organisation) if booking.user.organisation else ''

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        f'<title>Booking Confirmation #{booking.id:05d}</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700'
        '&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
        '<style>* { box-sizing:border-box; margin:0; padding:0; }'
        "body { font-family:'Sora',Arial,sans-serif; background:#f0f4f8;"
        '  display:flex; flex-direction:column; align-items:center; padding:40px 20px; }'
        '.page { background:#fff; width:794px; min-height:980px;'
        '  box-shadow:0 8px 40px rgba(0,0,0,.12); border-radius:4px; overflow:hidden; }'
        '@media print { body { background:#fff; padding:0; }'
        '  .page { box-shadow:none; width:100%; } .no-print { display:none!important; } }'
        '</style></head><body><div class="page">'

        # Header
        '<div style="background:linear-gradient(135deg,#1a3a5c,#2563a8);padding:36px 44px">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        '<div><div style="color:#fff;font-weight:700;font-size:1.25rem;margin-bottom:4px">'
        'Campus Facility Booking System</div>'
        '<div style="color:rgba(255,255,255,.5);font-size:.72rem;font-family:JetBrains Mono,monospace;'
        'text-transform:uppercase;letter-spacing:.08em">Durban University of Technology</div></div>'
        '<div style="text-align:right">'
        '<div style="color:rgba(255,255,255,.45);font-size:.65rem;font-family:JetBrains Mono,monospace;text-transform:uppercase">Ref No.</div>'
        f'<div style="color:#e8a020;font-size:1.7rem;font-weight:700;font-family:JetBrains Mono,monospace;line-height:1">#{booking.id:05d}</div>'
        '</div></div>'
        f'<div style="margin-top:20px;display:inline-flex;align-items:center;gap:8px;'
        f'background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);'
        f'border-radius:100px;padding:5px 14px">'
        f'<div style="width:8px;height:8px;border-radius:50%;background:{status_colour}"></div>'
        f'<span style="color:#fff;font-size:.8rem;font-weight:600">{status_label}</span></div></div>'

        # Info grid
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:28px 44px 0">'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Date</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem">{booking.booking_date.strftime("%d %B %Y")}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.booking_date.strftime("%A")}</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Time Slot</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem;font-family:JetBrains Mono,monospace">'
        f'{booking.start_time.strftime("%H:%M")} &ndash; {booking.end_time.strftime("%H:%M")}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.duration_hours:.1f} hours</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Facility</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1rem">{booking.facility.name}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.facility.location}{campus_str}</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Attendees</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem">{booking.attendees}</div>'
        f'<div style="color:#64748b;font-size:.8rem">Capacity: {booking.facility.capacity}</div></div>'
        '</div>'

        # Details table
        '<div style="padding:24px 44px 0">'
        '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;'
        'color:#94a3b8;margin-bottom:10px;font-family:monospace">Booking Details</div>'
        '<table style="width:100%;border-collapse:collapse">'
        f'<tr><td style="{rs}">Booking Title</td><td style="{vs}">{booking.title}</td></tr>'
        f'<tr><td style="{rs}">Booked By</td><td style="{vs}">{booking.user.full_name}</td></tr>'
        f'<tr><td style="{rs}">ID / Number</td><td style="{vs};font-family:JetBrains Mono,monospace">{id_str}</td></tr>'
        f'<tr><td style="{rs}">Role</td><td style="{vs}">{booking.user.role.title()}{org_str}</td></tr>'
        f'{extra_rows}'
        f'<tr><td style="color:#888;font-size:.85rem;padding:8px 0">Submitted</td>'
        f'<td style="color:#1a3a5c;font-weight:600;font-size:.85rem;padding:8px 0">'
        f'{booking.created_at.strftime("%d %b %Y at %H:%M")}</td></tr>'
        '</table></div>'

        # Reason
        '<div style="padding:20px 44px 0">'
        '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;'
        'color:#94a3b8;margin-bottom:8px;font-family:monospace">Reason for Booking</div>'
        f'<div style="background:#f8fafc;border-left:4px solid #e8a020;border-radius:0 8px 8px 0;'
        f'padding:14px 18px;color:#475569;font-size:.875rem;line-height:1.7">{booking.reason}</div></div>'

        f'{equipment_html}{qr_html}'

        # Footer
        '<div style="background:#f8fafc;border-top:2px solid #e2e8f0;padding:20px 44px;'
        'display:flex;justify-content:space-between;align-items:center;margin-top:20px">'
        '<div><div style="font-size:.8rem;font-weight:700;color:#1a3a5c">Campus Facility Booking System</div>'
        '<div style="font-size:.7rem;color:#94a3b8">Durban University of Technology</div>'
        '<div style="font-size:.7rem;color:#94a3b8">Official booking confirmation document</div></div>'
        '<div style="text-align:right">'
        f'<div style="font-size:.65rem;color:#cbd5e1;font-family:JetBrains Mono,monospace">Generated: {generated_at}</div>'
        f'<div style="font-size:.65rem;color:#cbd5e1;font-family:JetBrains Mono,monospace">CBS-{booking.id:05d}</div>'
        '</div></div></div>'

        # Print button (hidden when printing)
        '<div class="no-print" style="margin-top:20px;text-align:center">'
        '<button onclick="window.print()" style="background:#e8a020;color:#1a3a5c;border:none;'
        'padding:11px 30px;border-radius:8px;font-weight:700;font-size:.9rem;cursor:pointer;'
        "font-family:'Sora',sans-serif\">Print / Save as PDF</button>"
        '<a href="javascript:history.back()" '
        'style="color:#94a3b8;text-decoration:none;font-size:.8rem;margin-left:16px">Back to booking</a>'
        '</div></body></html>'
    )
'''

import os
from datetime import datetime
import io


# ── Colour palette ─────────────────────────────────────────────────────────────
_NAVY   = (26/255,  58/255,  92/255)
_GOLD   = (232/255, 160/255, 32/255)
_LIGHT  = (248/255, 250/255, 252/255)
_MUTED  = (148/255, 163/255, 184/255)
_BORDER = (226/255, 232/255, 240/255)
_GREEN  = (52/255,  211/255, 153/255)
_AMBER  = (251/255, 191/255, 36/255)
_RED    = (248/255, 113/255, 113/255)
_PURPLE = (167/255, 139/255, 250/255)
_WHITE  = (1, 1, 1)
_DARK   = (71/255,  85/255, 105/255)


def _status_colour(status):
    return {
        'approved': _GREEN,
        'rejected': _RED,
        'pending':  _AMBER,
        'paid':     _PURPLE,
    }.get(status, _MUTED)


# ── PDF builder ────────────────────────────────────────────────────────────────

def generate_pdf_bytes(booking, app_url=None):
    """
    Build a booking-confirmation PDF and return raw bytes.

    This uses reportlab's canvas API directly — no HTML-to-PDF conversion,
    no weasyprint, no Chrome — so output is always a valid PDF regardless
    of server environment.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib import colors

    PAGE_W, PAGE_H = A4
    MARGIN = 18 * mm

    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'Booking Confirmation #{booking.id:05d}')
    c.setAuthor('DUT Campus Facility Booking System')
    c.setSubject(booking.title)

    # ── Drawing helpers ──────────────────────────────────────────────────────

    def filled_rect(x, y, w, h, fill, stroke=None):
        c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke)
            c.rect(x, y, w, h, fill=1, stroke=1)
        else:
            c.rect(x, y, w, h, fill=1, stroke=0)

    def text_at(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawString(x, y, str(txt))

    def right_text(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawRightString(x, y, str(txt))

    def centred_text(x, y, txt, font='Helvetica', size=9, colour=_DARK):
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        c.drawCentredString(x, y, str(txt))

    def hline(y_pos, colour=_BORDER, width=0.5):
        c.setStrokeColorRGB(*colour)
        c.setLineWidth(width)
        c.line(MARGIN, y_pos, PAGE_W - MARGIN, y_pos)

    def card(x, y, w, h):
        filled_rect(x, y, w, h, _LIGHT, _BORDER)

    def section_label(x, y_pos, txt):
        c.setFont('Helvetica-Bold', 6.5)
        c.setFillColorRGB(*_MUTED)
        c.drawString(x, y_pos, txt.upper())

    # ── HEADER ───────────────────────────────────────────────────────────────
    HEADER_H = 52 * mm
    filled_rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, _NAVY)

    c.setFont('Helvetica-Bold', 13)
    c.setFillColorRGB(*_WHITE)
    c.drawString(MARGIN, PAGE_H - 16 * mm, 'Campus Facility Booking System')

    c.setFont('Helvetica', 7.5)
    c.setFillColorRGB(*_MUTED)
    c.drawString(MARGIN, PAGE_H - 22 * mm, 'Durban University of Technology')

    right_text(PAGE_W - MARGIN, PAGE_H - 14 * mm,
               f'#{booking.id:05d}', 'Helvetica-Bold', 22, _GOLD)
    right_text(PAGE_W - MARGIN, PAGE_H - 20 * mm,
               'REF NO.', size=6.5, colour=_MUTED)

    # Status badge
    status_label  = 'PAID' if booking.status == 'paid' else booking.status.upper()
    badge_w, badge_h = 28 * mm, 6.5 * mm
    badge_x = MARGIN
    badge_y = PAGE_H - HEADER_H + 10 * mm
    filled_rect(badge_x, badge_y, badge_w, badge_h, _status_colour(booking.status))
    centred_text(badge_x + badge_w / 2, badge_y + 2 * mm,
                 status_label, 'Helvetica-Bold', 7.5, _WHITE)

    gen_str = f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC"
    right_text(PAGE_W - MARGIN, badge_y + 2 * mm, gen_str, size=6.5, colour=_MUTED)

    y = PAGE_H - HEADER_H - 6 * mm

    # ── KEY INFO CARDS (2 x 2) ───────────────────────────────────────────────
    CARD_W = (PAGE_W - 2 * MARGIN - 4 * mm) / 2
    CARD_H = 20 * mm

    campus_str = (f' · {booking.facility.campus}' if booking.facility.campus else '')
    cards = [
        ('DATE',      booking.booking_date.strftime('%d %B %Y'),
                      booking.booking_date.strftime('%A')),
        ('TIME SLOT', f"{booking.start_time.strftime('%H:%M')} \u2013 {booking.end_time.strftime('%H:%M')}",
                      f'{booking.duration_hours:.1f} hours'),
        ('FACILITY',  booking.facility.name,
                      f'{booking.facility.location}{campus_str}'),
        ('ATTENDEES', str(booking.attendees),
                      f'Capacity: {booking.facility.capacity}'),
    ]

    for i, (label, main, sub) in enumerate(cards):
        col = i % 2
        row = i // 2
        cx  = MARGIN + col * (CARD_W + 4 * mm)
        cy  = (y - CARD_H) - row * (CARD_H + 3 * mm)
        card(cx, cy, CARD_W, CARD_H)
        section_label(cx + 3 * mm, cy + CARD_H - 5 * mm, label)
        text_at(cx + 3 * mm, cy + CARD_H - 10.5 * mm, main,
                'Helvetica-Bold', 9.5, _NAVY)
        text_at(cx + 3 * mm, cy + 3.5 * mm, sub, size=7.5, colour=_MUTED)

    y -= (CARD_H + 3 * mm) * 2 + 10 * mm

    # ── BOOKING DETAILS TABLE ────────────────────────────────────────────────
    hline(y + 4 * mm)
    section_label(MARGIN, y + 1 * mm, 'Booking Details')
    y -= 5 * mm

    id_str  = booking.user.student_number or booking.user.email
    org_str = f' \u2013 {booking.user.organisation}' if booking.user.organisation else ''

    detail_rows = [
        ('Booking Title', booking.title),
        ('Booked By',     booking.user.full_name),
        ('ID / Number',   id_str),
        ('Role',          f'{booking.user.role.title()}{org_str}'),
        ('Submitted',     booking.created_at.strftime('%d %b %Y at %H:%M')),
    ]
    if booking.is_recurring and booking.recurrence_pattern:
        end = (f' until {booking.recurrence_end_date.strftime("%d %b %Y")}'
               if booking.recurrence_end_date else '')
        detail_rows.append(('Recurrence', f'{booking.recurrence_pattern.title()}{end}'))
    if booking.admin_notes:
        detail_rows.append(('Admin Notes', booking.admin_notes))
    if booking.amount_paid:
        detail_rows.append(('Amount Paid', f'R{float(booking.amount_paid):.2f}'))
    if booking.is_attended and booking.attended_at:
        detail_rows.append(('Attended', booking.attended_at.strftime('%d %b %Y at %H:%M')))

    ROW_H = 7 * mm
    for label, value in detail_rows:
        text_at(MARGIN,              y, label, size=8, colour=_MUTED)
        text_at(MARGIN + 45 * mm,   y, value, 'Helvetica-Bold', 8, _NAVY)
        y -= ROW_H
        hline(y + 1.5 * mm, colour=(235/255, 238/255, 243/255), width=0.3)

    y -= 4 * mm

    # ── REASON ──────────────────────────────────────────────────────────────
    hline(y + 3 * mm)
    section_label(MARGIN, y, 'Reason for Booking')
    y -= 5 * mm

    reason_style = ParagraphStyle(
        'reason',
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
    )
    reason_para = Paragraph(booking.reason, reason_style)
    reason_w    = PAGE_W - 2 * MARGIN - 6 * mm
    _rw, rh     = reason_para.wrap(reason_w, 9999)
    box_h       = rh + 6 * mm

    card(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h)
    filled_rect(MARGIN, y - box_h, 2 * mm, box_h, _GOLD)
    reason_para.drawOn(c, MARGIN + 4 * mm, y - box_h + 3 * mm)
    y -= box_h + 5 * mm

    # ── QR CODE ──────────────────────────────────────────────────────────────
    if booking.qr_token:
        try:
            from utils.qr_generator import generate_qr_png
            base_url = (app_url or os.getenv('APP_URL', 'http://127.0.0.1:5000')).rstrip('/')
            qr_url   = f'{base_url}/checkin/{booking.qr_token}'
            qr_bytes = generate_qr_png(qr_url, box_size=6, border=2)
            QR_SIZE  = 32 * mm
            qr_img   = ImageReader(io.BytesIO(qr_bytes))
            box_h    = QR_SIZE + 10 * mm

            card(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h)
            c.drawImage(qr_img,
                        MARGIN + 4 * mm,
                        y - box_h + (box_h - QR_SIZE) / 2,
                        width=QR_SIZE, height=QR_SIZE,
                        preserveAspectRatio=True, mask='auto')

            tx = MARGIN + QR_SIZE + 10 * mm
            ty = y - 9 * mm
            text_at(tx, ty, 'Check-in QR Code', 'Helvetica-Bold', 9, _NAVY)
            text_at(tx, ty - 5  * mm,
                    'Present this document to the facility attendant on arrival.',
                    size=7.5, colour=_DARK)
            text_at(tx, ty - 9  * mm,
                    'They will scan this QR code to confirm your attendance.',
                    size=7.5, colour=_DARK)
            text_at(tx, ty - 13.5 * mm,
                    f'Token: {booking.qr_token[:36]}...',
                    size=6, colour=_MUTED)
            y -= box_h + 4 * mm
        except Exception:
            pass  # non-fatal — PDF is still valid without QR

    # ── FOOTER ───────────────────────────────────────────────────────────────
    footer_h = 12 * mm
    filled_rect(0, 0, PAGE_W, footer_h, _LIGHT)
    hline(footer_h, colour=_BORDER, width=0.5)
    centred_text(PAGE_W / 2, footer_h - 4 * mm,
                 'Campus Facility Booking System  \u00b7  Durban University of Technology',
                 size=6.5, colour=_MUTED)
    centred_text(PAGE_W / 2, footer_h - 8 * mm,
                 f'Official confirmation document  \u00b7  CBS-{booking.id:05d}',
                 size=6, colour=_MUTED)

    c.showPage()
    c.save()
    return buf.getvalue()


def try_generate_pdf_bytes(booking):
    """Convenience wrapper for the /download-pdf route. Returns bytes or None."""
    try:
        return generate_pdf_bytes(booking)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'PDF generation failed: {e}')
        return None


# ── Browser confirmation page (print/save route — unchanged) ───────────────────

def generate_confirmation_html(booking, base_url=None):
    """Return a printable HTML page for the /bookings/<id>/confirmation route."""
    base_url     = (base_url or os.getenv('APP_URL', 'http://127.0.0.1:5000')).rstrip('/')
    generated_at = datetime.utcnow().strftime('%d %B %Y at %H:%M UTC')

    qr_html = ''
    if booking.qr_token:
        try:
            from utils.qr_generator import generate_qr_base64
            qr_url        = f'{base_url}/checkin/{booking.qr_token}'
            qr_b64        = generate_qr_base64(qr_url, box_size=8)
            token_preview = booking.qr_token[:32] + '...'
            qr_html = (
                '<div style="padding:20px 44px 0;page-break-inside:avoid">'
                '<div style="display:flex;align-items:center;gap:24px;background:#f8fafc;'
                'border:1px solid #e2e8f0;border-radius:12px;padding:18px 22px">'
                '<div style="flex-shrink:0">'
                f'<img src="{qr_b64}" alt="Check-in QR" '
                'style="width:130px;height:130px;border:2px solid #1a3a5c;'
                'border-radius:8px;padding:4px;background:#fff">'
                '</div><div>'
                '<div style="font-weight:700;color:#1a3a5c;font-size:.95rem;margin-bottom:6px">'
                'Check-in QR Code</div>'
                '<div style="font-size:.78rem;color:#475569;line-height:1.7">'
                'Present this document to the facility attendant on arrival.<br>'
                'They will scan this QR code to confirm your attendance.<br>'
                f'<span style="font-family:monospace;font-size:.68rem;color:#94a3b8">'
                f'Token: {token_preview}</span></div></div></div></div>'
            )
        except Exception:
            pass

    rs = 'color:#888;font-size:.85rem;padding:8px 0;border-bottom:1px solid #f1f5f9;width:160px'
    vs = 'color:#1a3a5c;font-weight:600;font-size:.85rem;padding:8px 0;border-bottom:1px solid #f1f5f9'

    extra_rows = ''
    if booking.is_recurring and booking.recurrence_pattern:
        end = (f' until {booking.recurrence_end_date.strftime("%d %b %Y")}'
               if booking.recurrence_end_date else '')
        extra_rows += f'<tr><td style="{rs}">Recurrence</td><td style="{vs}">{booking.recurrence_pattern.title()}{end}</td></tr>'
    if booking.admin_notes:
        extra_rows += f'<tr><td style="{rs}">Admin Notes</td><td style="{vs}">{booking.admin_notes}</td></tr>'
    if booking.amount_paid:
        extra_rows += (f'<tr><td style="{rs}">Amount Paid</td>'
                       f'<td style="color:#5b21b6;font-weight:700;font-size:.85rem;'
                       f'padding:8px 0;border-bottom:1px solid #f1f5f9">'
                       f'R{float(booking.amount_paid):.2f}</td></tr>')
    if booking.is_attended:
        extra_rows += (f'<tr><td style="{rs}">Attended</td>'
                       f'<td style="color:#065f46;font-weight:700;font-size:.85rem;'
                       f'padding:8px 0;border-bottom:1px solid #f1f5f9">'
                       f'&#10003; {booking.attended_at.strftime("%d %b %Y at %H:%M")}</td></tr>')

    equipment_html = ''
    if booking.facility.equipment_list:
        tags = ''.join(
            f'<span style="display:inline-block;background:#f0f4ff;color:#1a3a5c;'
            f'font-size:.72rem;padding:3px 10px;border-radius:6px;margin:3px 2px 3px 0">'
            f'&#10003; {eq}</span>'
            for eq in booking.facility.equipment_list
        )
        equipment_html = (
            '<div style="margin:20px 44px 0">'
            '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.12em;color:#94a3b8;margin-bottom:8px;font-family:monospace">'
            'Equipment &amp; Resources</div>' + tags + '</div>'
        )

    status_colour = {'approved': '#34d399', 'rejected': '#f87171',
                     'pending': '#fbbf24', 'paid': '#a78bfa'}.get(booking.status, '#94a3b8')
    status_label  = 'PAID' if booking.status == 'paid' else booking.status.upper()
    campus_str    = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    id_str        = booking.user.student_number or booking.user.email
    org_str       = (' &mdash; ' + booking.user.organisation) if booking.user.organisation else ''

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        f'<title>Booking Confirmation #{booking.id:05d}</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700'
        '&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
        '<style>* { box-sizing:border-box; margin:0; padding:0; }'
        "body { font-family:'Sora',Arial,sans-serif; background:#f0f4f8;"
        '  display:flex; flex-direction:column; align-items:center; padding:40px 20px; }'
        '.page { background:#fff; width:794px; min-height:980px;'
        '  box-shadow:0 8px 40px rgba(0,0,0,.12); border-radius:4px; overflow:hidden; }'
        '@media print { body { background:#fff; padding:0; }'
        '  .page { box-shadow:none; width:100%; } .no-print { display:none!important; } }'
        '</style></head><body><div class="page">'

        # Header
        '<div style="background:linear-gradient(135deg,#1a3a5c,#2563a8);padding:36px 44px">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        '<div><div style="color:#fff;font-weight:700;font-size:1.25rem;margin-bottom:4px">'
        'Campus Facility Booking System</div>'
        '<div style="color:rgba(255,255,255,.5);font-size:.72rem;font-family:JetBrains Mono,monospace;'
        'text-transform:uppercase;letter-spacing:.08em">Durban University of Technology</div></div>'
        '<div style="text-align:right">'
        '<div style="color:rgba(255,255,255,.45);font-size:.65rem;font-family:JetBrains Mono,monospace;text-transform:uppercase">Ref No.</div>'
        f'<div style="color:#e8a020;font-size:1.7rem;font-weight:700;font-family:JetBrains Mono,monospace;line-height:1">#{booking.id:05d}</div>'
        '</div></div>'
        f'<div style="margin-top:20px;display:inline-flex;align-items:center;gap:8px;'
        f'background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);'
        f'border-radius:100px;padding:5px 14px">'
        f'<div style="width:8px;height:8px;border-radius:50%;background:{status_colour}"></div>'
        f'<span style="color:#fff;font-size:.8rem;font-weight:600">{status_label}</span></div></div>'

        # Info grid
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:28px 44px 0">'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Date</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem">{booking.booking_date.strftime("%d %B %Y")}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.booking_date.strftime("%A")}</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Time Slot</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem;font-family:JetBrains Mono,monospace">'
        f'{booking.start_time.strftime("%H:%M")} &ndash; {booking.end_time.strftime("%H:%M")}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.duration_hours:.1f} hours</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Facility</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1rem">{booking.facility.name}</div>'
        f'<div style="color:#64748b;font-size:.8rem">{booking.facility.location}{campus_str}</div></div>'
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px">'
        '<div style="font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;font-weight:700;margin-bottom:6px">Attendees</div>'
        f'<div style="font-weight:700;color:#1a3a5c;font-size:1.05rem">{booking.attendees}</div>'
        f'<div style="color:#64748b;font-size:.8rem">Capacity: {booking.facility.capacity}</div></div>'
        '</div>'

        # Details table
        '<div style="padding:24px 44px 0">'
        '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;'
        'color:#94a3b8;margin-bottom:10px;font-family:monospace">Booking Details</div>'
        '<table style="width:100%;border-collapse:collapse">'
        f'<tr><td style="{rs}">Booking Title</td><td style="{vs}">{booking.title}</td></tr>'
        f'<tr><td style="{rs}">Booked By</td><td style="{vs}">{booking.user.full_name}</td></tr>'
        f'<tr><td style="{rs}">ID / Number</td><td style="{vs};font-family:JetBrains Mono,monospace">{id_str}</td></tr>'
        f'<tr><td style="{rs}">Role</td><td style="{vs}">{booking.user.role.title()}{org_str}</td></tr>'
        f'{extra_rows}'
        f'<tr><td style="color:#888;font-size:.85rem;padding:8px 0">Submitted</td>'
        f'<td style="color:#1a3a5c;font-weight:600;font-size:.85rem;padding:8px 0">'
        f'{booking.created_at.strftime("%d %b %Y at %H:%M")}</td></tr>'
        '</table></div>'

        # Reason
        '<div style="padding:20px 44px 0">'
        '<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;'
        'color:#94a3b8;margin-bottom:8px;font-family:monospace">Reason for Booking</div>'
        f'<div style="background:#f8fafc;border-left:4px solid #e8a020;border-radius:0 8px 8px 0;'
        f'padding:14px 18px;color:#475569;font-size:.875rem;line-height:1.7">{booking.reason}</div></div>'

        f'{equipment_html}{qr_html}'

        # Footer
        '<div style="background:#f8fafc;border-top:2px solid #e2e8f0;padding:20px 44px;'
        'display:flex;justify-content:space-between;align-items:center;margin-top:20px">'
        '<div><div style="font-size:.8rem;font-weight:700;color:#1a3a5c">Campus Facility Booking System</div>'
        '<div style="font-size:.7rem;color:#94a3b8">Durban University of Technology</div>'
        '<div style="font-size:.7rem;color:#94a3b8">Official booking confirmation document</div></div>'
        '<div style="text-align:right">'
        f'<div style="font-size:.65rem;color:#cbd5e1;font-family:JetBrains Mono,monospace">Generated: {generated_at}</div>'
        f'<div style="font-size:.65rem;color:#cbd5e1;font-family:JetBrains Mono,monospace">CBS-{booking.id:05d}</div>'
        '</div></div></div>'

        # Print button (hidden when printing)
        '<div class="no-print" style="margin-top:20px;text-align:center">'
        '<button onclick="window.print()" style="background:#e8a020;color:#1a3a5c;border:none;'
        'padding:11px 30px;border-radius:8px;font-weight:700;font-size:.9rem;cursor:pointer;'
        "font-family:'Sora',sans-serif\">Print / Save as PDF</button>"
        '<a href="javascript:history.back()" '
        'style="color:#94a3b8;text-decoration:none;font-size:.8rem;margin-left:16px">Back to booking</a>'
        '</div></body></html>'
    )