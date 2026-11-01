"""Queries against the ledger tables. These never commit; the caller owns the transaction.

Every read and delete takes user_id, and every insert writes rows that carry it, so a caller cannot
reach another user's rows by forgetting to filter.
"""
