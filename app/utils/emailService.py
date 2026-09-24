import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from app.config import settings


APP_NAME = settings.APP_NAME
SENDER_EMAIL = settings.SENDER_EMAIL
SENDER_PASSWORD = settings.SENDER_PASSWORD

def build_otp_html(otp: str, expiry_minutes: int = 10, full_name: str | None = None) -> str:
    """Return an HTML string for the OTP email."""
    name_line = f"<p style='margin:0 0 18px 0;font-size:16px;'>Hi {full_name},</p>" if full_name else ""
    return f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Your OTP Code</title>
      </head>
      <body style="margin:0;padding:0;background:#f4f6f8;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;">
        <table role="presentation" width="100%" style="max-width:600px;margin:30px auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 16px rgba(16,24,40,0.08);">
          <tr>
            <td style="padding:24px 28px;">
              <h2 style="margin:0 0 8px 0;font-size:20px;color:#0f172a;">Email Verification</h2>
              {name_line}
              <p style="margin:0 0 18px 0;color:#475569;">
                Use the code below to verify your email address. This code will expire in <strong>{expiry_minutes} minutes</strong>.
              </p>

              <div style="display:flex;justify-content:center;margin:18px 0;">
                <div style="background:#f1f5f9;border-radius:8px;padding:18px 26px;text-align:center;box-shadow:inset 0 -1px 0 rgba(15,23,42,0.03);">
                  <p style="margin:0;font-size:14px;color:#94a3b8">Your verification code</p>
                  <p style="margin:8px 0 0 0;font-size:28px;letter-spacing:4px;font-weight:700;color:#0b61ff">{otp}</p>
                </div>
              </div>

              <hr style="border:none;border-top:1px solid #eef2f7;margin:20px 0;" />

              <p style="margin:0;color:#94a3b8;font-size:13px;">
                If you didn't request this, you can safely ignore this email. For help, reply to support.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#0b254b;color:#dbeafe;padding:14px 28px;text-align:center;font-size:13px;">
              <div style="max-width:520px;margin:0 auto;">
                <span>{APP_NAME} • Do not share your code</span>
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

def build_plain_text(otp: str, expiry_minutes: int = 10, full_name: str | None = None) -> str:
    name_line = f"Hi {full_name},\n\n" if full_name else ""
    return (
        f"{name_line}"
        f"Use this code to verify your email: {otp}\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        "If you did not request this, please ignore this message.\n"
    )

def send_otp_email(receiver_email: str, otp: str, expiry_minutes: int = 10, full_name: str | None = None) -> bool:
    """
    Send a styled HTML OTP email with a plain-text fallback.
    Returns True if sending succeeded, False otherwise.
    """
    # Build message container
    message = MIMEMultipart("alternative")
    message["Subject"] = "Your Email Verification Code"
    message["From"] = formataddr(("PTI-e-SIWES", SENDER_EMAIL))
    message["To"] = receiver_email

    # Build parts
    text_part = build_plain_text(otp, expiry_minutes, full_name)
    html_part = build_otp_html(otp, expiry_minutes, full_name)

    # Attach parts (plain first, then HTML)
    message.attach(MIMEText(text_part, "plain"))
    message.attach(MIMEText(html_part, "html"))

    try:
        # with smtplib.SMTP("mail.privateemail.com", 587) as server:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
          server.ehlo()
          server.starttls()
          server.ehlo()
          server.login(SENDER_EMAIL, SENDER_PASSWORD)
          server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
        return True
    except Exception as e:
        # In prod, log this to your logging system (not print)
        print("Failed to send OTP email:", e)
        return False

