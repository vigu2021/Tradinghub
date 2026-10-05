"""Queries against the ledger tables. These never commit; the caller owns the transaction.

Every function takes user_id, so a caller cannot read another user's rows by forgetting to filter.
"""
