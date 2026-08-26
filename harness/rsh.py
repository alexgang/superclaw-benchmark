#!/usr/bin/env python3
"""Reusable source-bound SSH exec/SFTP helper for LAN machine B.

Network moved to 10.188.194.x (2026-08 update). B == same machine (MAC bc-f1-05-6a-5b-76).
Usage:
    python rsh.py "whoami"                 # run a cmd.exe command on B
    python rsh.py -ps "Get-Process"        # run PowerShell on B
    from rsh import connect, run           # import for scripts
"""
import argparse
import socket
import subprocess
import sys
import paramiko

HOST, PORT, USER = "10.188.194.206", 22, "Trekker-PTL"
KEY = r"C:\Users\chengan1\.ssh\id_rsa"
# Source prefixes for binding the outbound socket (bypasses the mis-routed
# default route). Update to match the current /21 B is on; covers both /24s.
# Historical: .194/.195 (v1/v2). Current: .193/.194 (2026-08-11 session).
SRC_PREFIXES = ("10.188.193.", "10.188.194.", "10.188.195.")


def local_src_ip():
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {"
             + " -or ".join(f"$_.IPAddress -like '{p}*'" for p in SRC_PREFIXES)
             + "} | Select-Object -First 1 -ExpandProperty IPAddress)"],
            text=True, timeout=20).strip()
        return out or "10.188.194.207"
    except Exception:
        return "10.188.194.207"


def connect():
    key = paramiko.RSAKey.from_private_key_file(KEY)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((local_src_ip(), 0))
    sock.settimeout(30)
    sock.connect((HOST, PORT))
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, username=USER, pkey=key, sock=sock,
                timeout=30, allow_agent=False, look_for_keys=False)
    return cli


def run(cli, cmd, powershell=False):
    if powershell:
        cmd = "powershell -NoProfile -Command " + '"' + cmd.replace('"', '\\"') + '"'
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=120)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return out, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("-ps", "--powershell", action="store_true")
    args = ap.parse_args()
    cli = connect()
    out, err = run(cli, args.cmd, powershell=args.powershell)
    sys.stdout.write(out)
    if err.strip():
        sys.stderr.write("\n[stderr]\n" + err)
    cli.close()


if __name__ == "__main__":
    main()
