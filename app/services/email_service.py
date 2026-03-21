"""
Email service for sending absence notifications.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@faceattendance.edu")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.sender_name = os.getenv("SENDER_NAME", "Face Attendance System")

    def send_absence_notification(
        self,
        student_email: str,
        student_name: str,
        period_name: str,
        class_name: str,
        absence_date: str,
        teacher_name: Optional[str] = None,
    ) -> bool:
        """
        Send absence notification email to student.

        Args:
            student_email: Student's email address
            student_name: Student's name
            period_name: Period name (e.g., "Period 1", "Math")
            class_name: Class/Section name
            absence_date: Date in YYYY-MM-DD format
            teacher_name: Optional teacher name for context

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = f"Attendance Alert: Absent in {period_name} on {absence_date}"

        # Format date for display
        try:
            from datetime import datetime
            date_obj = datetime.strptime(absence_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = absence_date

        # Create email body
        teacher_info = f"Teacher: {teacher_name}" if teacher_name else ""

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #d9534f;">Attendance Alert</h2>
                    
                    <p>Dear {student_name},</p>
                    
                    <p>This is to notify you that you were marked <strong>ABSENT</strong> for the following period:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #d9534f; margin: 20px 0;">
                        <p><strong>Period:</strong> {period_name}</p>
                        <p><strong>Class:</strong> {class_name}</p>
                        <p><strong>Date:</strong> {formatted_date}</p>
                        {f"<p><strong>{teacher_info}</strong></p>" if teacher_info else ""}
                    </div>
                    
                    <p>
                        If you believe this is an error or if you marked attendance but it wasn't recorded, 
                        please contact your teacher immediately.
                    </p>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 12px;">
                        This is an automated message from the Face Attendance System. 
                        Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """

        return self._send_email(student_email, subject, html_body)

    def send_bulk_absence_notifications(
        self, recipients: List[dict], period_name: str, class_name: str, absence_date: str
    ) -> dict:
        """
        Send absence notifications to multiple students.

        Args:
            recipients: List of dicts with keys: email, name, teacher_name
            period_name: Period name
            class_name: Class name
            absence_date: Date in YYYY-MM-DD format

        Returns:
            Dict with 'sent' and 'failed' counts
        """
        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            try:
                success = self.send_absence_notification(
                    student_email=recipient.get("email"),
                    student_name=recipient.get("name"),
                    period_name=period_name,
                    class_name=class_name,
                    absence_date=absence_date,
                    teacher_name=recipient.get("teacher_name"),
                )
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to {recipient.get('email')}: {str(e)}")
                failed_count += 1

        return {"sent": sent_count, "failed": failed_count}

    def _send_email(self, recipient_email: str, subject: str, html_body: str) -> bool:
        """
        Internal method to send email via SMTP.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if credentials are configured
            if not self.sender_email or not self.sender_password:
                logger.warning("Email credentials not configured. Skipping email.")
                return False

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient_email

            # Attach HTML body
            mime_text = MIMEText(html_body, "html")
            message.attach(mime_text)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())

            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            logger.error(
                "Failed to send email to %s via %s:%s as %s | error=%s",
                recipient_email,
                self.smtp_server,
                self.smtp_port,
                self.sender_email,
                str(e),
            )
            return False
