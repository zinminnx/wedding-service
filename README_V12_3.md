# EverAfter v12.3 - Local Print Agent

Prerequisite: v12.2 Printing System.

Adds the trusted Windows print-agent bridge between EverAfter's cloud/server queue and a physical printer.

## Server-side additions

- Wedding-scoped `PrintAgentDevice` registry.
- Long random device token; only SHA-256 hash is stored in the database.
- Token rotation/revocation.
- Agent heartbeat and last-seen/error visibility.
- Atomic oldest-first job claiming.
- Five-minute lease for **Claimed** jobs only.
- No automatic requeue after **Printing** starts, preventing accidental duplicate physical prints.
- Authenticated source download restricted to the assigned device and wedding.
- Agent state callbacks: Claimed -> Printing -> Printed / Failed.
- Existing manual queue controls remain intact.

## Windows agent

`local_print_agent/` contains a separate virtual environment setup and polling client using `requests`, Pillow and pywin32. It prints directly through the Windows printer device context; the browser print dialog is not used.

The queue's Fit / Fill / Original mode and copy count are enforced. The `paper_size` value is kept as job metadata in v12.3; actual tray/media selection remains under the Windows printer driver so the agent does not silently modify machine-wide printer defaults.

## Install the Django patch

Extract into the wedding-service project root, then:

```powershell
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
python manage.py runserver
```

Open `/dashboard/printing/` and create a **Local Print Agent** token.

## Install on the Windows print PC

```powershell
cd local_print_agent
.\install_agent.ps1
```

Put the one-time server URL/token into `agent.env`, then:

```powershell
.\run_agent.ps1 --list-printers
.\run_agent.ps1 --once --dry-run
.\run_agent.ps1
```

`agent.env` is git-ignored. Never commit the device token.
