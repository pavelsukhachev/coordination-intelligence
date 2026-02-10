"""Communication channel selection and adapter layer.

The channel selector uses an ML-inspired scoring algorithm to pick
the best communication channel for each resolution action. Adapters
provide a common interface for Slack, Email, and SMS.
"""

from coordination_intelligence.channels.selector import ChannelSelector

__all__ = ["ChannelSelector"]
