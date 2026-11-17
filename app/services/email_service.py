import os
import smtplib
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosmtplib

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.email")


class EmailService:
    """Enterprise email notification service supporting attachments, diagnostics, and simulation modes."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.use_tls = settings.SMTP_USE_TLS

    def is_configured(self) -> bool:
        """Check if SMTP connection credentials are actively configured."""
        return bool(self.host and self.user and self.password)

    def _build_email_message(
        self,
        recipient_emails: List[str],
        subject: str,
        keyword: str,
        excel_file_path: Optional[Path] = None,
        stats: Optional[Dict[str, Any]] = None,
        error_logs: Optional[List[Dict[str, Any]]] = None,
        error_summary: Optional[str] = None,
    ) -> MIMEMultipart:
        """Construct a MIME multipart email with HTML body, attached Excel workbook, and diagnostic error log."""
        msg = MIMEMultipart("mixed")
        msg["From"] = self.from_email
        msg["To"] = ", ".join(recipient_emails)
        msg["Subject"] = subject

        stats = stats or {}
        jobs_count = stats.get("jobs_scraped", 0)
        expanded_count = stats.get("jobs_expanded", 0)
        high_value_count = stats.get("high_value_leads", 0)
        excel_name = excel_file_path.name if excel_file_path else "None (No workbook attached)"

        # Alternative container for plain text + html
        alt_part = MIMEMultipart("alternative")

        # Plain text fallback
        text_lines = [
            "Automated Upwork Lead Intelligence Report",
            f"Keyword: {keyword}",
            f"Jobs Scraped: {jobs_count}",
            f"Jobs Deep-Analyzed: {expanded_count}",
            f"High-Value Leads: {high_value_count}",
        ]
        if excel_file_path and excel_file_path.exists():
            text_lines.append(f"Attached Spreadsheet: {excel_file_path.name}")

        if error_summary:
            text_lines.append(f"\nExecution Notice: {error_summary}")
        if error_logs:
            text_lines.append(f"\nDiagnostic Errors ({len(error_logs)} captured):")
            for err in error_logs:
                text_lines.append(f" - Job {err.get('job_index', '?')}: {err.get('job_url', 'N/A')} -> {err.get('message', '')}")
            text_lines.append("See attached pipeline_execution_errors.log for full details.\n")

        alt_part.attach(MIMEText("\n".join(text_lines), "plain", "utf-8"))

        # HTML error card snippet
        error_html = ""
        if error_logs or error_summary:
            error_items = "".join(
                f"""<li style="margin-bottom: 4px;">
                    <strong>Job #{err.get('job_index', '?')}:</strong>
                    <span style="font-family: monospace; font-size: 11px;">{err.get('job_url', 'N/A')}</span>
                    <br/><span style="color: #b91c1c;">[{err.get('error_type', 'Error')}]: {err.get('message', '')}</span>
                </li>"""
                for err in (error_logs or [])
            )
            error_html = f"""
            <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; padding: 14px 16px; margin: 16px 0; border-radius: 6px;">
              <strong style="color: #92400e; font-size: 13px;">Pipeline Diagnostic Notice</strong>
              <p style="margin: 4px 0 8px 0; font-size: 12px; color: #78350f;">
                {error_summary or f"Encountered {len(error_logs)} issue(s) during deep inspection. All harvested data has been preserved in the workbook."}
              </p>
              {"<ul style='margin: 0; padding-left: 18px; font-size: 12px; color: #78350f;'>" + error_items + "</ul>" if error_logs else ""}
              {"<p style='margin: 8px 0 0 0; font-size: 11px; color: #92400e;'>A full diagnostic trace has been attached as pipeline_execution_errors.log.</p>" if error_logs else ""}
            </div>
            """

        # HTML body
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1a1a1a;
      background-color: #f7fafc;
      margin: 0;
      padding: 20px;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .header {{
      background: #1F4E78;
      color: #ffffff;
      padding: 24px;
      text-align: left;
    }}
    .header h2 {{
      margin: 0 0 6px 0;
      font-size: 20px;
      font-weight: 600;
    }}
    .header p {{
      margin: 0;
      font-size: 13px;
      color: #e2e8f0;
    }}
    .content {{
      padding: 24px;
    }}
    .metric-grid {{
      display: flex;
      gap: 12px;
      margin: 20px 0;
    }}
    .metric-box {{
      flex: 1;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 12px;
      text-align: center;
    }}
    .metric-value {{
      font-size: 22px;
      font-weight: 700;
      color: #1F4E78;
    }}
    .metric-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      margin-top: 4px;
    }}
    .footer {{
      border-top: 1px solid #e2e8f0;
      padding: 16px 24px;
      font-size: 12px;
      color: #64748b;
      background: #f8fafc;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>Automated Upwork Lead Intelligence</h2>
      <p>Scheduled Execution Report &bull; Keyword: <strong>{keyword}</strong></p>
    </div>
    <div class="content">
      <p>Your scheduled lead generation pipeline has completed execution.</p>

      {error_html}

      <!-- Metric Highlight Boxes -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin: 16px 0; border-collapse: separate; border-spacing: 8px 0;">
        <tr>
          <td width="33%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 6px; text-align: center;">
            <div style="font-size: 22px; font-weight: 700; color: #1F4E78;">{jobs_count}</div>
            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-top: 4px;">Jobs Scraped</div>
          </td>
          <td width="33%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 6px; text-align: center;">
            <div style="font-size: 22px; font-weight: 700; color: #1F4E78;">{expanded_count}</div>
            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-top: 4px;">Deeply Analyzed</div>
          </td>
          <td width="33%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 6px; text-align: center;">
            <div style="font-size: 22px; font-weight: 700; color: #1F4E78;">{high_value_count}</div>
            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-top: 4px;">Verified Leads</div>
          </td>
        </tr>
      </table>

      <!-- Pipeline Execution Details Table -->
      <table width="100%" cellpadding="8" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 6px; margin: 16px 0;">
        <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
          <td style="font-weight: 600; color: #475569;">Target Keyword</td>
          <td style="text-align: right; font-weight: 700; color: #1e293b;">{keyword}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="color: #475569;">Jobs Scraped from Feed</td>
          <td style="text-align: right; font-weight: 600;">{jobs_count}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="color: #475569;">Contracts Deeply Analyzed</td>
          <td style="text-align: right; font-weight: 600;">{expanded_count}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="color: #475569;">Decision Makers Resolved</td>
          <td style="text-align: right; font-weight: 600;">{high_value_count}</td>
        </tr>
        <tr>
          <td style="color: #475569;">Attached Master Workbook</td>
          <td style="text-align: right; font-family: monospace; font-size: 12px; color: #0284c7;">{excel_name}</td>
        </tr>
      </table>

      <p style="font-size: 13px; color: #475569;">
        Open the attached spreadsheet to inspect company identities, decision makers, verified contacts, and historical contractor spend.
      </p>
    </div>
    <div class="footer">
      Generated automatically by Upwork Lead Intelligence Platform.
    </div>
  </div>
</body>
</html>
"""
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        # Attach Excel file if present
        if excel_file_path and excel_file_path.exists():
            with open(excel_file_path, "rb") as f:
                attachment = MIMEBase(
                    "application",
                    "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{excel_file_path.name}\"",
                )
                msg.attach(attachment)
        elif excel_file_path:
            logger.warning(
                f"[EMAIL] Attachment path does not exist on disk: {excel_file_path}"
            )

        # Attach diagnostic error log if error_logs present
        if error_logs:
            log_lines = [
                "Upwork Automation - Pipeline Execution Error Diagnostics Log",
                f"Generated At (UTC): {datetime.now(timezone.utc).isoformat()}",
                f"Search Keyword: {keyword}",
                f"Total Errors Captured: {len(error_logs)}",
                "=" * 70,
                "",
            ]
            for err in error_logs:
                log_lines.append(f"Job Index: #{err.get('job_index', '?')}")
                log_lines.append(f"Job URL: {err.get('job_url', 'N/A')}")
                log_lines.append(f"Timestamp: {err.get('timestamp', 'N/A')}")
                log_lines.append(f"Error Type: {err.get('error_type', 'Exception')}")
                log_lines.append(f"Error Message: {err.get('message', '')}")
                log_lines.append("-" * 70)
            log_content = "\n".join(log_lines)

            err_attachment = MIMEBase("text", "plain")
            err_attachment.set_payload(log_content.encode("utf-8"))
            encoders.encode_base64(err_attachment)
            err_attachment.add_header(
                "Content-Disposition",
                'attachment; filename="pipeline_execution_errors.log"',
            )
            msg.attach(err_attachment)

        return msg

    async def send_excel_report_email_async(
        self,
        recipient_emails: List[str],
        keyword: str,
        excel_file_path: Optional[Path] = None,
        stats: Optional[Dict[str, Any]] = None,
        subject_override: Optional[str] = None,
        error_logs: Optional[List[Dict[str, Any]]] = None,
        error_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an Excel report asynchronously using aiosmtplib with fallback simulation."""
        excel_path_obj = Path(excel_file_path) if excel_file_path else None
        workbook_label = f" ({excel_path_obj.name})" if excel_path_obj else ""
        subject = subject_override or f"[Report] Upwork Leads for '{keyword}'{workbook_label}"

        if not recipient_emails:
            logger.warning("[EMAIL] [DISPATCH] Aborted: No recipient emails specified.")
            return {
                "status": "SKIPPED",
                "message": "No recipient emails provided",
                "recipients": [],
            }

        # Check configuration
        if not self.is_configured():
            logger.info(
                f"[EMAIL] [SIMULATION] SMTP credentials unconfigured. Simulating email dispatch to {recipient_emails} (keyword: '{keyword}')."
            )
            return {
                "status": "SIMULATED",
                "message": "Email simulated successfully (SMTP unconfigured)",
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
                "errors_captured": len(error_logs) if error_logs else 0,
            }

        try:
            logger.info(
                f"[EMAIL] [DISPATCH] Sending report email via {self.host}:{self.port} to {recipient_emails}..."
            )
            msg = self._build_email_message(
                recipient_emails=recipient_emails,
                subject=subject,
                keyword=keyword,
                excel_file_path=excel_path_obj,
                stats=stats,
                error_logs=error_logs,
                error_summary=error_summary,
            )

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls,
                timeout=30,
            )

            logger.info(
                f"[EMAIL] [SUCCESS] Report delivered to {len(recipient_emails)} recipients."
            )
            return {
                "status": "SENT",
                "message": "Email delivered successfully",
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
                "errors_captured": len(error_logs) if error_logs else 0,
            }
        except Exception as e:
            logger.error(
                f"[EMAIL] [FAILED] Could not send email via aiosmtplib: {e}",
                exc_info=True,
            )
            return {
                "status": "FAILED",
                "message": str(e),
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
            }

    def send_excel_report_email(
        self,
        recipient_emails: List[str],
        keyword: str,
        excel_file_path: Optional[Path] = None,
        stats: Optional[Dict[str, Any]] = None,
        subject_override: Optional[str] = None,
        error_logs: Optional[List[Dict[str, Any]]] = None,
        error_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for Celery workers and synchronous tasks."""
        excel_path_obj = Path(excel_file_path) if excel_file_path else None
        workbook_label = f" ({excel_path_obj.name})" if excel_path_obj else ""
        subject = subject_override or f"[Report] Upwork Leads for '{keyword}'{workbook_label}"

        if not recipient_emails:
            logger.warning("[EMAIL] [DISPATCH] Aborted: No recipient emails specified.")
            return {
                "status": "SKIPPED",
                "message": "No recipient emails provided",
                "recipients": [],
            }

        if not self.is_configured():
            logger.info(
                f"[EMAIL] [SIMULATION] SMTP unconfigured. Simulating dispatch to {recipient_emails} (keyword: '{keyword}')."
            )
            return {
                "status": "SIMULATED",
                "message": "Email simulated successfully (SMTP unconfigured)",
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
                "errors_captured": len(error_logs) if error_logs else 0,
            }

        try:
            logger.info(
                f"[EMAIL] [DISPATCH] Sending report via synchronous SMTP to {recipient_emails}..."
            )
            msg = self._build_email_message(
                recipient_emails=recipient_emails,
                subject=subject,
                keyword=keyword,
                excel_file_path=excel_path_obj,
                stats=stats,
                error_logs=error_logs,
                error_summary=error_summary,
            )

            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)

            logger.info(
                f"[EMAIL] [SUCCESS] Synchronous report delivered to {len(recipient_emails)} recipients."
            )
            return {
                "status": "SENT",
                "message": "Email delivered successfully",
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
                "errors_captured": len(error_logs) if error_logs else 0,
            }
        except Exception as e:
            logger.error(
                f"[EMAIL] [FAILED] Synchronous email delivery failed: {e}",
                exc_info=True,
            )
            return {
                "status": "FAILED",
                "message": str(e),
                "recipients": recipient_emails,
                "excel_file": str(excel_path_obj) if excel_path_obj else None,
            }


email_service = EmailService()
