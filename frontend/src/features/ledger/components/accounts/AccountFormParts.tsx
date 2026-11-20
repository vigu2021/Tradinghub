"use client";

import { useQuery } from "@tanstack/react-query";
import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";
import {
  Controller,
  type Control,
  type FieldErrors,
  type UseFormSetFocus,
} from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ComboField } from "@/components/ui/ComboField";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { SelectField } from "@/components/ui/Field";
import { messageFor } from "@/lib/api/errors";

import { accountQueries } from "../../api/accounts";
import {
  ACCOUNT_TYPE_LABELS,
  ACCOUNT_TYPES,
  COMMON_UNITS,
  type Account,
} from "../../types/accounts";

/** The rules of ledger/schemas/accounts.py: AccountCreate, checked before anything is sent. */
export const accountSchema = z.object({
  group_name: z
    .string()
    .trim()
    .min(1, "Give the account a group, like Savings.")
    .max(60, "Keep the group to 60 characters."),
  unit: z
    .string()
    .trim()
    .min(2, "A unit is at least 2 characters, like GBP.")
    .max(10, "Keep the unit to 10 characters.")
    .regex(/^[A-Za-z0-9]+$/, "Letters and digits only, like GBP or BTC."),
  // Blank until picked, so a new account's type is never assumed.
  type: z
    .enum([...ACCOUNT_TYPES, ""])
    .pipe(z.enum(ACCOUNT_TYPES, { error: "Say what it is." })),
  name: z
    .string()
    .trim()
    .min(1, "Give the account a name.")
    .max(60, "Keep the name to 60 characters."),
});

export type AccountInput = z.input<typeof accountSchema>;
export type AccountValues = z.output<typeof accountSchema>;
type AccountControl = Control<AccountInput, unknown, AccountValues>;

const FIELD_ORDER = ["group_name", "unit", "type", "name"] as const;

/**
 * Moves focus to the first invalid field from the top. react-hook-form's own focusing follows the
 * order fields registered, which puts plain inputs ahead of the combo boxes above them.
 */
export function focusFirstError(
  errors: FieldErrors<AccountInput>,
  setFocus: UseFormSetFocus<AccountInput>,
) {
  const first = FIELD_ORDER.find((name) => errors[name]);
  if (first) {
    setFocus(first);
  }
}

/** Unit holds codes like GBP and BTC, so phones should not capitalise words or autocorrect them. */
export const UNIT_INPUT = {
  autoCapitalize: "characters",
  autoCorrect: "off",
  spellCheck: false,
} as const;

/**
 * The groups and units the user can pick from, out of the cached account list. While that list is
 * loading or has failed there is nothing honest to offer, so the forms wait or show the error.
 */
export function useAccountChoices() {
  const {
    data: accounts = [],
    isPending,
    error,
  } = useQuery(accountQueries.list());
  return {
    groups: groupChoices(accounts),
    units: unitChoices(accounts),
    isPending,
    error,
  };
}

type ChoicesStatusProps = {
  isPending: boolean;
  error: Error | null;
};

/** What a form shows instead of its fields while the choices are not ready. */
export function ChoicesStatus({ isPending, error }: ChoicesStatusProps) {
  if (error) {
    return <ErrorBanner>{messageFor(error)}</ErrorBanner>;
  }
  return isPending ? (
    <p className="text-sm text-ink-faint">Loading...</p>
  ) : null;
}

type ChoiceFieldProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "className" | "value" | "onChange" | "onBlur" | "defaultValue"
> & {
  control: AccountControl;
  name: "group_name" | "unit";
  label: string;
  hint: string;
  error?: string;
  options: string[];
  /** Runs after each change, for a form that fills other fields from this one. */
  onChoose?: (value: string) => void;
};

/** Group or Unit: a combo box wired to the form. */
export function ChoiceField({
  control,
  name,
  onChoose,
  ...combo
}: ChoiceFieldProps) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <ComboField
          {...combo}
          ref={field.ref}
          value={field.value}
          onBlur={field.onBlur}
          onChange={(value) => {
            field.onChange(value);
            onChoose?.(value);
          }}
        />
      )}
    />
  );
}

type TypeFieldProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "className"
> & {
  label: string;
  error?: string;
};

/** Starts on "Choose one" when blank, so a new account's type is picked rather than defaulted. */
export function TypeField(select: TypeFieldProps) {
  return (
    <SelectField id="account-type" {...select}>
      <option value="" disabled className="bg-surface">
        Choose one
      </option>
      {ACCOUNT_TYPES.map((type) => (
        <option key={type} value={type} className="bg-surface">
          {ACCOUNT_TYPE_LABELS[type]}
        </option>
      ))}
    </SelectField>
  );
}

type FormFooterProps = {
  error: Error | null;
  pending: boolean;
  label: { idle: string; busy: string };
  onCancel: () => void;
};

/** The request error, if any, then submit and Cancel. */
export function FormFooter({
  error,
  pending,
  label,
  onCancel,
}: FormFooterProps) {
  return (
    <>
      {error && <ErrorBanner>{messageFor(error)}</ErrorBanner>}
      <div className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? label.busy : label.idle}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </>
  );
}

/** The user's groups, each once regardless of case (the last spelling wins), in alphabetical order. */
function groupChoices(accounts: Account[]): string[] {
  const byKey = new Map(
    accounts.map(({ group_name }) => [group_name.toLowerCase(), group_name]),
  );
  return [...byKey.values()].sort((a, b) => a.localeCompare(b));
}

/** The user's own units in alphabetical order, then the common ones they have not used yet. */
function unitChoices(accounts: Account[]): string[] {
  const own = [...new Set(accounts.map((account) => account.unit))].sort();
  return [...own, ...COMMON_UNITS.filter((unit) => !own.includes(unit))];
}
