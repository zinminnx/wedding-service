# EverVow v12.3 Local Print Agent

This folder runs on the Windows PC that is physically connected to the wedding printer.

## Security

- Each device gets a long random wedding-scoped token.
- EverVow stores only the SHA-256 hash of that token.
- A token can claim jobs only for its own wedding.
- Source downloads require the same device token and an active job assignment.
- Revoking or rotating a device token immediately blocks the old token.
- `agent.env` is ignored by Git and must never be committed.

## Setup

```powershell
cd local_print_agent
.\install_agent.ps1
```

In EverVow open **Printing > Local Print Agents**, create a device and copy the one-time token into `agent.env`.

List Windows printers:

```powershell
.\run_agent.ps1 --list-printers
```

Safe dry run (claims/downloads one job but does not send it to the printer):

```powershell
.\run_agent.ps1 --once --dry-run
```

Start continuous polling:

```powershell
.\run_agent.ps1
```

## Printing behavior

The agent uses Pillow + pywin32 and prints directly through the Windows printer device context; no browser print dialog is involved. Copies and Fit/Fill/Original are enforced by the agent. `paper_size` remains visible in the job and logs, but the actual tray/media must be configured in the Windows printer driver for this v12.3 agent. This avoids changing global printer defaults behind the operator's back.

Claimed jobs have a 5-minute lease. If an agent disappears before it starts printing, the job can be safely claimed again after the lease. Once a job enters **Printing**, EverVow never auto-requeues it, because automatic retry could produce duplicate physical prints.

## Optional: start automatically at Windows logon

After a successful dry run:

```powershell
.\install_startup_task.ps1
```

To remove it later:

```powershell
.\remove_startup_task.ps1
```

The task runs under the current Windows user so it uses that user's installed/default printers.
