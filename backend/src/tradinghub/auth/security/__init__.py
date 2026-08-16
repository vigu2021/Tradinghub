"""Cryptographic primitives for authentication: pure functions, no database, no request context.

Anything that reads or writes a row belongs in services/ instead, even when it is security-shaped.
Import from the module that defines a function, not from here.
"""
