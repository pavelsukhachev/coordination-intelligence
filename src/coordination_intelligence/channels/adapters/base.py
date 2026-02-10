"""Abstract base class for channel adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeliveryResult:
    """Result of a message delivery attempt."""

    success: bool
    channel: str
    recipient: str
    message_preview: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    error: str = ""


class ChannelAdapter(ABC):
    """Common interface for all communication channel adapters.

    Subclasses implement ``send()`` for their specific platform.
    In this reference implementation, all adapters simulate delivery.
    """

    @abstractmethod
    def send(self, recipient: str, message: str, **kwargs: object) -> DeliveryResult:
        """Send a message through this channel.

        Args:
            recipient: Target identifier (email, Slack user ID, phone).
            message: Message content.
            **kwargs: Channel-specific options.

        Returns:
            A DeliveryResult indicating success or failure.
        """
        ...

    @abstractmethod
    def channel_name(self) -> str:
        """Return the human-readable channel name."""
        ...
