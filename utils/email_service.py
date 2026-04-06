"""
Email notification service.

All emails are suppressed in dev (MAIL_SUPPRESS_SEND=true).
Set MAIL_SUPPRESS_SEND=false and configure MAIL_* vars in .env for live sending.
For Gmail: enable 2FA and use an App Password as MAIL_PASSWORD.

PDF attachments are generated via reportlab — no weasyprint required.
Required packages: flask-mail  reportlab  qrcode[pil]  Pillow
"""
'''import os
from flask import current_app
from flask_mail import Message
from extensions import mail


# ── Internal helpers ───────────────────────────────────────────────────────────

def _send(subject, recipients, html_body, pdf_bytes=None, pdf_filename='booking.pdf'):
    """Core send with optional PDF attachment. Logs but never crashes the caller."""
    try:
        msg = Message(subject=subject, recipients=recipients, html=html_body)
        if pdf_bytes:
            msg.attach(
                filename     = pdf_filename,
                content_type = 'application/pdf',
                data         = pdf_bytes,
            )
        mail.send(msg)
        current_app.logger.info(
            f'[EMAIL OK] {subject} -> {recipients}'
            + (' (+PDF)' if pdf_bytes else '')
        )
    except Exception as e:
        current_app.logger.error(
            f'[EMAIL FAILED] {subject} -> {recipients} | '
            f'Error: {e} | Check MAIL_USERNAME / MAIL_PASSWORD in .env'
        )


def _pdf(booking):
    """Generate PDF bytes for a booking. Returns None on failure (non-fatal)."""
    try:
        from utils.pdf_generator import generate_pdf_bytes
        app_url = current_app.config.get('APP_URL', os.environ.get('APP_URL', ''))
        return generate_pdf_bytes(booking, app_url=app_url)
    except Exception as e:
        current_app.logger.warning(f'[PDF] Generation failed for booking {booking.id}: {e}')
        return None


def _pdf_filename(booking):
    return f"DUT_Booking_{booking.id:05d}_{booking.booking_date.strftime('%Y%m%d')}.pdf"


# ── Shared HTML wrapper ────────────────────────────────────────────────────────

_WRAP = """\
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body  { font-family:Arial,sans-serif; background:#f4f6f9; margin:0; padding:0; }
  .wrap { max-width:560px; margin:32px auto; background:#fff; border-radius:10px;
          overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,.08); }
  .hdr  { background:#1a3a5c; padding:24px 28px; }
  .hdr h1 { color:#fff; margin:0; font-size:1.1rem; font-weight:700; }
  .hdr p  { color:rgba(255,255,255,.55); margin:4px 0 0; font-size:.8rem; }
  .bdy  { padding:28px; }
  .bdy h2 { color:#1a3a5c; font-size:1rem; margin-top:0; }
  .bdy p  { color:#555; line-height:1.7; font-size:.88rem; }
  .box  { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;
          padding:14px 18px; margin:16px 0; }
  .row  { display:flex; justify-content:space-between; padding:5px 0;
          border-bottom:1px solid #eee; font-size:.85rem; }
  .row:last-child { border-bottom:none; }
  .lbl  { color:#888; }
  .val  { color:#1a3a5c; font-weight:600; }
  .ftr  { background:#f8fafc; padding:16px 28px; text-align:center;
          border-top:1px solid #e2e8f0; }
  .ftr p { color:#aaa; font-size:.72rem; margin:0; }
  .badge-approved { background:#d1fae5; color:#065f46; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
  .badge-rejected { background:#fde8e8; color:#9b1c1c; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
  .badge-pending  { background:#fef3c7; color:#92400e; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
</style></head><body>
<div class="wrap">
  <div class="hdr">
    <h1>DUT Campus Booking System</h1>
    <p>Durban University of Technology</p>
  </div>
  <div class="bdy">{BODY}</div>
  <div class="ftr"><p>Automated message &mdash; do not reply to this email.</p></div>
</div></body></html>
"""


def _wrap(body):
    return _WRAP.replace('{BODY}', body)


def _booking_rows(b, show_status=None):
    status_html = ''
    if show_status:
        css = {'approved': 'badge-approved', 'rejected': 'badge-rejected'}.get(
            show_status, 'badge-pending')
        status_html = (
            f'<div class="row"><span class="lbl">Status</span>'
            f'<span class="val"><span class="{css}">{show_status.upper()}</span></span></div>'
        )
    notes_html = (
        f'<div class="row"><span class="lbl">Admin Notes</span>'
        f'<span class="val">{b.admin_notes}</span></div>'
        if b.admin_notes else ''
    )
    return f"""
    <div class="box">
      <div class="row"><span class="lbl">Title</span><span class="val">{b.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{b.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span><span class="val">{b.facility.location}</span></div>
      <div class="row"><span class="lbl">Date</span><span class="val">{b.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span><span class="val">{b.start_time.strftime('%H:%M')} &ndash; {b.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{b.attendees}</span></div>
      {status_html}
      {notes_html}
    </div>"""


def _qr_section(booking, accent='#1a3a5c'):
    """Inline QR code block for email body (base64 PNG embedded in <img>)."""
    if not booking.qr_token:
        return ''
    try:
        from utils.qr_generator import generate_qr_base64
        app_url  = current_app.config.get('APP_URL', os.environ.get('APP_URL', 'http://127.0.0.1:5000'))
        qr_url   = f"{app_url.rstrip('/')}/checkin/{booking.qr_token}"
        qr_b64   = generate_qr_base64(qr_url, box_size=5)
        token_preview = booking.qr_token[:30] + '...'
        return f"""
    <div class="box" style="text-align:center">
      <div style="font-weight:700;color:{accent};margin-bottom:10px;font-size:.9rem">
        Check-in QR Code
      </div>
      <img src="{qr_b64}" alt="Check-in QR Code"
           style="width:130px;height:130px;border:2px solid {accent};
                  border-radius:8px;padding:4px;background:#fff">
      <div style="margin-top:8px;font-size:.7rem;color:#94a3b8;font-family:monospace">
        {token_preview}
      </div>
      <div style="margin-top:6px;font-size:.75rem;color:#475569">
        Present this QR code or the attached PDF to the facility attendant on arrival.
      </div>
    </div>"""
    except Exception:
        return ''


# ── Public email functions ─────────────────────────────────────────────────────

def send_booking_request(booking, admin_emails=None):
    """
    Sent when a user submits a new booking request.
      - User receives a 'pending review' notice.
      - Each admin receives an action-required alert.
    """
    # User notification
    user_body = f"""
    <h2>Booking Request Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking request has been submitted and is awaiting admin approval.</p>
    {_booking_rows(booking, show_status='pending')}
    <p>You will be notified by email once an administrator reviews your request.</p>"""
    _send(
        subject    = f'Booking Request Received - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(user_body),
    )

    # Admin notification(s)
    if admin_emails:
        for email in admin_emails:
            _send_admin_new_request(booking, email)


def _send_admin_new_request(booking, admin_email):
    body = f"""
    <h2>New Booking Request</h2>
    <p>A new booking request requires your review.</p>
    <div class="box">
      <div class="row"><span class="lbl">Submitted By</span>
        <span class="val">{booking.user.full_name} ({booking.user.student_number})</span></div>
      <div class="row"><span class="lbl">Title</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}</span></div>
    </div>
    <p>Log in to the admin panel to approve or reject this request.</p>"""
    _send(
        subject    = f'[Action Required] New Booking: {booking.title}',
        recipients = [admin_email],
        html_body  = _wrap(body),
    )


# Keep the old name as an alias — called directly from routes/bookings.py and routes/admin.py
def send_admin_new_request(booking, admin_email):
    _send_admin_new_request(booking, admin_email)


# Keep the old name — called from routes/bookings.py
def send_booking_confirmation(booking):
    """Legacy alias: sends the booking-request-received email to the user only."""
    user_body = f"""
    <h2>Booking Request Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking request has been submitted and is awaiting admin approval.</p>
    {_booking_rows(booking, show_status='pending')}
    <p>You will be notified by email once an administrator reviews your request.</p>"""
    _send(
        subject    = f'Booking Request Received -  {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(user_body),
    )


def send_booking_approved(booking):
    """
    Sent when an admin approves a booking.
    Attaches a PDF confirmation containing the QR code.
    """
    body = f"""
    <h2>Booking Approved</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been <strong>approved</strong>. Please arrive on time.</p>
    {_booking_rows(booking, show_status='approved')}
    {_qr_section(booking)}
    <p style="font-size:.8rem;color:#94a3b8">
      A PDF confirmation with your QR code is attached to this email.
      Print it or save it to your device &mdash; the facility attendant will scan it on arrival.
    </p>"""
    _send(
        subject      = f'Booking Approved -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_booking_rejected(booking):
    """Sent when an admin rejects a booking."""
    body = f"""
    <h2>Booking Not Approved</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Unfortunately your booking request was <strong>not approved</strong>.</p>
    {_booking_rows(booking, show_status='rejected')}
    <p>You are welcome to submit a new request with an alternative date or facility.</p>"""
    _send(
        subject    = f'Booking Not Approved - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_booking_cancelled(booking):
    """Sent when a booking is cancelled."""
    body = f"""
    <h2>Booking Cancelled</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been cancelled.</p>
    {_booking_rows(booking)}
    <p>Submit a new booking request if needed.</p>"""
    _send(
        subject    = f'Booking Cancelled -  {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_booking_reminder(booking):
    """
    30-minute reminder sent by the APScheduler job.
    Attaches a PDF confirmation containing the QR code.
    """
    campus_str = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    body = f"""
    <h2>Booking Reminder &mdash; Starting in 30 Minutes</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    This is a reminder that your booking starts soon. Please make your way to the facility now.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span>
        <span class="val">{booking.facility.location}{campus_str}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &#8211; {booking.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{booking.attendees}</span></div>
    </div>
    {_qr_section(booking)}
    <p style="font-size:.8rem;color:#94a3b8">
      If you can no longer attend, please cancel via the booking system before the session starts.
    </p>"""
    _send(
        subject      = f'Reminder: "{booking.title}" starts in 30 minutes',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_booking_rescheduled(booking, old_date, old_start, old_end):
    """Sent when a booking is rescheduled to a new date/time. Attaches updated PDF."""
    body = f"""
    <h2>Booking Rescheduled</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been successfully rescheduled. Here are the updated details:</p>

    <div class="box">
      <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #eee">
        <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
                    color:#94a3b8;font-weight:700;margin-bottom:4px">Previous Schedule</div>
        <div style="color:#94a3b8;text-decoration:line-through;font-size:.88rem">
          {old_date.strftime('%A, %d %B %Y')} &mdash;
          {old_start.strftime('%H:%M')} &ndash; {old_end.strftime('%H:%M')}
        </div>
      </div>
      <div>
        <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
                    color:#065f46;font-weight:700;margin-bottom:4px">New Schedule</div>
        <div style="color:#1a3a5c;font-weight:700;font-size:.95rem">
          {booking.booking_date.strftime('%A, %d %B %Y')} &mdash;
          {booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}
        </div>
      </div>
    </div>

    {_booking_rows(booking, show_status=booking.status)}
    <p style="font-size:.8rem;color:#94a3b8">
      Your QR code remains valid for the new date. An updated PDF confirmation is attached.
    </p>"""
    _send(
        subject      = f'Booking Rescheduled -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_external_booking_confirmed(booking):
    """
    Sent to external users after a successful PayFast payment.
    Attaches a PDF confirmation with QR code.
    """
    amount_str = f'R{float(booking.amount_paid):.2f}' if booking.amount_paid else ''
    campus_str = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    amount_row = (
        f'<div class="row"><span class="lbl">Amount Paid</span>'
        f'<span class="val" style="color:#5b21b6;font-weight:700">{amount_str}</span></div>'
        if amount_str else ''
    )
    body = f"""
    <h2>Booking Confirmed &amp; Payment Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Thank you for your payment. Your facility booking has been confirmed.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span>
        <span class="val">{booking.facility.location}{campus_str}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{booking.attendees}</span></div>
      {amount_row}
      <div class="row"><span class="lbl">Status</span>
        <span class="val" style="color:#5b21b6;font-weight:700">PAID</span></div>
    </div>
    {_qr_section(booking, accent='#5b21b6')}
    <p style="font-size:.8rem;color:#94a3b8">
      A PDF confirmation with your QR code is attached. Print it or save it &mdash; the facility
      attendant will scan it when you arrive. A 30-minute reminder will also be sent before your session.
    </p>"""
    _send(
        subject      = f'Booking Confirmed &amp; Paid -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_checkin_confirmed(booking, scanned_by):
    """Sent when a staff member scans a user's QR code to confirm attendance."""
    body = f"""
    <h2>Attendance Confirmed</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your attendance for the following booking has been confirmed.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Checked In At</span>
        <span class="val">{booking.attended_at.strftime('%H:%M on %d %b %Y')}</span></div>
      <div class="row"><span class="lbl">Verified By</span>
        <span class="val">{scanned_by.full_name}</span></div>
    </div>
    <p style="font-size:.8rem;color:#94a3b8">Thank you for using the Campus Facility Booking System.</p>"""
    _send(
        subject    = f'Attendance Confirmed - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_password_reset(user, reset_url):
    """Send a password reset link to the user."""
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Hi <strong>{user.name}</strong>,<br>
    We received a request to reset the password for your account.
    Click the button below to set a new password.
    This link expires in <strong>1 hour</strong>.</p>
    <div style="text-align:center;margin:28px 0">
      <a href="{reset_url}"
         style="background:#1a3a5c;color:#fff;text-decoration:none;padding:12px 28px;
                border-radius:8px;font-weight:700;font-size:.9rem;display:inline-block">
        Reset My Password
      </a>
    </div>
    <div class="box" style="font-size:.8rem;color:#888">
      <strong>Did not request this?</strong> You can safely ignore this email &mdash;
      your password will not change unless you click the link above.
    </div>
    <p style="font-size:.78rem;color:#aaa;margin-top:12px">
      Or copy this link:
      <span style="font-family:monospace;color:#1a3a5c">{reset_url}</span>
    </p>"""
    _send(
        subject    = 'Reset Your Campus Booking Password',
        recipients = [user.email],
        html_body  = _wrap(body),
    )


def send_welcome_oauth(user):
    """Welcome email for users who sign up via Microsoft OAuth."""
    body = f"""
    <h2>Welcome to Campus Facility Booking</h2>
    <p>Hi <strong>{user.name}</strong>,<br>
    Your account has been created using your <strong>Microsoft account</strong>.
    You can sign in anytime using the <em>Sign in with Microsoft</em> button.</p>
    <div class="box">
      <div class="row"><span class="lbl">Name</span><span class="val">{user.full_name}</span></div>
      <div class="row"><span class="lbl">Student Number</span><span class="val">{user.student_number}</span></div>
      <div class="row"><span class="lbl">Email</span><span class="val">{user.email}</span></div>
      <div class="row"><span class="lbl">Role</span><span class="val">{user.role.title()}</span></div>
    </div>
    <p>Start by browsing available facilities and submitting your first booking request.</p>"""
    _send(
        subject    = 'Welcome to Campus Facility Booking System',
        recipients = [user.email],
        html_body  = _wrap(body),
    )
'''


