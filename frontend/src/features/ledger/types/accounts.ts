export const ACCOUNT_TYPES = ["cash", "crypto", "stock"] as const;
export type AccountType = (typeof ACCOUNT_TYPES)[number];

/** Mirrors ledger/schemas/accounts.py: AccountResponse. Nothing enforces the match. */
export type Account = {
  id: number;
  name: string;
  unit: string;
  type: AccountType;
  balance: string;
  archived_at: string | null;
};

/** Mirrors ledger/schemas/accounts.py: AccountCreate. */
export type AccountCreate = {
  name: string;
  unit: string;
  type: AccountType;
};

/** Mirrors ledger/schemas/accounts.py: AccountUpdate. An omitted field is left alone. */
export type AccountUpdate = {
  name?: string;
  unit?: string;
  type?: AccountType;
  archived?: boolean;
};
