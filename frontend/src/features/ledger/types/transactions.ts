export const TRANSACTION_KINDS = ["income", "expense", "transfer"] as const;
export type TransactionKind = (typeof TRANSACTION_KINDS)[number];
export type IncomeOrExpense = Exclude<TransactionKind, "transfer">;

/** Mirrors ledger/schemas/transactions.py: TransactionResponse. The amount is signed: out is negative. */
export type Transaction = {
  id: number;
  account_id: number;
  amount: string;
  kind: TransactionKind;
  category: string | null;
  occurred_at: string;
  note: string | null;
  transfer_group_id: string | null;
};

/** Mirrors ledger/schemas/transactions.py: TransactionCreate. */
export type TransactionCreate = {
  account_id: number;
  amount: string;
  kind: IncomeOrExpense;
  category?: string;
  occurred_at: string;
  note?: string;
};

/** Mirrors ledger/schemas/transactions.py: TransactionPage. total counts every match, not just this page. */
export type TransactionPage = {
  items: Transaction[];
  total: number;
};

/** Mirrors ledger/schemas/transactions.py: TransactionUpdate. An omitted field is left alone; null clears category or note. */
export type TransactionUpdate = {
  amount?: string;
  kind?: IncomeOrExpense;
  category?: string | null;
  occurred_at?: string;
  note?: string | null;
};

/** Mirrors ledger/schemas/transactions.py: TransactionFilters. Every filter is optional and they combine. */
export type TransactionFilters = {
  account_id?: number;
  kind?: TransactionKind;
  category?: string;
  occurred_from?: string;
  occurred_to?: string;
  limit?: number;
  offset?: number;
};
