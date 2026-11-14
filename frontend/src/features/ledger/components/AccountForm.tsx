"use client";

import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Field, SelectField } from "@/components/ui/Field";
import { messageFor } from "@/lib/api/errors";

import { ACCOUNT_TYPES } from "../types/accounts";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { accountMutations } from "../api/accounts";

/** The rules of ledger/schemas/accounts.py: AccountCreate, checked before anything is sent. */
const createAccountSchema = z.object({
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

type CreateAccount = z.infer<typeof createAccountSchema>;

export function CreateAccountForm() {
  const createAccount = useMutation(accountMutations.create());
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateAccount>({
    resolver: zodResolver(createAccountSchema),
    mode: "onTouched",
  });

  const submit = handleSubmit((values) => {
    createAccount.mutate(values, {
      onSuccess: () => console.log("Created account"),
    });
  });

  return (
    <form onSubmit={submit} noValidate className="space-y-7">
      <Field
        id="account-name"
        label="Name"
        error={errors.name?.message}
        {...field("name")}
      />
      <Field
        id="account-unit"
        label="Unit"
        hint="A currency or ticker, like GBP or BTC"
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
          <option key={type} value={type} className="bg-ground">
            {type}
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
