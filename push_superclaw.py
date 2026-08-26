#!/usr/bin/env python3
"""Push the SuperClaw installer to LAN machine B over SSH (user-authorized).

Robustness:
  * auto-detect the local NIC on 10.177.54.0/23 (DHCP may have moved .224)
  * confirm auth with a cheap `whoami` before moving ~2 GB
  * verify remote byte-count == local after transfer
"""
import os
import socket
import sys
import paramiko

HOST, PORT, USER = "10.177.54.203", 22, "Trekker-PTL"
KEY = r"C:\Users\chengan1\.ssh\id_rsa"
LOCAL = r"C:\Users\chengan1\Downloads\superclaw-installer-20260802-testing-version.zip"
REMOTE = r"C:\Users\Trekker-PTL\Downloads\superclaw-installer-20260802-testing-version.zip"


def local_src_ip():
    """Find our IPv4 in 10.177.54/23 to bind as the source (bypass the mis-route)."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetIPAddress -AddressFamily IPv4 | "
             "Where-Object {$_.IPAddress -like '10.177.54.*' -or $_.IPAddress -like '10.177.55.*'} "
             "| Select-Object -First 1 -ExpandProperty IPAddress)"],
            text=True, timeout=20).strip()
        return out or "10.177.54.224"
    except Exception:
        return "10.177.54.224"


def main():
    src = local_src_ip()
    print(f"[push] source-bind {src} -> {HOST}:{PORT} as {USER}")
    local_size = os.path.getsize(LOCAL)
    print(f"[push] local size = {local_size} bytes")

    key = paramiko.RSAKey.from_private_key_file(KEY)  # explicit load (paramiko 5.0 pitfall)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((src, 0))
    sock.settimeout(30)
    sock.connect((HOST, PORT))

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, username=USER, pkey=key, sock=sock,
                timeout=30, allow_agent=False, look_for_keys=False)

    _, out, _ = cli.exec_command("whoami")
    print(f"[push] auth OK, remote whoami = {out.read().decode().strip()}")

    sftp = cli.open_sftp()
    # ensure remote dir exists
    rdir = os.path.dirname(REMOTE).replace("\\", "/")
    try:
        sftp.stat(rdir)
    except IOError:
        print(f"[push] remote dir missing: {rdir}", file=sys.stderr)

    last = {"pct": -1}

    def prog(done, total):
        pct = done * 100 // total
        if pct != last["pct"]:
            last["pct"] = pct
            print(f"\r[push] {done/1048576:.0f}/{total/1048576:.0f} MB ({pct}%)", end="", flush=True)

    sftp.put(LOCAL, REMOTE, callback=prog)
    print()

    remote_size = sftp.stat(REMOTE).st_size
    ok = remote_size == local_size
    print(f"[push] remote size = {remote_size} bytes  match={ok}")
    sftp.close()
    cli.close()
    if not ok:
        sys.exit("SIZE MISMATCH — transfer corrupt")
    print(f"[push] DONE -> {REMOTE}")


if __name__ == "__main__":
    main()
