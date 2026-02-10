"""Email channel adapter (simulated)."""

from __future__ import annotations

from coordination_intelligence.channels.adapters.base import ChannelAdapter, DeliveryResult


class EmailAdapter(ChannelAdapter):
    """Simulated Email adapter.

    In production, this would integrate with SMTP or an email API
    (SendGrid, SES, etc.).
    """

    def __init__(self) -> None:
        self._sent: list[DeliveryResult] = []

    def send(self, recipient: str, message: str, **kwargs: object) -> DeliveryResult:
        """Simulate sending an email."""
        subject = kwargs.get("subject", "Blocker Resolution")
        result = DeliveryResult(
            success=True,
            channel="email",
            recipient=recipient,
            message_preview=f"Subject: {subject} | {message[:80]}",
        )
        self._sent.append(result)
        return result

    def channel_name(self) -> str:
        return "Email"

    @property
    def sent_messages(self) -> list[DeliveryResult]:
        """Return all simulated sent messages."""
        return list(self._sent)