"""
Email notification service.

All emails are suppressed in dev (MAIL_SUPPRESS_SEND=true).
Set MAIL_SUPPRESS_SEND=false and configure MAIL_* vars in .env for live sending.
For Gmail: enable 2FA and use an App Password as MAIL_PASSWORD.

PDF attachments are generated via reportlab — no weasyprint required.
Required packages: flask-mail  reportlab  qrcode[pil]  Pillow
"""
import os
from flask import current_app
from flask_mail import Message
from extensions import mail


# ── Internal helpers ───────────────────────────────────────────────────────────

def _send(subject, recipients, html_body, pdf_bytes=None, pdf_filename='booking.pdf'):
    """Core send with optional PDF attachment. Logs but never crashes the caller."""
    try:
        msg = Message(subject=subject, recipients=recipients, html=html_body)
        if pdf_bytes:
            msg.attach(
                filename     = pdf_filename,
                content_type = 'application/pdf',
                data         = pdf_bytes,
            )
        mail.send(msg)
        current_app.logger.info(
            f'[EMAIL OK] {subject} -> {recipients}'
            + (' (+PDF)' if pdf_bytes else '')
        )
    except Exception as e:
        current_app.logger.error(
            f'[EMAIL FAILED] {subject} -> {recipients} | '
            f'Error: {e} | Check MAIL_USERNAME / MAIL_PASSWORD in .env'
        )


