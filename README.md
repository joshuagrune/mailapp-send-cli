# mailapp-send-cli

Small macOS helper to send email through **Mail.app** via AppleScript.

Goals:

- Pick the **correct Mail account** (not the system default)
- Disable Mail's default **signature** (`message signature = missing value`)
- Avoid empty **compose windows** (no sender probe drafts; `visible:false`)
- **Dry-run by default** — require `--execute` for real sends

## Requirements

- macOS with Mail.app configured
- Automation permission for the calling app/terminal
- Python 3.10+

## Usage

List configured Mail accounts:

```bash
python3 send_mail_via_mailapp.py --list-accounts
```

Preview a send (no mail leaves the machine):

```bash
python3 send_mail_via_mailapp.py \
  --account "Work" \
  --to recipient@example.com \
  --subject "Hello" \
  --body "Plain text body"
```

Send after explicit confirmation:

```bash
python3 send_mail_via_mailapp.py \
  --account "Work" \
  --to recipient@example.com \
  --subject "Invoice 123" \
  --body-file message.txt \
  --attachment invoice.pdf \
  --execute
```

## Agent safety rule

If you use this from an AI agent, pair it with a rule that **always confirms before external sends**. See `examples/external-send-confirmation.mdc`.

## Limitations

- AppleScript + Mail.app only (no SMTP/Gmail API)
- Sender display name comes from the Mail account's configured full name
- Aliases must be configured inside Mail.app / Gmail "Send mail as"

## License

MIT
