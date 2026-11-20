"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";

import { Field } from "@/components/ui/Field";

import { accountMutations } from "../api/accounts";
import type { Account } from "../types/accounts";
import {
  accountSchema,
  ChoiceField,
  ChoicesStatus,
  focusFirstError,
  FormFooter,
  TypeField,
  UNIT_INPUT,
  useAccountChoices,
  type AccountInput,
  type AccountValues,
} from "./AccountFormParts";

type EditAccountFormProps = {
  account: Account;
  /** Called after a save, and on Cancel. */
  onClose: () => void;
};

/** An account's settings. Nothing fills itself here: an existing name is never rewritten. */
export function EditAccountForm({ account, onClose }: EditAccountFormProps) {
  const updateAccount = useMutation(accountMutations.update());
  const { groups, units, ...choices } = useAccountChoices();
  const {
    register,
    handleSubmit,
    setFocus,
    control,
    formState: { errors },
  } = useForm<AccountInput, unknown, AccountValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: {
      group_name: account.group_name,
      unit: account.unit,
      type: account.type,
      name: account.name,
    },
    mode: "onSubmit",
    reValidateMode: "onChange",
    shouldFocusError: false,
  });

  const unit = useWatch({ control, name: "unit" });

  const submit = handleSubmit(
    (values) =>
      updateAccount.mutate(
        { id: account.id, changes: values },
        { onSuccess: onClose },
      ),
    (invalid) => focusFirstError(invalid, setFocus),
  );

  if (choices.isPending || choices.error) {
    return <ChoicesStatus {...choices} />;
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-7">
      <div className="grid gap-5 sm:grid-cols-2">
        <ChoiceField
          control={control}
          name="group_name"
          label="Group"
          hint="How you file it, like Binance, Savings or Home safe"
          placeholder="Pick one or type a new group"
          options={groups}
          error={errors.group_name?.message}
        />
        <ChoiceField
          control={control}
          name="unit"
          label="Unit"
          hint={
            unitChangeWarning(account, unit) ??
            "A currency or ticker, like GBP or BTC"
          }
          options={units}
          placeholder="Pick one or type a new unit"
          error={errors.unit?.message}
          {...UNIT_INPUT}
        />
        <TypeField
          label="Type"
          error={errors.type?.message}
          {...register("type")}
        />
        <Field
          id="account-name"
          label="Name"
          hint="Which account it is, like Revolut GBP or Cash jar"
          autoComplete="off"
          error={errors.name?.message}
          {...register("name")}
        />
      </div>
      <FormFooter
        error={updateAccount.error}
        pending={updateAccount.isPending}
        label={{ idle: "Save", busy: "Saving" }}
        onCancel={onClose}
      />
    </form>
  );
}

/**
 * Changing a unit relabels the balance rather than converting it, so a non-zero balance says what
 * will happen to it. Returns nothing when there is no change to warn about.
 */
function unitChangeWarning(
  account: Account,
  typed: string,
): string | undefined {
  const unit = typed.trim().toUpperCase();
  if (unit === "" || unit === account.unit || Number(account.balance) === 0) {
    return undefined;
  }
  return `Nothing is converted: ${account.balance} ${account.unit} becomes ${account.balance} ${unit}.`;
}
