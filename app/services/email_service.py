from loguru import logger


class EmailService:
    """Minimal email service placeholder for template bootstrap."""

    def send_password_reset_code_email(
        self, to_email: str, user_name: str, reset_code: str, ip_address: str, user_agent: str
    ) -> None:
        logger.info(
            "Password reset code email placeholder | to={} user={} code={}",
            to_email,
            user_name,
            reset_code,
        )

    def send_password_changed_notification_email(
        self, to_email: str, user_name: str, ip_address: str, user_agent: str, change_type: str
    ) -> None:
        logger.info(
            "Password changed email placeholder | to={} user={} type={}",
            to_email,
            user_name,
            change_type,
        )
