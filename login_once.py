#!/usr/bin/env -S uv run --project instagram_dm_mcp python
"""One-time (or when-expired) Instagram login for the morning reel digest.

Run this yourself in a terminal; it needs a sessionid copied from your browser
(or, with --password, a 2FA/verification code), which the unattended morning job cannot provide.

    cd /path/to/reel-digest && ./login_once.py              # reuse a browser session (works today)
    cd /path/to/reel-digest && ./login_once.py --password   # password login (currently rejected by Instagram)

It saves a session file the MCP server reuses, then asks which DM group to watch
and writes the choice to config.json.
"""

import getpass
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, unquote

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, TwoFactorRequired

ROOT = Path(__file__).resolve().parent
SERVER_DIR = ROOT / "instagram_dm_mcp"
ENV_FILE = SERVER_DIR / ".env"
CONFIG_FILE = ROOT / "config.json"


def credentials() -> tuple[str, str]:
    load_dotenv(ENV_FILE)
    username, password = os.getenv("INSTAGRAM_USERNAME"), os.getenv("INSTAGRAM_PASSWORD")
    if username and password:
        return username, password
    username = input("Instagram username: ").strip()
    password = getpass.getpass("Instagram password: ").strip()
    ENV_FILE.write_text(f"INSTAGRAM_USERNAME={username}\nINSTAGRAM_PASSWORD={password}\n")
    ENV_FILE.chmod(0o600)
    print(f"Saved credentials to {ENV_FILE} (readable only by you)")
    return username, password


def password_login(client: Client, username: str, password: str) -> None:
    try:
        client.login(username, password)
    except TwoFactorRequired:
        code = input("2FA code from your authenticator app / SMS: ").strip()
        client.login(username, password, verification_code=code)


BROWSER_SESSION_STEPS = """
Instagram currently rejects password logins from scripts with a misleading "Your version of Instagram
is out of date" (instagrapi issues #2807 / #2881), so this reuses a browser login instead:

  1. In Chrome, open a NEW INCOGNITO window and log in at https://www.instagram.com
     (a separate session, so logging out in your normal browser won't break the digest)
  2. View > Developer > Developer Tools > Application tab > Cookies > https://www.instagram.com
  3. Click the "sessionid" row and copy its Value (starts with digits, about 70 characters)
  4. Close the Incognito window. Do NOT click "Log out" (that would end this session too)

Treat the sessionid like a password: it is stored only in the chmod-600 session file.
"""


def browser_session_login(client: Client) -> None:
    print(BROWSER_SESSION_STEPS)
    raw = getpass.getpass("Paste the sessionid value (input is hidden): ").strip().strip('"')
    # DevTools shows the cookie URL-encoded (digits%3A...); accept a decoded paste too
    client.login_by_sessionid(quote(unquote(raw), safe=""))


def login(username: str, password: str) -> Client:
    client = Client()
    client.delay_range = [1, 3]
    session_file = SERVER_DIR / f"{username}_session.json"

    valid = False
    if session_file.exists():
        client.load_settings(session_file, override_app_version=True)
        try:
            client.account_info()  # cheap call that fails if the session is dead
            valid = True
            print("Existing session is still valid.")
        except LoginRequired:
            print("Saved session has expired.")
            uuids = client.get_settings()["uuids"]  # keep the same device id
            client.set_settings({})
            client.set_uuids(uuids)

    if not valid:
        if "--password" in sys.argv:
            password_login(client, username, password)
        else:
            browser_session_login(client)

    client.dump_settings(session_file)
    session_file.chmod(0o600)
    print(f"Logged in as {client.username}; session saved to {session_file}")
    return client


def pick_thread(client: Client) -> None:
    current = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
    if current.get("thread_id"):
        print(f"\nCurrently watching: {current.get('thread_title')!r}")
        if input("Change it? [y/N] ").strip().lower() != "y":
            return

    threads = client.direct_threads(amount=40)
    # Groups first, since that's what the digest is meant to watch
    threads.sort(key=lambda t: not t.is_group)
    print("\nYour recent DM threads:")
    for i, t in enumerate(threads, 1):
        name = t.thread_title or ", ".join(u.username for u in t.users)
        print(f"  {i:2}. {'[group] ' if t.is_group else ''}{name}")
    choice = int(input("\nNumber of the group you send workflow reels to: "))
    thread = threads[choice - 1]
    current.update(
        thread_id=str(thread.id),
        thread_title=thread.thread_title or ", ".join(u.username for u in thread.users),
    )
    CONFIG_FILE.write_text(json.dumps(current, indent=2) + "\n")
    print(f"Saved to {CONFIG_FILE}: watching {current['thread_title']!r}")


if __name__ == "__main__":
    pick_thread(login(*credentials()))