def _pdf(booking):
    """Generate PDF bytes for a booking. Returns None on failure (non-fatal)."""
    try:
        from utils.pdf_generator import generate_pdf_bytes
        # APP_URL is resolved inside generate_pdf_bytes from os.getenv — no need to pass it
        return generate_pdf_bytes(booking)
    except Exception as e:
        current_app.logger.warning(f'[PDF] Generation failed for booking {booking.id}: {e}')
        return None


def _pdf_filename(booking):
    return f"DUT_Booking_{booking.id:05d}_{booking.booking_date.strftime('%Y%m%d')}.pdf"


# ── Shared HTML wrapper ────────────────────────────────────────────────────────

_WRAP = """\
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body  { font-family:Arial,sans-serif; background:#f4f6f9; margin:0; padding:0; }
  .wrap { max-width:560px; margin:32px auto; background:#fff; border-radius:10px;
          overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,.08); }
  .hdr  { background:#1a3a5c; padding:24px 28px; }
  .hdr h1 { color:#fff; margin:0; font-size:1.1rem; font-weight:700; }
  .hdr p  { color:rgba(255,255,255,.55); margin:4px 0 0; font-size:.8rem; }
  .bdy  { padding:28px; }
  .bdy h2 { color:#1a3a5c; font-size:1rem; margin-top:0; }
  .bdy p  { color:#555; line-height:1.7; font-size:.88rem; }
  .box  { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;
          padding:14px 18px; margin:16px 0; }
  .row  { display:flex; justify-content:space-between; padding:5px 0;
          border-bottom:1px solid #eee; font-size:.85rem; }
  .row:last-child { border-bottom:none; }
  .lbl  { color:#888; }
  .val  { color:#1a3a5c; font-weight:600; }
  .ftr  { background:#f8fafc; padding:16px 28px; text-align:center;
          border-top:1px solid #e2e8f0; }
  .ftr p { color:#aaa; font-size:.72rem; margin:0; }
  .badge-approved { background:#d1fae5; color:#065f46; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
  .badge-rejected { background:#fde8e8; color:#9b1c1c; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
  .badge-pending  { background:#fef3c7; color:#92400e; padding:2px 10px;
                    border-radius:100px; font-size:.75rem; font-weight:700; }
</style></head><body>
<div class="wrap">
  <div class="hdr">
    <h1>DUT Campus Booking System</h1>
    <p>Durban University of Technology</p>
  </div>
  <div class="bdy">{BODY}</div>
  <div class="ftr"><p>Automated message &mdash; do not reply to this email.</p></div>
</div></body></html>
"""


