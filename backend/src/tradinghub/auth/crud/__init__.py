"""Queries against the authentication tables.

These functions never commit. The calling service owns the transaction, so several of them can
make up one atomic operation.
"""
