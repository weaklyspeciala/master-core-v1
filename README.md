# MASTER AI WORKSTATION - MASTER_CORE_V1

This is a new, isolated safety foundation. Existing projects and legacy agent files
were not changed by the bootstrap installer.

## Folders
- safety: safety policy and safe file-operation module
- approvals: reserved for approval-ticket records
- backups: reserved for timestamped backups
- logs: append-only JSONL audit log
- staging: reserved for proposed changes

## First-phase limitations
- No existing project code is imported or executed.
- No dashboard or background worker is started.
- No file deletion or bulk editing is implemented.
- The safe-write module is a building block; it is not yet connected to the
  legacy workstation or autonomous agent.
- Review and test the module before integrating it into any production workflow.

## Next step
Run the read-only verification script supplied separately, then review the
generated report before any integration work.