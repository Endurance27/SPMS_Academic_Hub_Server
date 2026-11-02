from typing import Optional

import aiohttp
from loguru import logger

from app.core.config import settings


MAILTRAP_SEND_URL = "https://send.api.mailtrap.io/api/send"


class EmailService:

    def __init__(self) -> None:
        self._api_key = settings.MAILTRAP_API_KEY
        self._sender_email = settings.MAILTRAP_SENDER_EMAIL
        self._sender_name = settings.MAILTRAP_SENDER_NAME
        self._frontend_url = settings.FRONTEND_URL.rstrip("/")

    async def _send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        if not self._api_key:
            logger.warning(
                "MAILTRAP_API_KEY not configured — email not sent | to={} subject={}",
                to_email,
                subject,
            )
            return False

        payload = {
            "from": {"email": self._sender_email, "name": self._sender_name},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "html": html_body,
        }
        if text_body:
            payload["text"] = text_body

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=15)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    MAILTRAP_SEND_URL, json=payload, headers=headers
                ) as response:
                    body = await response.text()

                    if response.status in (200, 201):
                        logger.info("Email sent | to={} subject={}", to_email, subject)
                        return True

                    logger.error(
                        "Mailtrap API error | status={} body={}", response.status, body
                    )
                    return False
        except aiohttp.ClientError as exc:
            logger.error("Mailtrap request failed | to={} error={}", to_email, exc)
            return False

    # ------------------------------------------------------------------
    # Invitation emails
    # ------------------------------------------------------------------

    async def send_invitation_email(
        self,
        to_email: str,
        user_name: str,
        role: str,
        invitation_token: str,
        department_name: Optional[str] = None,
        temporary_password: Optional[str] = None,
    ) -> bool:
        accept_url = f"{self._frontend_url}/accept-invitation?token={invitation_token}"
        login_url = f"{self._frontend_url}/login"

        role_label = {
            "department": "Department Administrator",
            "lecturer": "Faculty Member",
            "super": "Super Administrator",
            "student": "Student",
        }.get(role, role.title())

        dept_line = f" for <strong>{department_name}</strong>" if department_name else ""

        credentials_html = ""
        credentials_text = ""
        if temporary_password:
            credentials_html = f"""
            <div style="background: #f8f9fc; border-radius: 8px; padding: 20px 24px; margin: 24px 0; border: 1px solid #e2e8f0;">
                <p style="color: #1a365d; font-weight: 600; font-size: 14px; margin: 0 0 16px; text-transform: uppercase; letter-spacing: 0.5px;">
                    Your Login Credentials
                </p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; font-size: 13px; width: 140px;">Email Address</td>
                        <td style="padding: 8px 0; color: #1e293b; font-family: 'SF Mono', SFMono-Regular, Consolas, monospace; font-size: 14px; font-weight: 500;">{to_email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; font-size: 13px; border-top: 1px solid #e2e8f0;">Temporary Password</td>
                        <td style="padding: 8px 0; color: #1e293b; font-family: 'SF Mono', SFMono-Regular, Consolas, monospace; font-size: 14px; font-weight: 600; border-top: 1px solid #e2e8f0;">{temporary_password}</td>
                    </tr>
                </table>
                <p style="color: #94a3b8; font-size: 12px; margin: 12px 0 0;">
                    Please keep these credentials confidential.
                </p>
            </div>
            """
            credentials_text = (
                f"Email Address: {to_email}\n"
                f"Temporary Password: {temporary_password}\n"
                "Please keep these credentials confidential.\n\n"
            )

        subject = f"You've been invited to {self._sender_name}"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #0b3d91 0%, #1a56c4 100%); padding: 32px 40px; border-radius: 8px 8px 0 0;">
                <h1 style="color: #ffffff; font-size: 20px; font-weight: 600; margin: 0;">{self._sender_name}</h1>
                <p style="color: rgba(255,255,255,0.8); font-size: 13px; margin: 4px 0 0;">School of Physical and Mathematical Sciences</p>
            </div>

            <!-- Body -->
            <div style="padding: 32px 40px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #1a365d; font-size: 22px; margin: 0 0 8px;">Welcome to {self._sender_name}</h2>
                <p style="color: #475569; line-height: 1.7; font-size: 15px; margin: 16px 0;">
                    Hello &#x1F44B;,
                </p>
                <p style="color: #475569; line-height: 1.7; font-size: 15px; margin: 0 0 8px;">
                    You've been invited to join as a <strong style="color: #1a365d;">{role_label}</strong>{dept_line}.
                    Click the button below to set your password and activate your account.
                </p>

                {credentials_html}

                <!-- How to log in -->
                <div style="margin: 24px 0;">
                    <p style="color: #1a365d; font-weight: 600; font-size: 14px; margin: 0 0 12px;">How to log in</p>
                    <ol style="color: #475569; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
                        <li>Click the <strong>Activate Your Account</strong> button below.</li>
                        <li>Enter your email address: <strong>{to_email}</strong></li>
                        <li>Enter the temporary password provided above.</li>
                        <li>For security, you will be required to create a new password before continuing.</li>
                    </ol>
                </div>

                <!-- CTA Button -->
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{accept_url}"
                       style="display: inline-block; background: #0b3d91; color: #ffffff; padding: 14px 40px;
                              border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 15px;
                              box-shadow: 0 2px 4px rgba(11,61,145,0.25);">
                        Activate Your Account
                    </a>
                </div>

                <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; text-align: center;">
                    If the button above doesn't work, copy and paste this link into your browser:<br/>
                    <a href="{accept_url}" style="color: #0b3d91; word-break: break-all;">{accept_url}</a>
                </p>

                <!-- Security Notice -->
                <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 18px; margin: 24px 0; border-radius: 0 6px 6px 0;">
                    <p style="color: #92400e; font-weight: 600; font-size: 13px; margin: 0 0 6px;">Security Notice</p>
                    <p style="color: #78350f; font-size: 13px; margin: 0; line-height: 1.5;">
                        This is a temporary password issued for your initial login. You will be required to change it immediately after signing in.
                        Do not share your password with anyone. {self._sender_name} staff will never ask you to disclose your password by email or telephone.
                    </p>
                </div>

                <p style="color: #94a3b8; font-size: 13px; text-align: center; margin: 24px 0 0;">
                    This invitation expires in 7 days. If you did not expect this email, you can safely ignore it.
                </p>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding: 20px 40px;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    &copy; {self._sender_name}. All rights reserved.
                </p>
            </div>
        </div>
        """

        text_body = (
            f"Hello,\n\n"
            f"You've been invited to join {self._sender_name} as a {role_label}"
            f"{dept_line.replace('<strong>', '').replace('</strong>', '')}.\n\n"
            f"{credentials_text}"
            f"How to log in:\n"
            f"1. Open the activation link below.\n"
            f"2. Enter your email address: {to_email}\n"
            f"3. Enter the temporary password provided above.\n"
            f"4. You will be required to create a new password before continuing.\n\n"
            f"Activate your account: {accept_url}\n\n"
            f"This invitation expires in 7 days."
        )

        return await self._send(to_email, user_name, subject, html_body, text_body)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def send_password_reset_code_email(
        self,
        to_email: str,
        user_name: str,
        reset_code: str,
        ip_address: str,
        user_agent: str,
    ) -> bool:
        subject = f"Your password reset code — {self._sender_name}"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 0;">
            <h2 style="color: #1a1a2e; margin-bottom: 8px;">Password Reset</h2>
            <p style="color: #444; line-height: 1.6;">
                Hi {user_name},
            </p>
            <p style="color: #444; line-height: 1.6;">
                We received a request to reset your password. Use the code below to proceed:
            </p>
            <div style="text-align: center; margin: 28px 0;">
                <span style="display: inline-block; font-size: 32px; font-weight: 700; letter-spacing: 8px;
                             background: #f1f5f9; padding: 16px 32px; border-radius: 8px; color: #1a1a2e;">
                    {reset_code}
                </span>
            </div>
            <p style="color: #444; line-height: 1.6;">
                This code expires in <strong>15 minutes</strong>.
            </p>
            <p style="color: #888; font-size: 13px; line-height: 1.5;">
                Request from IP: {ip_address}<br/>
                If you did not request this, please ignore this email — your password will remain unchanged.
            </p>
        </div>
        """

        text_body = (
            f"Hi {user_name},\n\n"
            f"Your password reset code is: {reset_code}\n\n"
            f"This code expires in 15 minutes.\n\n"
            f"Request from IP: {ip_address}\n"
            f"If you did not request this, please ignore this email."
        )

        return await self._send(to_email, user_name, subject, html_body, text_body)

    # ------------------------------------------------------------------
    # Password changed notification
    # ------------------------------------------------------------------

    async def send_password_changed_notification_email(
        self,
        to_email: str,
        user_name: str,
        ip_address: str,
        user_agent: str,
        change_type: str,
    ) -> bool:
        action = "reset" if change_type == "reset" else "changed"
        subject = f"Your password was {action} — {self._sender_name}"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 0;">
            <h2 style="color: #1a1a2e; margin-bottom: 8px;">Password {action.title()}</h2>
            <p style="color: #444; line-height: 1.6;">
                Hi {user_name},
            </p>
            <p style="color: #444; line-height: 1.6;">
                Your password was successfully {action}. If you did not make this change,
                please contact support immediately.
            </p>
            <p style="color: #888; font-size: 13px; line-height: 1.5;">
                IP address: {ip_address}<br/>
                Device: {user_agent}
            </p>
        </div>
        """

        text_body = (
            f"Hi {user_name},\n\n"
            f"Your password was successfully {action}.\n\n"
            f"IP: {ip_address}\nDevice: {user_agent}\n\n"
            f"If you did not make this change, please contact support immediately."
        )

        return await self._send(to_email, user_name, subject, html_body, text_body)