def _wrap(body):
    return _WRAP.replace('{BODY}', body)


def _booking_rows(b, show_status=None):
    status_html = ''
    if show_status:
        css = {'approved': 'badge-approved', 'rejected': 'badge-rejected'}.get(
            show_status, 'badge-pending')
        status_html = (
            f'<div class="row"><span class="lbl">Status</span>'
            f'<span class="val"><span class="{css}">{show_status.upper()}</span></span></div>'
        )
    notes_html = (
        f'<div class="row"><span class="lbl">Admin Notes</span>'
        f'<span class="val">{b.admin_notes}</span></div>'
        if b.admin_notes else ''
    )
    return f"""
    <div class="box">
      <div class="row"><span class="lbl">Title</span><span class="val">{b.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{b.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span><span class="val">{b.facility.location}</span></div>
      <div class="row"><span class="lbl">Date</span><span class="val">{b.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span><span class="val">{b.start_time.strftime('%H:%M')} &ndash; {b.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{b.attendees}</span></div>
      {status_html}
      {notes_html}
    </div>"""


def _qr_section(booking, accent='#1a3a5c'):
    """Inline QR code block for email body (base64 PNG embedded in <img>)."""
    if not booking.qr_token:
        return ''
    try:
        from utils.qr_generator import generate_qr_base64
        app_url  = os.getenv('APP_URL', 'http://127.0.0.1:5000')
        qr_url   = f"{app_url.rstrip('/')}/checkin/{booking.qr_token}"
        qr_b64   = generate_qr_base64(qr_url, box_size=5)
        token_preview = booking.qr_token[:30] + '...'
        return f"""
    <div class="box" style="text-align:center">
      <div style="font-weight:700;color:{accent};margin-bottom:10px;font-size:.9rem">
        Check-in QR Code
      </div>
      <img src="{qr_b64}" alt="Check-in QR Code"
           style="width:130px;height:130px;border:2px solid {accent};
                  border-radius:8px;padding:4px;background:#fff">
      <div style="margin-top:8px;font-size:.7rem;color:#94a3b8;font-family:monospace">
        {token_preview}
      </div>
      <div style="margin-top:6px;font-size:.75rem;color:#475569">
        Present this QR code or the attached PDF to the facility attendant on arrival.
      </div>
    </div>"""
    except Exception:
        return ''


