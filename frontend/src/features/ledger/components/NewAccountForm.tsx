"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRef } from "react";
import { useForm } from "react-hook-form";

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

type NewAccountFormProps = {
  onCreated: (account: Account) => void;
  onCancel: () => void;
};

/** Group, Unit, Type, Name. Name fills itself from the group and unit until the user types their own. */
export function NewAccountForm({ onCreated, onCancel }: NewAccountFormProps) {
  const createAccount = useMutation(accountMutations.create());
  const { groups, units, ...choices } = useAccountChoices();
  const {
    register,
    handleSubmit,
    setFocus,
    control,
    setValue,
    getValues,
    formState: { errors, isSubmitted },
  } = useForm<AccountInput, unknown, AccountValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: { group_name: "", unit: "", type: "", name: "" },
    mode: "onSubmit",
    reValidateMode: "onChange",
    shouldFocusError: false,
  });

  // Set only by typing in Name, which a value filled in here never triggers.
  const nameIsTheirs = useRef(false);
  const fillName = () => {
    if (!nameIsTheirs.current) {
      setValue(
        "name",
        suggestedName(getValues("group_name"), getValues("unit")),
        { shouldValidate: isSubmitted },
      );
    }
  };
  const nameField = register("name");

  const submit = handleSubmit(
    (values) => createAccount.mutate(values, { onSuccess: onCreated }),
    (invalid) => focusFirstError(invalid, setFocus),
  );

  if (choices.isPending || choices.error) {
    return <ChoicesStatus {...choices} />;
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-7">
      <ChoiceField
        control={control}
        name="group_name"
        label="Group"
        hint="How you file it, like Binance, Savings or Home safe"
        placeholder="Pick one or type a new group"
        options={groups}
        error={errors.group_name?.message}
        onChoose={fillName}
      />
      <ChoiceField
        control={control}
        name="unit"
        label="Unit"
        hint="A currency or ticker, like GBP or BTC"
        options={units}
        placeholder="Pick one or type a new unit"
        error={errors.unit?.message}
        onChoose={fillName}
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
        hint="Fills itself from the group and unit until you type your own"
        autoComplete="off"
        error={errors.name?.message}
        {...nameField}
        onChange={(event) => {
          nameIsTheirs.current = event.target.value !== "";
          return nameField.onChange(event);
        }}
      />
      <FormFooter
        error={createAccount.error}
        pending={createAccount.isPending}
        label={{ idle: "Add account", busy: "Adding" }}
        onCancel={onCancel}
      />
    </form>
  );
}

/** "Binance BTC": the name a new account gets until the user types their own. */
function suggestedName(group: string, unit: string): string {
  return [group.trim(), unit.trim().toUpperCase()].filter(Boolean).join(" ");
}
