"""Slack channel adapter (simulated)."""

from __future__ import annotations

from coordination_intelligence.channels.adapters.base import ChannelAdapter, DeliveryResult


class SlackAdapter(ChannelAdapter):
    """Simulated Slack adapter.

    In production, this would integrate with the Slack Web API.
    """

    def __init__(self) -> None:
        self._sent: list[DeliveryResult] = []

    def send(self, recipient: str, message: str, **kwargs: object) -> DeliveryResult:
        """Simulate sending a Slack message."""
        result = DeliveryResult(
            success=True,
            channel="slack",
            recipient=recipient,
            message_preview=message[:100],
        )
        self._sent.append(result)
        return result

    def channel_name(self) -> str:
        return "Slack"

    @property
    def sent_messages(self) -> list[DeliveryResult]:
        """Return all simulated sent messages."""
        return list(self._sent)
