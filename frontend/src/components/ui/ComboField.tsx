"use client";

import type { InputHTMLAttributes } from "react";
import {
  ComboBox,
  FieldError,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Text,
} from "react-aria-components";

import { CONTROL } from "./Field";

type ComboFieldProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "className" | "value" | "onChange" | "onBlur" | "defaultValue"
> & {
  label: string;
  hint?: string;
  error?: string;
  /** The values already in use, offered as the user types. */
  options: string[];
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
};

type Option = { id: string; label: string; text: string; creates: boolean };

const CREATE = "\u0000create";

/**
 * Type to filter `options`, pick one, or keep a new value through "+ Create …". Reports one string,
 * so a form validates it like a text field. A value matching an option apart from case becomes that
 * option, so "binance" files under "Binance" rather than splitting it. Extra props go to the input.
 */
export function ComboField({
  label,
  hint,
  error,
  options,
  value,
  onChange,
  onBlur,
  ...input
}: ComboFieldProps) {
  const typed = value.trim();
  const existing = matchIgnoringCase(options, typed);
  const items = optionsFor(options, typed, existing);

  return (
    <ComboBox
      allowsCustomValue
      menuTrigger="focus"
      items={items}
      defaultFilter={() => true}
      inputValue={value}
      onInputChange={onChange}
      onSelectionChange={(key) => {
        if (key !== null) {
          onChange(key === CREATE ? typed : String(key));
        }
      }}
      onBlur={() => {
        if (existing !== undefined && existing !== value) {
          onChange(existing);
        }
        onBlur?.();
      }}
      isInvalid={Boolean(error)}
      className="group"
    >
      <Label
        className={`block text-[0.8125rem] font-medium transition-colors ${
          error ? "text-danger" : "text-ink-dim group-focus-within:text-ink"
        }`}
      >
        {label}
      </Label>
      <Input
        className={`${CONTROL} ${error ? "border-danger" : "border-control"}`}
        {...input}
      />
      {hint && !error && (
        <Text slot="description" className="mt-2 block text-xs text-ink-faint">
          {hint}
        </Text>
      )}
      <FieldError className="mt-2 block text-xs text-danger">
        {error}
      </FieldError>
      <Popover
        offset={0}
        className="w-(--trigger-width) border border-t-0 border-rule-strong bg-ground shadow-[0_10px_24px_rgba(0,0,0,0.08)]"
      >
        <ListBox<Option> className="max-h-60 overflow-auto py-1 outline-none">
          {(option) => (
            <ListBoxItem
              id={option.id}
              textValue={option.text}
              className={`flex min-h-11 cursor-pointer items-center px-3 text-base outline-none data-[focused]:bg-surface ${
                option.creates ? "font-semibold text-accent" : "text-ink"
              }`}
            >
              {option.label}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </ComboBox>
  );
}

function matchIgnoringCase(
  options: string[],
  typed: string,
): string | undefined {
  const wanted = typed.toLowerCase();
  return options.find((option) => option.toLowerCase() === wanted);
}

/** The options containing what is typed, then "+ Create …" when the typed value is new. */
function optionsFor(
  options: string[],
  typed: string,
  existing: string | undefined,
): Option[] {
  const wanted = typed.toLowerCase();
  const matches: Option[] = options
    .filter((option) => option.toLowerCase().includes(wanted))
    .map((option) => ({
      id: option,
      label: option,
      text: option,
      creates: false,
    }));
  if (typed === "" || existing !== undefined) {
    return matches;
  }
  return [
    ...matches,
    { id: CREATE, label: `+ Create "${typed}"`, text: typed, creates: true },
  ];
}