# ── Public email functions ─────────────────────────────────────────────────────

def send_booking_request(booking, admin_emails=None):
    """
    Sent when a user submits a new booking request.
      - User receives a 'pending review' notice.
      - Each admin receives an action-required alert.
    """
    # User notification
    user_body = f"""
    <h2>Booking Request Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking request has been submitted and is awaiting admin approval.</p>
    {_booking_rows(booking, show_status='pending')}
    <p>You will be notified by email once an administrator reviews your request.</p>"""
    _send(
        subject    = f'Booking Request Received - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(user_body),
    )

    # Admin notification(s)
    if admin_emails:
        for email in admin_emails:
            _send_admin_new_request(booking, email)


def _send_admin_new_request(booking, admin_email):
    body = f"""
    <h2>New Booking Request</h2>
    <p>A new booking request requires your review.</p>
    <div class="box">
      <div class="row"><span class="lbl">Submitted By</span>
        <span class="val">{booking.user.full_name} ({booking.user.student_number})</span></div>
      <div class="row"><span class="lbl">Title</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}</span></div>
    </div>
    <p>Log in to the admin panel to approve or reject this request.</p>"""
    _send(
        subject    = f'[Action Required] New Booking: {booking.title}',
        recipients = [admin_email],
        html_body  = _wrap(body),
    )


