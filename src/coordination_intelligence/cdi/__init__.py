"""Coordination Debt Index (CDI) proxy calculator.

The CDI quantifies organizational coordination overhead on a 0-100
scale. Lower is better. It uses six observable metrics as proxies
for coordination health.
"""

from coordination_intelligence.cdi.proxy import CDIProxy

__all__ = ["CDIProxy"]
