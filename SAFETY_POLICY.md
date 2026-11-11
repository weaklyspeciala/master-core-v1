# Master Core V1 - Safety Policy

## Operating principles
1. This core is isolated from legacy projects.
2. Never delete or bulk-modify project files automatically.
3. Never overwrite an existing file without an explicit approval ticket.
4. Before an approved edit, create a timestamped backup and verify its SHA256.
5. An approval ticket expires after 10 minutes and is bound to the target path,
   proposed content hash, and current file hash.
6. Re-check all hashes immediately before applying an approved change.
7. Write to a temporary file in the same directory, then atomically replace.
8. Keep an audit record for ticket creation, approval, rejection, backup, and edit.
9. Do not run Python, PowerShell, Node, installers, or render jobs in this phase.
10. If validation or backup fails, stop. Do not continue with the write.

## Human approval
This phase only provides the approval-ticket and safe-write building blocks.
It does not create a dashboard, start a background agent, or execute tools.
A later phase must add authenticated local UI/API handling and explicit user approval.