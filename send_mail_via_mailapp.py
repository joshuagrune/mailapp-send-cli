#!/usr/bin/env python3
"""Send email via macOS Mail.app from a named account, with signature disabled.

Dry-run by default. Pass --execute only after explicit user confirmation.
Requires Mail.app configured locally and Automation permission for the caller.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def resolve_mail_account(account_name: str) -> dict[str, str]:
    acct = _applescript_string(account_name)
    script = f"""
tell application "Mail"
    set targetAcct to missing value
    repeat with acct in accounts
        if name of acct is {acct} then
            set targetAcct to acct
            exit repeat
        end if
    end repeat
    if targetAcct is missing value then error "Mail account not found"
    set acctName to name of targetAcct
    set acctFullName to full name of targetAcct
    set acctEmails to email addresses of targetAcct
    set acctEmail to item 1 of acctEmails
    return acctName & tab & acctFullName & tab & acctEmail
end tell
"""
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    name, full_name, email = result.stdout.strip().split("\t", 2)
    return {"name": name, "full_name": full_name, "email": email}


def list_mail_accounts() -> list[dict[str, str]]:
    script = """
tell application "Mail"
    set output to ""
    repeat with acct in accounts
        set acctName to name of acct
        set acctFullName to full name of acct
        set acctEmails to email addresses of acct
        set acctEmail to item 1 of acctEmails
        set output to output & acctName & tab & acctFullName & tab & acctEmail & linefeed
    end repeat
    return output
end tell
"""
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    accounts: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, full_name, email = line.split("\t", 2)
        accounts.append({"name": name, "full_name": full_name, "email": email})
    return accounts


def resolve_sender_string(account_name: str) -> tuple[str, str]:
    account = resolve_mail_account(account_name)
    sender = f"{account['full_name']} <{account['email']}>"
    note = f"using Mail account {account['name']} ({account['email']})"
    return sender, note


def build_applescript(
    *,
    to_address: str,
    subject: str,
    body: str,
    sender: str,
    attachment: Path | None,
) -> str:
    attachment_block = ""
    attachment_setup = ""
    if attachment is not None:
        attachment_setup = f"set attachmentPath to POSIX file {_applescript_string(str(attachment))}\n"
        attachment_block = (
            "        make new attachment with properties {file name:attachmentPath} "
            "at after the last paragraph\n"
        )

    return f"""
{attachment_setup}set toAddress to {_applescript_string(to_address)}
set msgSubject to {_applescript_string(subject)}
set msgBody to {_applescript_string(body)}
set msgSender to {_applescript_string(sender)}

tell application "Mail"
    try
        delete (every outgoing message whose subject is "probe")
    end try

    set newMessage to make new outgoing message with properties {{subject:msgSubject, content:msgBody & return & return, sender:msgSender, visible:false}}
    tell newMessage
        set visible to false
        set message signature to missing value
        make new to recipient at end of to recipients with properties {{address:toAddress}}
{attachment_block}        set visible to false
    end tell
    send newMessage
end tell

return "sent"
"""


def send_mail(
    *,
    to_address: str,
    subject: str,
    body: str,
    sender: str,
    attachment: Path | None = None,
    execute: bool = False,
) -> None:
    print("Mail Send Preview")
    print(f"  to: {to_address}")
    print(f"  from: {sender}")
    print(f"  subject: {subject}")
    print("  signature: disabled (message signature = missing value)")
    print("  compose window: suppressed (visible:false)")
    if attachment:
        print(f"  attachment: {attachment.name}")

    if not execute:
        print("\nDry run only. Pass --execute after explicit user confirmation.")
        return

    script = build_applescript(
        to_address=to_address,
        subject=subject,
        body=body,
        sender=sender,
        attachment=attachment,
    )
    result = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
    print(result.stdout.strip() or "sent")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-accounts", action="store_true", help="List Mail.app account names")
    parser.add_argument("--account", help="Mail.app account name (required unless --list-accounts)")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", default="", help="Email subject")
    parser.add_argument("--body", default="", help="Plain-text email body")
    parser.add_argument("--body-file", type=Path, help="Read body from a file")
    parser.add_argument("--attachment", type=Path, help="Optional file attachment")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually send. Without this flag, only prints the preview.",
    )
    args = parser.parse_args()

    if args.list_accounts:
        for account in list_mail_accounts():
            print(
                f"{account['name']}\t{account['full_name']}\t<{account['email']}>"
            )
        return 0

    if not args.account or not args.to:
        parser.error("--account and --to are required unless --list-accounts is used")

    body = args.body
    if args.body_file:
        body = args.body_file.read_text(encoding="utf-8")

    sender, sender_note = resolve_sender_string(args.account)
    print(f"Sender resolution: {sender_note}")

    if args.attachment and not args.attachment.exists():
        raise RuntimeError(f"Attachment not found: {args.attachment}")

    send_mail(
        to_address=args.to,
        subject=args.subject,
        body=body,
        sender=sender,
        attachment=args.attachment,
        execute=args.execute,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
