/** Mirrors ledger/schemas/summary.py: SummaryPeriod. Includes its start, excludes its end. */
export type SummaryPeriod = {
  occurred_from: string;
  occurred_to: string;
};

/** Mirrors ledger/schemas/summary.py: UnitTotal. */
export type UnitTotal = {
  unit: string;
  amount: string;
};

/** Mirrors ledger/schemas/summary.py: CategoryTotal. A null category is uncategorised. */
export type CategoryTotal = {
  category: string | null;
  unit: string;
  amount: string;
};

/**
 * Mirrors ledger/schemas/summary.py: SummaryResponse. Every total is per unit, and expenses are
 * positive: what was spent.
 */
export type Summary = {
  totals: UnitTotal[];
  income: UnitTotal[];
  expenses: UnitTotal[];
  by_category: CategoryTotal[];
};