# Keep the old name as an alias — called directly from routes/bookings.py and routes/admin.py
def send_admin_new_request(booking, admin_email):
    _send_admin_new_request(booking, admin_email)


# Keep the old name — called from routes/bookings.py
def send_booking_confirmation(booking):
    """Legacy alias: sends the booking-request-received email to the user only."""
    user_body = f"""
    <h2>Booking Request Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking request has been submitted and is awaiting admin approval.</p>
    {_booking_rows(booking, show_status='pending')}
    <p>You will be notified by email once an administrator reviews your request.</p>"""
    _send(
        subject    = f'Booking Request Received -  {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(user_body),
    )


def send_booking_approved(booking):
    """
    Sent when an admin approves a booking.
    Attaches a PDF confirmation containing the QR code.
    """
    body = f"""
    <h2>Booking Approved</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been <strong>approved</strong>. Please arrive on time.</p>
    {_booking_rows(booking, show_status='approved')}
    {_qr_section(booking)}
    <p style="font-size:.8rem;color:#94a3b8">
      A PDF confirmation with your QR code is attached to this email.
      Print it or save it to your device &mdash; the facility attendant will scan it on arrival.
    </p>"""
    _send(
        subject      = f'Booking Approved -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_booking_rejected(booking):
    """Sent when an admin rejects a booking."""
    body = f"""
    <h2>Booking Not Approved</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Unfortunately your booking request was <strong>not approved</strong>.</p>
    {_booking_rows(booking, show_status='rejected')}
    <p>You are welcome to submit a new request with an alternative date or facility.</p>"""
    _send(
        subject    = f'Booking Not Approved - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_booking_cancelled(booking):
    """Sent when a booking is cancelled."""
    body = f"""
    <h2>Booking Cancelled</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been cancelled.</p>
    {_booking_rows(booking)}
    <p>Submit a new booking request if needed.</p>"""
    _send(
        subject    = f'Booking Cancelled -  {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_booking_reminder(booking):
    """
    30-minute reminder sent by the APScheduler job.
    Attaches a PDF confirmation containing the QR code.
    """
    campus_str = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    body = f"""
    <h2>Booking Reminder &mdash; Starting in 30 Minutes</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    This is a reminder that your booking starts soon. Please make your way to the facility now.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span>
        <span class="val">{booking.facility.location}{campus_str}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &#8211; {booking.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{booking.attendees}</span></div>
    </div>
    {_qr_section(booking)}
    <p style="font-size:.8rem;color:#94a3b8">
      If you can no longer attend, please cancel via the booking system before the session starts.
    </p>"""
    _send(
        subject      = f'Reminder: "{booking.title}" starts in 30 minutes',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_booking_rescheduled(booking, old_date, old_start, old_end):
    """Sent when a booking is rescheduled to a new date/time. Attaches updated PDF."""
    body = f"""
    <h2>Booking Rescheduled</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your booking has been successfully rescheduled. Here are the updated details:</p>

    <div class="box">
      <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #eee">
        <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
                    color:#94a3b8;font-weight:700;margin-bottom:4px">Previous Schedule</div>
        <div style="color:#94a3b8;text-decoration:line-through;font-size:.88rem">
          {old_date.strftime('%A, %d %B %Y')} &mdash;
          {old_start.strftime('%H:%M')} &ndash; {old_end.strftime('%H:%M')}
        </div>
      </div>
      <div>
        <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
                    color:#065f46;font-weight:700;margin-bottom:4px">New Schedule</div>
        <div style="color:#1a3a5c;font-weight:700;font-size:.95rem">
          {booking.booking_date.strftime('%A, %d %B %Y')} &mdash;
          {booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}
        </div>
      </div>
    </div>

    {_booking_rows(booking, show_status=booking.status)}
    <p style="font-size:.8rem;color:#94a3b8">
      Your QR code remains valid for the new date. An updated PDF confirmation is attached.
    </p>"""
    _send(
        subject      = f'Booking Rescheduled -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_external_booking_confirmed(booking):
    """
    Sent to external users after a successful PayFast payment.
    Attaches a PDF confirmation with QR code.
    """
    amount_str = f'R{float(booking.amount_paid):.2f}' if booking.amount_paid else ''
    campus_str = (' &middot; ' + booking.facility.campus) if booking.facility.campus else ''
    amount_row = (
        f'<div class="row"><span class="lbl">Amount Paid</span>'
        f'<span class="val" style="color:#5b21b6;font-weight:700">{amount_str}</span></div>'
        if amount_str else ''
    )
    body = f"""
    <h2>Booking Confirmed &amp; Payment Received</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Thank you for your payment. Your facility booking has been confirmed.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Location</span>
        <span class="val">{booking.facility.location}{campus_str}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Time</span>
        <span class="val">{booking.start_time.strftime('%H:%M')} &ndash; {booking.end_time.strftime('%H:%M')}</span></div>
      <div class="row"><span class="lbl">Attendees</span><span class="val">{booking.attendees}</span></div>
      {amount_row}
      <div class="row"><span class="lbl">Status</span>
        <span class="val" style="color:#5b21b6;font-weight:700">PAID</span></div>
    </div>
    {_qr_section(booking, accent='#5b21b6')}
    <p style="font-size:.8rem;color:#94a3b8">
      A PDF confirmation with your QR code is attached. Print it or save it &mdash; the facility
      attendant will scan it when you arrive. A 30-minute reminder will also be sent before your session.
    </p>"""
    _send(
        subject      = f'Booking Confirmed &amp; Paid -  {booking.title}',
        recipients   = [booking.user.email],
        html_body    = _wrap(body),
        pdf_bytes    = _pdf(booking),
        pdf_filename = _pdf_filename(booking),
    )


def send_checkin_confirmed(booking, scanned_by):
    """Sent when a staff member scans a user's QR code to confirm attendance."""
    body = f"""
    <h2>Attendance Confirmed</h2>
    <p>Hi <strong>{booking.user.name}</strong>,<br>
    Your attendance for the following booking has been confirmed.</p>
    <div class="box">
      <div class="row"><span class="lbl">Booking</span><span class="val">{booking.title}</span></div>
      <div class="row"><span class="lbl">Facility</span><span class="val">{booking.facility.name}</span></div>
      <div class="row"><span class="lbl">Date</span>
        <span class="val">{booking.booking_date.strftime('%A, %d %B %Y')}</span></div>
      <div class="row"><span class="lbl">Checked In At</span>
        <span class="val">{booking.attended_at.strftime('%H:%M on %d %b %Y')}</span></div>
      <div class="row"><span class="lbl">Verified By</span>
        <span class="val">{scanned_by.full_name}</span></div>
    </div>
    <p style="font-size:.8rem;color:#94a3b8">Thank you for using the Campus Facility Booking System.</p>"""
    _send(
        subject    = f'Attendance Confirmed - {booking.title}',
        recipients = [booking.user.email],
        html_body  = _wrap(body),
    )


def send_password_reset(user, reset_url):
    """Send a password reset link to the user."""
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Hi <strong>{user.name}</strong>,<br>
    We received a request to reset the password for your account.
    Click the button below to set a new password.
    This link expires in <strong>1 hour</strong>.</p>
    <div style="text-align:center;margin:28px 0">
      <a href="{reset_url}"
         style="background:#1a3a5c;color:#fff;text-decoration:none;padding:12px 28px;
                border-radius:8px;font-weight:700;font-size:.9rem;display:inline-block">
        Reset My Password
      </a>
    </div>
    <div class="box" style="font-size:.8rem;color:#888">
      <strong>Did not request this?</strong> You can safely ignore this email &mdash;
      your password will not change unless you click the link above.
    </div>
    <p style="font-size:.78rem;color:#aaa;margin-top:12px">
      Or copy this link:
      <span style="font-family:monospace;color:#1a3a5c">{reset_url}</span>
    </p>"""
    _send(
        subject    = 'Reset Your Campus Booking Password',
        recipients = [user.email],
        html_body  = _wrap(body),
    )


def send_welcome_oauth(user):
    """Welcome email for users who sign up via Microsoft OAuth."""
    body = f"""
    <h2>Welcome to Campus Facility Booking</h2>
    <p>Hi <strong>{user.name}</strong>,<br>
    Your account has been created using your <strong>Microsoft account</strong>.
    You can sign in anytime using the <em>Sign in with Microsoft</em> button.</p>
    <div class="box">
      <div class="row"><span class="lbl">Name</span><span class="val">{user.full_name}</span></div>
      <div class="row"><span class="lbl">Student Number</span><span class="val">{user.student_number}</span></div>
      <div class="row"><span class="lbl">Email</span><span class="val">{user.email}</span></div>
      <div class="row"><span class="lbl">Role</span><span class="val">{user.role.title()}</span></div>
    </div>
    <p>Start by browsing available facilities and submitting your first booking request.</p>"""
    _send(
        subject    = 'Welcome to Campus Facility Booking System',
        recipients = [user.email],
        html_body  = _wrap(body),
    )