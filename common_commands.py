"""Shared metadata for common bash command servers and documentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class CommandInfo:
    """Details about a common bash command available as a server."""

    name: str
    description: str
    role: str  # Source | Transform | Dual

    @property
    def safe_for_readonly(self) -> bool:
        """Commands marked as Dual can mutate system state and stay out of readonly boots."""

        return self.role.lower() != "dual"


def _command(name: str, description: str, role: str) -> CommandInfo:
    return CommandInfo(name=name, description=description, role=role)


COMMON_COMMANDS: List[CommandInfo] = [
    _command("awk", "Pattern scanning and text processing language", "Transform"),
    _command("base64", "Encode/decode Base64", "Transform"),
    _command("basename", "Strip directory/suffix from a path", "Transform"),
    _command("bc", "Arbitrary-precision calculator", "Transform"),
    _command("bzip2", "Compress/decompress bzip2 data", "Dual"),
    _command("cat", "Concatenate files / pass stdin through", "Source"),
    _command("column", "Align text into columns", "Transform"),
    _command("comm", "Compare two sorted files line-by-line", "Transform"),
    _command("csvtool", "Inspect/transform CSV", "Transform"),
    _command("curl", "Transfer data from URLs", "Dual"),
    _command("cut", "Extract fields/columns from lines", "Transform"),
    _command("date", "Print/format date/time", "Source"),
    _command("df", "Show filesystem space usage", "Source"),
    _command("diff", "Show differences between files/streams", "Transform"),
    _command("dig", "DNS query tool", "Source"),
    _command("dirname", "Strip last path component", "Transform"),
    _command("dmesg", "Kernel ring buffer messages", "Source"),
    _command("docker", "Container CLI (query or mutate)", "Dual"),
    _command("du", "Disk usage for files/dirs", "Source"),
    _command("echo", "Print arguments", "Source"),
    _command("env", "Print env or run command with env", "Dual"),
    _command("expand", "Convert tabs to spaces", "Transform"),
    _command("expr", "Evaluate simple expressions / string ops", "Transform"),
    _command("file", "Identify file type by content", "Source"),
    _command("find", "Locate files; can also execute actions", "Dual"),
    _command("fold", "Wrap lines to a width", "Transform"),
    _command("free", "Memory usage summary", "Source"),
    _command("git", "VCS; log/diff and also mutates repo", "Dual"),
    _command("grep", "Filter lines by regex", "Transform"),
    _command("gunzip", "Decompress gzip", "Dual"),
    _command("gzip", "Compress/decompress gzip", "Dual"),
    _command("head", "First lines/bytes", "Transform"),
    _command("hexdump", "Hex/ASCII dump", "Transform"),
    _command("host", "DNS lookup tool", "Source"),
    _command("hostname", "Print hostname", "Source"),
    _command("id", "User/group identity info", "Source"),
    _command("ifconfig", "Show/configure interfaces (legacy)", "Dual"),
    _command("ip", "Show/configure networking (iproute2)", "Dual"),
    _command("jobs", "List shell jobs", "Source"),
    _command("join", "Join two files on a key field", "Transform"),
    _command("jq", "Query/transform JSON", "Transform"),
    _command("journalctl", "Query systemd journal logs", "Source"),
    _command("kubectl", "Kubernetes CLI (query or mutate cluster)", "Dual"),
    _command("md5sum", "Hash/check MD5 digests", "Transform"),
    _command("mktemp", "Create temp file/dir and print its name", "Dual"),
    _command("netstat", "Network connections/routes (legacy)", "Source"),
    _command("nl", "Number lines", "Transform"),
    _command("nslookup", "DNS lookup tool", "Source"),
    _command("od", "Octal/hex dump", "Transform"),
    _command("paste", "Merge lines as columns", "Transform"),
    _command("perl", "Run Perl (often for text processing)", "Transform"),
    _command("pgrep", "Find process IDs by match", "Source"),
    _command("ping", "Probe reachability/latency", "Source"),
    _command("printenv", "Print environment variables", "Source"),
    _command("printf", "Formatted output", "Source"),
    _command("ps", "Process listing", "Source"),
    _command("pwd", "Print working directory", "Source"),
    _command("python", "Run Python (often for data/text processing)", "Transform"),
    _command("readlink", "Print symlink target / resolve paths", "Transform"),
    _command("realpath", "Canonicalize absolute path", "Transform"),
    _command("rev", "Reverse characters per line", "Transform"),
    _command("rg", "ripgrep recursive search", "Transform"),
    _command("sed", "Stream editor", "Transform"),
    _command("seq", "Generate numeric sequences", "Source"),
    _command("sha256sum", "Hash/check SHA-256 digests", "Transform"),
    _command("sort", "Sort lines", "Transform"),
    _command("ss", "Socket statistics", "Source"),
    _command("stat", "Detailed file metadata", "Source"),
    _command("strings", "Extract printable strings from binary", "Transform"),
    _command("systemctl", "Query/control services (often queried in one-liners)", "Dual"),
    _command("tar", "Create/extract archives; can stream to stdout", "Dual"),
    _command("tail", "Last lines/bytes", "Transform"),
    _command("tee", "Duplicate stream to file + stdout", "Dual"),
    _command("time", "Measure command runtime", "Dual"),
    _command("timeout", "Run a command with a time limit", "Dual"),
    _command("tr", "Translate/delete characters", "Transform"),
    _command("traceroute", "Trace network path", "Source"),
    _command("uname", "System information", "Source"),
    _command("unexpand", "Convert spaces to tabs", "Transform"),
    _command("uniq", "Filter adjacent duplicates", "Transform"),
    _command("uptime", "Uptime/load averages", "Source"),
    _command("wc", "Count lines/words/bytes", "Transform"),
    _command("wget", "Download from URLs", "Dual"),
    _command("whoami", "Effective username", "Source"),
    _command("xargs", "Build/execute commands from stdin items", "Dual"),
    _command("xmllint", "Parse/query/format XML", "Transform"),
    _command("xxd", "Hex dump and reverse", "Transform"),
    _command("xz", "Compress/decompress xz data", "Dual"),
    _command("yq", "Query/transform YAML (and often JSON)", "Transform"),
    _command("zcat", "Decompress .gz to stdout", "Transform"),
    _command("zip", "Create ZIP archives", "Dual"),
    _command("unzip", "Extract ZIP archives", "Dual"),
    _command("man", "Display manual pages", "Source"),
    _command("tldr", "Display concise summaries of commands", "Source"),
]


def group_commands_for_readonly(commands: Iterable[CommandInfo]) -> list[CommandInfo]:
    """Return commands safe to include in the readonly boot image."""

    return [command for command in commands if command.safe_for_readonly]

