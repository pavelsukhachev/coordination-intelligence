"""Communication channel adapters.

Each adapter implements the ChannelAdapter interface for a specific
communication platform. In this reference implementation, all adapters
are stubs that simulate message delivery.
"""

from coordination_intelligence.channels.adapters.base import ChannelAdapter
from coordination_intelligence.channels.adapters.email_adapter import EmailAdapter
from coordination_intelligence.channels.adapters.slack_adapter import SlackAdapter
from coordination_intelligence.channels.adapters.sms_adapter import SMSAdapter

__all__ = ["ChannelAdapter", "SlackAdapter", "EmailAdapter", "SMSAdapter"]
