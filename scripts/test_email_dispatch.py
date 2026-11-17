import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.email_service import EmailService


async def main():
    recipient = "sudhanshu.kumar@drcsystems.com"
    excel_path = Path("data/exports/leads_automation.xlsx")
    if not excel_path.exists():
        excel_path = None

    print(f"[TEST EMAIL] Initializing EmailService...")
    print(f"[TEST EMAIL] SMTP Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    print(f"[TEST EMAIL] SMTP User: {settings.SMTP_USER}")
    print(f"[TEST EMAIL] SMTP From: {settings.SMTP_FROM_EMAIL}")
    print(f"[TEST EMAIL] Target Recipient: {recipient}")

    svc = EmailService()
    if not svc.is_configured():
        print("[TEST EMAIL] [FAILED] SMTP credentials are not properly configured.")
        return

    stats = {
        "jobs_scraped": 15,
        "jobs_expanded": 8,
        "high_value_leads": 6,
    }

    print("[TEST EMAIL] Sending test email asynchronously...")
    result = await svc.send_excel_report_email_async(
        recipient_emails=[recipient],
        keyword="Full Stack Automation (Test)",
        excel_file_path=excel_path,
        stats=stats,
        subject_override="[Test Verification] Upwork Lead Intelligence Email Service Active",
    )
    print(f"[TEST EMAIL] Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
