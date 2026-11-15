"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Field, SelectField } from "@/components/ui/Field";
import { messageFor } from "@/lib/api/errors";

import { accountMutations } from "../api/accounts";
import { Account, ACCOUNT_TYPE_LABELS, ACCOUNT_TYPES } from "../types/accounts";

/** The rules of ledger/schemas/accounts.py: AccountCreate, checked before anything is sent. */
const accountSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Give the account a name.")
    .max(60, "Keep the name to 60 characters."),
  unit: z
    .string()
    .trim()
    .min(2, "A unit is at least 2 characters, like GBP.")
    .max(10, "Keep the unit to 10 characters.")
    .regex(/^[A-Za-z0-9]+$/, "Letters and digits only, like GBP or BTC."),
  type: z.enum(ACCOUNT_TYPES),
});

type AccountValues = z.infer<typeof accountSchema>;

type AccountFormProps =
  | { mode: "creating" }
  | {
      mode: "editing";
      account: Account;
      onDone: () => void;
    };

export function AccountForm(props: AccountFormProps) {
  const createAccount = useMutation(accountMutations.create());
  const updateAccount = useMutation(accountMutations.update());

  const {
    register: field,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AccountValues>({
    resolver: zodResolver(accountSchema),
    mode: "onSubmit",
    reValidateMode: "onChange",
  });

  const submit = handleSubmit((values) => {
    if (props.mode === "creating") {
      createAccount.mutate(values, {
        onSuccess: () => reset(),
      });
    } else {
      updateAccount.mutate(
        { id: props.account.id, changes: values },
        {
          onSuccess: () => props.onDone(),
        },
      );
    }
  });

  return (
    <form onSubmit={submit} noValidate className="space-y-7">
      <Field
        id="account-name"
        label="Name"
        autoComplete="off"
        error={errors.name?.message}
        {...field("name")}
      />
      <Field
        id="account-unit"
        label="Unit"
        hint="A currency or ticker, like GBP or BTC"
        autoComplete="off"
        autoCapitalize="characters"
        autoCorrect="off"
        spellCheck={false}
        error={errors.unit?.message}
        {...field("unit")}
      />
      <SelectField
        id="account-type"
        label="Type"
        error={errors.type?.message}
        {...field("type")}
      >
        {ACCOUNT_TYPES.map((type) => (
          <option key={type} value={type} className="bg-surface">
            {ACCOUNT_TYPE_LABELS[type]}
          </option>
        ))}
      </SelectField>

      {createAccount.error && (
        <ErrorBanner>{messageFor(createAccount.error)}</ErrorBanner>
      )}

      <Button
        type="submit"
        className="w-full"
        disabled={createAccount.isPending}
      >
        {createAccount.isPending ? "Adding" : "Add account"}
      </Button>
    </form>
  );
}
