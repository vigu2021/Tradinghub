export const ACCOUNT_TYPES = ["cash", "crypto", "stock"] as const;
export type AccountType = (typeof ACCOUNT_TYPES)[number];

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  cash: "Cash",
  crypto: "Crypto",
  stock: "Stocks",
};

/** Units offered alongside the user's own, so a first account has something to pick. */
export const COMMON_UNITS = ["GBP", "USD", "EUR", "BTC", "ETH", "USDT"];

/** Mirrors ledger/schemas/accounts.py: AccountResponse. Nothing enforces the match. */
export type Account = {
  id: number;
  name: string;
  unit: string;
  type: AccountType;
  group_name: string;
  balance: string;
  archived_at: string | null;
};

/** Mirrors ledger/schemas/accounts.py: AccountCreate. */
export type AccountCreate = {
  name: string;
  unit: string;
  type: AccountType;
  group_name: string;
};

/** Mirrors ledger/schemas/accounts.py: AccountUpdate. An omitted field is left alone. */
export type AccountUpdate = {
  name?: string;
  unit?: string;
  type?: AccountType;
  group_name?: string;
  archived?: boolean;
};
