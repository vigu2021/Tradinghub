/** Mirrors ledger/schemas/transfers.py: TransferCreate. Both amounts are positive; they differ when the units do. fee and fee_account_id come together. */
export type TransferCreate = {
  from_account_id: number;
  to_account_id: number;
  amount_sent: string;
  amount_received: string;
  fee?: string;
  fee_account_id?: number;
  fee_category?: string;
  occurred_at: string;
  note?: string;
};
