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
    ) -> bool:
        accept_url = f"{self._frontend_url}/accept-invitation?token={invitation_token}"

        role_label = {
            "department": "Department Administrator",
            "lecturer": "Faculty Member",
            "super": "Super Administrator",
        }.get(role, role.title())

        dept_line = f" for <strong>{department_name}</strong>" if department_name else ""

        subject = f"You've been invited to {self._sender_name}"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 0;">
            <h2 style="color: #1a1a2e; margin-bottom: 8px;">Welcome to {self._sender_name}</h2>
            <p style="color: #444; line-height: 1.6;">
                Hi {user_name},
            </p>
            <p style="color: #444; line-height: 1.6;">
                You've been invited to join as a <strong>{role_label}</strong>{dept_line}.
                Click the button below to set your password and activate your account.
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{accept_url}"
                   style="display: inline-block; background: #2563eb; color: #fff; padding: 12px 32px;
                          border-radius: 6px; text-decoration: none; font-weight: 600;">
                    Accept Invitation
                </a>
            </div>
            <p style="color: #888; font-size: 13px; line-height: 1.5;">
                If the button doesn't work, copy and paste this link into your browser:<br/>
                <a href="{accept_url}" style="color: #2563eb; word-break: break-all;">{accept_url}</a>
            </p>
            <p style="color: #888; font-size: 13px;">
                This invitation expires in 7 days. If you did not expect this email, you can safely ignore it.
            </p>
        </div>
        """

        text_body = (
            f"Hi {user_name},\n\n"
            f"You've been invited to join {self._sender_name} as a {role_label}{dept_line.replace('<strong>', '').replace('</strong>', '')}.\n\n"
            f"Accept your invitation: {accept_url}\n\n"
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
