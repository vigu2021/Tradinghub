"use client";

import { useState, type InputHTMLAttributes, type Ref } from "react";
import {
  Button,
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
  /** Lets a form move focus here, as react-hook-form does to the first invalid field. */
  ref?: Ref<HTMLInputElement>;
};

type Option = { id: string; label: string };

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
  ref,
  ...input
}: ComboFieldProps) {
  // Opening the list on purpose (tapping in, or the button) shows everything; typing filters it.
  const [showingAll, setShowingAll] = useState(true);
  const typed = value.trim();
  const existing = options.find(
    (option) => option.toLowerCase() === typed.toLowerCase(),
  );
  const items: Option[] = options
    .filter(
      (option) =>
        showingAll || option.toLowerCase().includes(typed.toLowerCase()),
    )
    .map((option) => ({ id: option, label: option }));
  if (typed !== "" && existing === undefined) {
    items.push({ id: CREATE, label: `+ Create "${typed}"` });
  }

  return (
    <ComboBox
      allowsCustomValue
      menuTrigger="focus"
      items={items}
      inputValue={value}
      onInputChange={(next) => {
        setShowingAll(false);
        onChange(next);
      }}
      onOpenChange={(isOpen, trigger) => {
        if (isOpen && trigger !== "input") {
          setShowingAll(true);
        }
      }}
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
      <div className="relative">
        <Input
          ref={ref}
          className={`${CONTROL} pr-11 ${error ? "border-danger" : "border-control"}`}
          {...input}
        />
        <Button className="absolute top-2 right-0 bottom-0 flex w-11 items-center justify-center text-ink-faint outline-none hover:text-ink data-[focus-visible]:text-accent">
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.75}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </Button>
      </div>
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
              textValue={option.id === CREATE ? typed : option.id}
              className={`flex min-h-11 cursor-pointer items-center px-3 text-base outline-none data-[focused]:bg-surface ${
                option.id === CREATE ? "font-semibold text-accent" : "text-ink"
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
