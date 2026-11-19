"use client";

import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { messageFor } from "@/lib/api/errors";

import { accountMutations } from "../api/accounts";
import type { Account } from "../types/accounts";

type ArchiveAccountProps = {
  account: Account;
};

const COPY = {
  archive: {
    title: "Archive",
    detail: "Hide it from your list and keep its history.",
    idle: "Archive",
    busy: "Archiving",
  },
  restore: {
    title: "Archived",
    detail: "Hidden from your list. Its history is kept.",
    idle: "Restore",
    busy: "Restoring",
  },
} as const;

/**
 * The settings row that archives an active account or restores an archived one. Each undoes the
 * other, so neither asks for confirmation.
 */
export function ArchiveAccount({ account }: ArchiveAccountProps) {
  const toggleArchive = useMutation(accountMutations.update());
  const active = account.archived_at === null;
  const copy = active ? COPY.archive : COPY.restore;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1 text-sm">
          <p className="font-semibold">{copy.title}</p>
          <p className="mt-0.5 text-ink-dim">{copy.detail}</p>
        </div>
        <Button
          variant="ghost"
          className="min-w-24 shrink-0"
          disabled={toggleArchive.isPending}
          onClick={() =>
            toggleArchive.mutate({
              id: account.id,
              changes: { archived: active },
            })
          }
        >
          {toggleArchive.isPending ? copy.busy : copy.idle}
        </Button>
      </div>
      {toggleArchive.error && (
        <ErrorBanner>{messageFor(toggleArchive.error)}</ErrorBanner>
      )}
    </div>
  );
}
