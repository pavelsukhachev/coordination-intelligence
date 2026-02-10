"""SMS channel adapter (simulated)."""

from __future__ import annotations

from coordination_intelligence.channels.adapters.base import ChannelAdapter, DeliveryResult


class SMSAdapter(ChannelAdapter):
    """Simulated SMS adapter.

    In production, this would integrate with Twilio or a similar
    SMS gateway.
    """

    def __init__(self) -> None:
        self._sent: list[DeliveryResult] = []

    def send(self, recipient: str, message: str, **kwargs: object) -> DeliveryResult:
        """Simulate sending an SMS.

        SMS messages are truncated to 160 characters.
        """
        truncated = message[:160]
        result = DeliveryResult(
            success=True,
            channel="sms",
            recipient=recipient,
            message_preview=truncated,
        )
        self._sent.append(result)
        return result

    def channel_name(self) -> str:
        return "SMS"

    @property
    def sent_messages(self) -> list[DeliveryResult]:
        """Return all simulated sent messages."""
        return list(self._sent)
