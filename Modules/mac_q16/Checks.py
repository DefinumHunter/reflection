"""Compare all known outputs every clock, including busy and sidebands.

The golden's None means an uninitialized (X) value. Reflection's exact
comparison skips only those values; it does not mask data on valid=0.
"""
from Engine.Checks import exact as compare
