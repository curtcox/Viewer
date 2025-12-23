# Bash command servers

This document lists all bash-based servers, their roles, and quick links to run them. 
Use `_` as a placeholder argument when you want to chain input without passing options to the command.

## At-a-glance roles

| Command | Role | Description |
| --- | --- | --- |
| `awk` | Transform | Pattern scanning and text processing language |
| `base64` | Transform | Encode/decode Base64 |
| `basename` | Transform | Strip directory/suffix from a path |
| `bc` | Transform | Arbitrary-precision calculator |
| `bzip2` | Dual | Compress/decompress bzip2 data |
| `cat` | Source | Concatenate files / pass stdin through |
| `column` | Transform | Align text into columns |
| `comm` | Transform | Compare two sorted files line-by-line |
| `csvtool` | Transform | Inspect/transform CSV |
| `curl` | Dual | Transfer data from URLs |
| `cut` | Transform | Extract fields/columns from lines |
| `date` | Source | Print/format date/time |
| `df` | Source | Show filesystem space usage |
| `diff` | Transform | Show differences between files/streams |
| `dig` | Source | DNS query tool |
| `dirname` | Transform | Strip last path component |
| `dmesg` | Source | Kernel ring buffer messages |
| `docker` | Dual | Container CLI (query or mutate) |
| `du` | Source | Disk usage for files/dirs |
| `echo` | Source | Print arguments |
| `env` | Dual | Print env or run command with env |
| `expand` | Transform | Convert tabs to spaces |
| `expr` | Transform | Evaluate simple expressions / string ops |
| `file` | Source | Identify file type by content |
| `find` | Dual | Locate files; can also execute actions |
| `fold` | Transform | Wrap lines to a width |
| `free` | Source | Memory usage summary |
| `git` | Dual | VCS; log/diff and also mutates repo |
| `grep` | Transform | Filter lines by regex |
| `gunzip` | Dual | Decompress gzip |
| `gzip` | Dual | Compress/decompress gzip |
| `head` | Transform | First lines/bytes |
| `hexdump` | Transform | Hex/ASCII dump |
| `host` | Source | DNS lookup tool |
| `hostname` | Source | Print hostname |
| `id` | Source | User/group identity info |
| `ifconfig` | Dual | Show/configure interfaces (legacy) |
| `ip` | Dual | Show/configure networking (iproute2) |
| `jobs` | Source | List shell jobs |
| `join` | Transform | Join two files on a key field |
| `jq` | Transform | Query/transform JSON |
| `journalctl` | Source | Query systemd journal logs |
| `kubectl` | Dual | Kubernetes CLI (query or mutate cluster) |
| `ls` | Source | List directory contents |
| `md5sum` | Transform | Hash/check MD5 digests |
| `mktemp` | Dual | Create temp file/dir and print its name |
| `netstat` | Source | Network connections/routes (legacy) |
| `nl` | Transform | Number lines |
| `nslookup` | Source | DNS lookup tool |
| `od` | Transform | Octal/hex dump |
| `paste` | Transform | Merge lines as columns |
| `perl` | Transform | Run Perl (often for text processing) |
| `pgrep` | Source | Find process IDs by match |
| `ping` | Source | Probe reachability/latency |
| `printenv` | Source | Print environment variables |
| `printf` | Source | Formatted output |
| `ps` | Source | Process listing |
| `pwd` | Source | Print working directory |
| `python` | Transform | Run Python (often for data/text processing) |
| `readlink` | Transform | Print symlink target / resolve paths |
| `realpath` | Transform | Canonicalize absolute path |
| `rev` | Transform | Reverse characters per line |
| `rg` | Transform | ripgrep recursive search |
| `sed` | Transform | Stream editor |
| `seq` | Source | Generate numeric sequences |
| `shasum` | Transform | Hash/check SHA digests |
| `sha256sum` | Transform | Hash/check SHA-256 digests |
| `sort` | Transform | Sort lines |
| `ss` | Source | Socket statistics |
| `stat` | Source | Detailed file metadata |
| `strings` | Transform | Extract printable strings from binary |
| `systemctl` | Dual | Query/control services (often queried in one-liners) |
| `tar` | Dual | Create/extract archives; can stream to stdout |
| `tail` | Transform | Last lines/bytes |
| `tee` | Dual | Duplicate stream to file + stdout |
| `time` | Dual | Measure command runtime |
| `timeout` | Dual | Run a command with a time limit |
| `tr` | Transform | Translate/delete characters |
| `traceroute` | Source | Trace network path |
| `tree` | Source | Display a directory tree |
| `uname` | Source | System information |
| `unexpand` | Transform | Convert spaces to tabs |
| `uniq` | Transform | Filter adjacent duplicates |
| `uptime` | Source | Uptime/load averages |
| `wc` | Transform | Count lines/words/bytes |
| `wget` | Dual | Download from URLs |
| `which` | Source | Locate a command in PATH |
| `whoami` | Source | Effective username |
| `xargs` | Dual | Build/execute commands from stdin items |
| `xmllint` | Transform | Parse/query/format XML |
| `xxd` | Transform | Hex dump and reverse |
| `xz` | Dual | Compress/decompress xz data |
| `yq` | Transform | Query/transform YAML (and often JSON) |
| `zcat` | Transform | Decompress .gz to stdout |
| `zip` | Dual | Create ZIP archives |
| `unzip` | Dual | Extract ZIP archives |
| `man` | Source | Display manual pages |
| `tldr` | Source | Display concise summaries of commands |

## Example 3-command pipeline

Pipeline URLs execute from right to left. The example below uppercases text using three commands:

- `echo` provides the input
- `rev` reverses the string
- `tr` translates lowercase to uppercase

- Pipeline: [Execute](/tr/a-z%20A-Z/rev/_/echo/hello) · [Debug](/tr/a-z%20A-Z/rev/_/echo/hello?debug=true)

## Command reference

### `awk` (Transform)

Pattern scanning and text processing language

- Just the command: [Execute](/awk) · [Debug](/awk?debug=true)
- With parameters: [Execute](/awk/--help) · [Debug](/awk/--help?debug=true)
- In a pipeline: [Execute](/awk/_/echo/Hello%20World) · [Debug](/awk/_/echo/Hello%20World?debug=true)

### `base64` (Transform)

Encode/decode Base64

- Just the command: [Execute](/base64) · [Debug](/base64?debug=true)
- With parameters: [Execute](/base64/--help) · [Debug](/base64/--help?debug=true)
- In a pipeline: [Execute](/base64/_/echo/Hello%20World) · [Debug](/base64/_/echo/Hello%20World?debug=true)

### `basename` (Transform)

Strip directory/suffix from a path

- Just the command: [Execute](/basename) · [Debug](/basename?debug=true)
- With parameters: [Execute](/basename/--help) · [Debug](/basename/--help?debug=true)
- In a pipeline: [Execute](/basename/_/echo/Hello%20World) · [Debug](/basename/_/echo/Hello%20World?debug=true)

### `bc` (Transform)

Arbitrary-precision calculator

- Just the command: [Execute](/bc) · [Debug](/bc?debug=true)
- With parameters: [Execute](/bc/--help) · [Debug](/bc/--help?debug=true)
- In a pipeline: [Execute](/bc/_/echo/Hello%20World) · [Debug](/bc/_/echo/Hello%20World?debug=true)

### `bzip2` (Dual)

Compress/decompress bzip2 data

- Just the command: [Execute](/bzip2) · [Debug](/bzip2?debug=true)
- With parameters: [Execute](/bzip2/--help) · [Debug](/bzip2/--help?debug=true)
- In a pipeline: [Execute](/bzip2/_/echo/Hello%20World) · [Debug](/bzip2/_/echo/Hello%20World?debug=true)

### `cat` (Source)

Concatenate files / pass stdin through

- Just the command: [Execute](/cat) · [Debug](/cat?debug=true)
- With parameters: [Execute](/cat/--help) · [Debug](/cat/--help?debug=true)
- In a pipeline: [Execute](/cat/_/echo/Hello%20World) · [Debug](/cat/_/echo/Hello%20World?debug=true)

### `column` (Transform)

Align text into columns

- Just the command: [Execute](/column) · [Debug](/column?debug=true)
- With parameters: [Execute](/column/--help) · [Debug](/column/--help?debug=true)
- In a pipeline: [Execute](/column/_/echo/Hello%20World) · [Debug](/column/_/echo/Hello%20World?debug=true)

### `comm` (Transform)

Compare two sorted files line-by-line

- Just the command: [Execute](/comm) · [Debug](/comm?debug=true)
- With parameters: [Execute](/comm/--help) · [Debug](/comm/--help?debug=true)
- In a pipeline: [Execute](/comm/_/echo/Hello%20World) · [Debug](/comm/_/echo/Hello%20World?debug=true)

### `csvtool` (Transform)

Inspect/transform CSV

- Just the command: [Execute](/csvtool) · [Debug](/csvtool?debug=true)
- With parameters: [Execute](/csvtool/--help) · [Debug](/csvtool/--help?debug=true)
- In a pipeline: [Execute](/csvtool/_/echo/Hello%20World) · [Debug](/csvtool/_/echo/Hello%20World?debug=true)

### `curl` (Dual)

Transfer data from URLs

- Just the command: [Execute](/curl) · [Debug](/curl?debug=true)
- With parameters: [Execute](/curl/--help) · [Debug](/curl/--help?debug=true)
- In a pipeline: [Execute](/curl/_/echo/Hello%20World) · [Debug](/curl/_/echo/Hello%20World?debug=true)

### `cut` (Transform)

Extract fields/columns from lines

- Just the command: [Execute](/cut) · [Debug](/cut?debug=true)
- With parameters: [Execute](/cut/--help) · [Debug](/cut/--help?debug=true)
- In a pipeline: [Execute](/cut/_/echo/Hello%20World) · [Debug](/cut/_/echo/Hello%20World?debug=true)

### `date` (Source)

Print/format date/time

- Just the command: [Execute](/date) · [Debug](/date?debug=true)
- With parameters: [Execute](/date/--help) · [Debug](/date/--help?debug=true)
- In a pipeline: [Execute](/date/_/echo/Hello%20World) · [Debug](/date/_/echo/Hello%20World?debug=true)

### `df` (Source)

Show filesystem space usage

- Just the command: [Execute](/df) · [Debug](/df?debug=true)
- With parameters: [Execute](/df/--help) · [Debug](/df/--help?debug=true)
- In a pipeline: [Execute](/df/_/echo/Hello%20World) · [Debug](/df/_/echo/Hello%20World?debug=true)

### `diff` (Transform)

Show differences between files/streams

- Just the command: [Execute](/diff) · [Debug](/diff?debug=true)
- With parameters: [Execute](/diff/--help) · [Debug](/diff/--help?debug=true)
- In a pipeline: [Execute](/diff/_/echo/Hello%20World) · [Debug](/diff/_/echo/Hello%20World?debug=true)

### `dig` (Source)

DNS query tool

- Just the command: [Execute](/dig) · [Debug](/dig?debug=true)
- With parameters: [Execute](/dig/--help) · [Debug](/dig/--help?debug=true)
- In a pipeline: [Execute](/dig/_/echo/Hello%20World) · [Debug](/dig/_/echo/Hello%20World?debug=true)

### `dirname` (Transform)

Strip last path component

- Just the command: [Execute](/dirname) · [Debug](/dirname?debug=true)
- With parameters: [Execute](/dirname/--help) · [Debug](/dirname/--help?debug=true)
- In a pipeline: [Execute](/dirname/_/echo/Hello%20World) · [Debug](/dirname/_/echo/Hello%20World?debug=true)

### `dmesg` (Source)

Kernel ring buffer messages

- Just the command: [Execute](/dmesg) · [Debug](/dmesg?debug=true)
- With parameters: [Execute](/dmesg/--help) · [Debug](/dmesg/--help?debug=true)
- In a pipeline: [Execute](/dmesg/_/echo/Hello%20World) · [Debug](/dmesg/_/echo/Hello%20World?debug=true)

### `docker` (Dual)

Container CLI (query or mutate)

- Just the command: [Execute](/docker) · [Debug](/docker?debug=true)
- With parameters: [Execute](/docker/--help) · [Debug](/docker/--help?debug=true)
- In a pipeline: [Execute](/docker/_/echo/Hello%20World) · [Debug](/docker/_/echo/Hello%20World?debug=true)

### `du` (Source)

Disk usage for files/dirs

- Just the command: [Execute](/du) · [Debug](/du?debug=true)
- With parameters: [Execute](/du/--help) · [Debug](/du/--help?debug=true)
- In a pipeline: [Execute](/du/_/echo/Hello%20World) · [Debug](/du/_/echo/Hello%20World?debug=true)

### `echo` (Source)

Print arguments

- Just the command: [Execute](/echo) · [Debug](/echo?debug=true)
- With parameters: [Execute](/echo/--help) · [Debug](/echo/--help?debug=true)
- In a pipeline: [Execute](/echo/_/echo/Hello%20World) · [Debug](/echo/_/echo/Hello%20World?debug=true)

### `env` (Dual)

Print env or run command with env

- Just the command: [Execute](/env) · [Debug](/env?debug=true)
- With parameters: [Execute](/env/--help) · [Debug](/env/--help?debug=true)
- In a pipeline: [Execute](/env/_/echo/Hello%20World) · [Debug](/env/_/echo/Hello%20World?debug=true)

### `expand` (Transform)

Convert tabs to spaces

- Just the command: [Execute](/expand) · [Debug](/expand?debug=true)
- With parameters: [Execute](/expand/--help) · [Debug](/expand/--help?debug=true)
- In a pipeline: [Execute](/expand/_/echo/Hello%20World) · [Debug](/expand/_/echo/Hello%20World?debug=true)

### `expr` (Transform)

Evaluate simple expressions / string ops

- Just the command: [Execute](/expr) · [Debug](/expr?debug=true)
- With parameters: [Execute](/expr/--help) · [Debug](/expr/--help?debug=true)
- In a pipeline: [Execute](/expr/_/echo/Hello%20World) · [Debug](/expr/_/echo/Hello%20World?debug=true)

### `file` (Source)

Identify file type by content

- Just the command: [Execute](/file) · [Debug](/file?debug=true)
- With parameters: [Execute](/file/--help) · [Debug](/file/--help?debug=true)
- In a pipeline: [Execute](/file/_/echo/Hello%20World) · [Debug](/file/_/echo/Hello%20World?debug=true)

### `find` (Dual)

Locate files; can also execute actions

- Just the command: [Execute](/find) · [Debug](/find?debug=true)
- With parameters: [Execute](/find/--help) · [Debug](/find/--help?debug=true)
- In a pipeline: [Execute](/find/_/echo/Hello%20World) · [Debug](/find/_/echo/Hello%20World?debug=true)

### `fold` (Transform)

Wrap lines to a width

- Just the command: [Execute](/fold) · [Debug](/fold?debug=true)
- With parameters: [Execute](/fold/--help) · [Debug](/fold/--help?debug=true)
- In a pipeline: [Execute](/fold/_/echo/Hello%20World) · [Debug](/fold/_/echo/Hello%20World?debug=true)

### `free` (Source)

Memory usage summary

- Just the command: [Execute](/free) · [Debug](/free?debug=true)
- With parameters: [Execute](/free/--help) · [Debug](/free/--help?debug=true)
- In a pipeline: [Execute](/free/_/echo/Hello%20World) · [Debug](/free/_/echo/Hello%20World?debug=true)

### `git` (Dual)

VCS; log/diff and also mutates repo

- Just the command: [Execute](/git) · [Debug](/git?debug=true)
- With parameters: [Execute](/git/--help) · [Debug](/git/--help?debug=true)
- In a pipeline: [Execute](/git/_/echo/Hello%20World) · [Debug](/git/_/echo/Hello%20World?debug=true)

### `grep` (Transform)

Filter lines by regex

- Just the command: [Execute](/grep) · [Debug](/grep?debug=true)
- With parameters: [Execute](/grep/--help) · [Debug](/grep/--help?debug=true)
- In a pipeline: [Execute](/grep/_/echo/Hello%20World) · [Debug](/grep/_/echo/Hello%20World?debug=true)

### `gunzip` (Dual)

Decompress gzip

- Just the command: [Execute](/gunzip) · [Debug](/gunzip?debug=true)
- With parameters: [Execute](/gunzip/--help) · [Debug](/gunzip/--help?debug=true)
- In a pipeline: [Execute](/gunzip/_/echo/Hello%20World) · [Debug](/gunzip/_/echo/Hello%20World?debug=true)

### `gzip` (Dual)

Compress/decompress gzip

- Just the command: [Execute](/gzip) · [Debug](/gzip?debug=true)
- With parameters: [Execute](/gzip/--help) · [Debug](/gzip/--help?debug=true)
- In a pipeline: [Execute](/gzip/_/echo/Hello%20World) · [Debug](/gzip/_/echo/Hello%20World?debug=true)

### `head` (Transform)

First lines/bytes

- Just the command: [Execute](/head) · [Debug](/head?debug=true)
- With parameters: [Execute](/head/--help) · [Debug](/head/--help?debug=true)
- In a pipeline: [Execute](/head/_/echo/Hello%20World) · [Debug](/head/_/echo/Hello%20World?debug=true)

### `hexdump` (Transform)

Hex/ASCII dump

- Just the command: [Execute](/hexdump) · [Debug](/hexdump?debug=true)
- With parameters: [Execute](/hexdump/--help) · [Debug](/hexdump/--help?debug=true)
- In a pipeline: [Execute](/hexdump/_/echo/Hello%20World) · [Debug](/hexdump/_/echo/Hello%20World?debug=true)

### `host` (Source)

DNS lookup tool

- Just the command: [Execute](/host) · [Debug](/host?debug=true)
- With parameters: [Execute](/host/--help) · [Debug](/host/--help?debug=true)
- In a pipeline: [Execute](/host/_/echo/Hello%20World) · [Debug](/host/_/echo/Hello%20World?debug=true)

### `hostname` (Source)

Print hostname

- Just the command: [Execute](/hostname) · [Debug](/hostname?debug=true)
- With parameters: [Execute](/hostname/--help) · [Debug](/hostname/--help?debug=true)
- In a pipeline: [Execute](/hostname/_/echo/Hello%20World) · [Debug](/hostname/_/echo/Hello%20World?debug=true)

### `id` (Source)

User/group identity info

- Just the command: [Execute](/id) · [Debug](/id?debug=true)
- With parameters: [Execute](/id/--help) · [Debug](/id/--help?debug=true)
- In a pipeline: [Execute](/id/_/echo/Hello%20World) · [Debug](/id/_/echo/Hello%20World?debug=true)

### `ifconfig` (Dual)

Show/configure interfaces (legacy)

- Just the command: [Execute](/ifconfig) · [Debug](/ifconfig?debug=true)
- With parameters: [Execute](/ifconfig/--help) · [Debug](/ifconfig/--help?debug=true)
- In a pipeline: [Execute](/ifconfig/_/echo/Hello%20World) · [Debug](/ifconfig/_/echo/Hello%20World?debug=true)

### `ip` (Dual)

Show/configure networking (iproute2)

- Just the command: [Execute](/ip) · [Debug](/ip?debug=true)
- With parameters: [Execute](/ip/--help) · [Debug](/ip/--help?debug=true)
- In a pipeline: [Execute](/ip/_/echo/Hello%20World) · [Debug](/ip/_/echo/Hello%20World?debug=true)

### `jobs` (Source)

List shell jobs

- Just the command: [Execute](/jobs) · [Debug](/jobs?debug=true)
- With parameters: [Execute](/jobs/--help) · [Debug](/jobs/--help?debug=true)
- In a pipeline: [Execute](/jobs/_/echo/Hello%20World) · [Debug](/jobs/_/echo/Hello%20World?debug=true)

### `join` (Transform)

Join two files on a key field

- Just the command: [Execute](/join) · [Debug](/join?debug=true)
- With parameters: [Execute](/join/--help) · [Debug](/join/--help?debug=true)
- In a pipeline: [Execute](/join/_/echo/Hello%20World) · [Debug](/join/_/echo/Hello%20World?debug=true)

### `jq` (Transform)

Query/transform JSON

- Just the command: [Execute](/jq) · [Debug](/jq?debug=true)
- With parameters: [Execute](/jq/--help) · [Debug](/jq/--help?debug=true)
- In a pipeline: [Execute](/jq/_/echo/Hello%20World) · [Debug](/jq/_/echo/Hello%20World?debug=true)

### `journalctl` (Source)

Query systemd journal logs

- Just the command: [Execute](/journalctl) · [Debug](/journalctl?debug=true)
- With parameters: [Execute](/journalctl/--help) · [Debug](/journalctl/--help?debug=true)
- In a pipeline: [Execute](/journalctl/_/echo/Hello%20World) · [Debug](/journalctl/_/echo/Hello%20World?debug=true)

### `kubectl` (Dual)

Kubernetes CLI (query or mutate cluster)

- Just the command: [Execute](/kubectl) · [Debug](/kubectl?debug=true)
- With parameters: [Execute](/kubectl/--help) · [Debug](/kubectl/--help?debug=true)
- In a pipeline: [Execute](/kubectl/_/echo/Hello%20World) · [Debug](/kubectl/_/echo/Hello%20World?debug=true)

### `ls` (Source)

List directory contents

- Just the command: [Execute](/ls) · [Debug](/ls?debug=true)
- With parameters: [Execute](/ls/--help) · [Debug](/ls/--help?debug=true)
- In a pipeline: [Execute](/ls/_/echo/Hello%20World) · [Debug](/ls/_/echo/Hello%20World?debug=true)

### `md5sum` (Transform)

Hash/check MD5 digests

- Just the command: [Execute](/md5sum) · [Debug](/md5sum?debug=true)
- With parameters: [Execute](/md5sum/--help) · [Debug](/md5sum/--help?debug=true)
- In a pipeline: [Execute](/md5sum/_/echo/Hello%20World) · [Debug](/md5sum/_/echo/Hello%20World?debug=true)

### `mktemp` (Dual)

Create temp file/dir and print its name

- Just the command: [Execute](/mktemp) · [Debug](/mktemp?debug=true)
- With parameters: [Execute](/mktemp/--help) · [Debug](/mktemp/--help?debug=true)
- In a pipeline: [Execute](/mktemp/_/echo/Hello%20World) · [Debug](/mktemp/_/echo/Hello%20World?debug=true)

### `netstat` (Source)

Network connections/routes (legacy)

- Just the command: [Execute](/netstat) · [Debug](/netstat?debug=true)
- With parameters: [Execute](/netstat/--help) · [Debug](/netstat/--help?debug=true)
- In a pipeline: [Execute](/netstat/_/echo/Hello%20World) · [Debug](/netstat/_/echo/Hello%20World?debug=true)

### `nl` (Transform)

Number lines

- Just the command: [Execute](/nl) · [Debug](/nl?debug=true)
- With parameters: [Execute](/nl/--help) · [Debug](/nl/--help?debug=true)
- In a pipeline: [Execute](/nl/_/echo/Hello%20World) · [Debug](/nl/_/echo/Hello%20World?debug=true)

### `nslookup` (Source)

DNS lookup tool

- Just the command: [Execute](/nslookup) · [Debug](/nslookup?debug=true)
- With parameters: [Execute](/nslookup/--help) · [Debug](/nslookup/--help?debug=true)
- In a pipeline: [Execute](/nslookup/_/echo/Hello%20World) · [Debug](/nslookup/_/echo/Hello%20World?debug=true)

### `od` (Transform)

Octal/hex dump

- Just the command: [Execute](/od) · [Debug](/od?debug=true)
- With parameters: [Execute](/od/--help) · [Debug](/od/--help?debug=true)
- In a pipeline: [Execute](/od/_/echo/Hello%20World) · [Debug](/od/_/echo/Hello%20World?debug=true)

### `paste` (Transform)

Merge lines as columns

- Just the command: [Execute](/paste) · [Debug](/paste?debug=true)
- With parameters: [Execute](/paste/--help) · [Debug](/paste/--help?debug=true)
- In a pipeline: [Execute](/paste/_/echo/Hello%20World) · [Debug](/paste/_/echo/Hello%20World?debug=true)

### `perl` (Transform)

Run Perl (often for text processing)

- Just the command: [Execute](/perl) · [Debug](/perl?debug=true)
- With parameters: [Execute](/perl/--help) · [Debug](/perl/--help?debug=true)
- In a pipeline: [Execute](/perl/_/echo/Hello%20World) · [Debug](/perl/_/echo/Hello%20World?debug=true)

### `pgrep` (Source)

Find process IDs by match

- Just the command: [Execute](/pgrep) · [Debug](/pgrep?debug=true)
- With parameters: [Execute](/pgrep/--help) · [Debug](/pgrep/--help?debug=true)
- In a pipeline: [Execute](/pgrep/_/echo/Hello%20World) · [Debug](/pgrep/_/echo/Hello%20World?debug=true)

### `ping` (Source)

Probe reachability/latency

- Just the command: [Execute](/ping) · [Debug](/ping?debug=true)
- With parameters: [Execute](/ping/--help) · [Debug](/ping/--help?debug=true)
- In a pipeline: [Execute](/ping/_/echo/Hello%20World) · [Debug](/ping/_/echo/Hello%20World?debug=true)

### `printenv` (Source)

Print environment variables

- Just the command: [Execute](/printenv) · [Debug](/printenv?debug=true)
- With parameters: [Execute](/printenv/--help) · [Debug](/printenv/--help?debug=true)
- In a pipeline: [Execute](/printenv/_/echo/Hello%20World) · [Debug](/printenv/_/echo/Hello%20World?debug=true)

### `printf` (Source)

Formatted output

- Just the command: [Execute](/printf) · [Debug](/printf?debug=true)
- With parameters: [Execute](/printf/--help) · [Debug](/printf/--help?debug=true)
- In a pipeline: [Execute](/printf/_/echo/Hello%20World) · [Debug](/printf/_/echo/Hello%20World?debug=true)

### `ps` (Source)

Process listing

- Just the command: [Execute](/ps) · [Debug](/ps?debug=true)
- With parameters: [Execute](/ps/--help) · [Debug](/ps/--help?debug=true)
- In a pipeline: [Execute](/ps/_/echo/Hello%20World) · [Debug](/ps/_/echo/Hello%20World?debug=true)

### `pwd` (Source)

Print working directory

- Just the command: [Execute](/pwd) · [Debug](/pwd?debug=true)
- With parameters: [Execute](/pwd/--help) · [Debug](/pwd/--help?debug=true)
- In a pipeline: [Execute](/pwd/_/echo/Hello%20World) · [Debug](/pwd/_/echo/Hello%20World?debug=true)

### `python` (Transform)

Run Python (often for data/text processing)

- Just the command: [Execute](/python) · [Debug](/python?debug=true)
- With parameters: [Execute](/python/--help) · [Debug](/python/--help?debug=true)
- In a pipeline: [Execute](/python/_/echo/Hello%20World) · [Debug](/python/_/echo/Hello%20World?debug=true)

### `readlink` (Transform)

Print symlink target / resolve paths

- Just the command: [Execute](/readlink) · [Debug](/readlink?debug=true)
- With parameters: [Execute](/readlink/--help) · [Debug](/readlink/--help?debug=true)
- In a pipeline: [Execute](/readlink/_/echo/Hello%20World) · [Debug](/readlink/_/echo/Hello%20World?debug=true)

### `realpath` (Transform)

Canonicalize absolute path

- Just the command: [Execute](/realpath) · [Debug](/realpath?debug=true)
- With parameters: [Execute](/realpath/--help) · [Debug](/realpath/--help?debug=true)
- In a pipeline: [Execute](/realpath/_/echo/Hello%20World) · [Debug](/realpath/_/echo/Hello%20World?debug=true)

### `rev` (Transform)

Reverse characters per line

- Just the command: [Execute](/rev) · [Debug](/rev?debug=true)
- With parameters: [Execute](/rev/--help) · [Debug](/rev/--help?debug=true)
- In a pipeline: [Execute](/rev/_/echo/Hello%20World) · [Debug](/rev/_/echo/Hello%20World?debug=true)

### `rg` (Transform)

ripgrep recursive search

- Just the command: [Execute](/rg) · [Debug](/rg?debug=true)
- With parameters: [Execute](/rg/--help) · [Debug](/rg/--help?debug=true)
- In a pipeline: [Execute](/rg/_/echo/Hello%20World) · [Debug](/rg/_/echo/Hello%20World?debug=true)

### `sed` (Transform)

Stream editor

- Just the command: [Execute](/sed) · [Debug](/sed?debug=true)
- With parameters: [Execute](/sed/--help) · [Debug](/sed/--help?debug=true)
- In a pipeline: [Execute](/sed/_/echo/Hello%20World) · [Debug](/sed/_/echo/Hello%20World?debug=true)

### `seq` (Source)

Generate numeric sequences

- Just the command: [Execute](/seq) · [Debug](/seq?debug=true)
- With parameters: [Execute](/seq/--help) · [Debug](/seq/--help?debug=true)
- In a pipeline: [Execute](/seq/_/echo/Hello%20World) · [Debug](/seq/_/echo/Hello%20World?debug=true)

### `shasum` (Transform)

Hash/check SHA digests

- Just the command: [Execute](/shasum) · [Debug](/shasum?debug=true)
- With parameters: [Execute](/shasum/--help) · [Debug](/shasum/--help?debug=true)
- In a pipeline: [Execute](/shasum/_/echo/Hello%20World) · [Debug](/shasum/_/echo/Hello%20World?debug=true)

### `sha256sum` (Transform)

Hash/check SHA-256 digests

- Just the command: [Execute](/sha256sum) · [Debug](/sha256sum?debug=true)
- With parameters: [Execute](/sha256sum/--help) · [Debug](/sha256sum/--help?debug=true)
- In a pipeline: [Execute](/sha256sum/_/echo/Hello%20World) · [Debug](/sha256sum/_/echo/Hello%20World?debug=true)

### `sort` (Transform)

Sort lines

- Just the command: [Execute](/sort) · [Debug](/sort?debug=true)
- With parameters: [Execute](/sort/--help) · [Debug](/sort/--help?debug=true)
- In a pipeline: [Execute](/sort/_/echo/Hello%20World) · [Debug](/sort/_/echo/Hello%20World?debug=true)

### `ss` (Source)

Socket statistics

- Just the command: [Execute](/ss) · [Debug](/ss?debug=true)
- With parameters: [Execute](/ss/--help) · [Debug](/ss/--help?debug=true)
- In a pipeline: [Execute](/ss/_/echo/Hello%20World) · [Debug](/ss/_/echo/Hello%20World?debug=true)

### `stat` (Source)

Detailed file metadata

- Just the command: [Execute](/stat) · [Debug](/stat?debug=true)
- With parameters: [Execute](/stat/--help) · [Debug](/stat/--help?debug=true)
- In a pipeline: [Execute](/stat/_/echo/Hello%20World) · [Debug](/stat/_/echo/Hello%20World?debug=true)

### `strings` (Transform)

Extract printable strings from binary

- Just the command: [Execute](/strings) · [Debug](/strings?debug=true)
- With parameters: [Execute](/strings/--help) · [Debug](/strings/--help?debug=true)
- In a pipeline: [Execute](/strings/_/echo/Hello%20World) · [Debug](/strings/_/echo/Hello%20World?debug=true)

### `systemctl` (Dual)

Query/control services (often queried in one-liners)

- Just the command: [Execute](/systemctl) · [Debug](/systemctl?debug=true)
- With parameters: [Execute](/systemctl/--help) · [Debug](/systemctl/--help?debug=true)
- In a pipeline: [Execute](/systemctl/_/echo/Hello%20World) · [Debug](/systemctl/_/echo/Hello%20World?debug=true)

### `tar` (Dual)

Create/extract archives; can stream to stdout

- Just the command: [Execute](/tar) · [Debug](/tar?debug=true)
- With parameters: [Execute](/tar/--help) · [Debug](/tar/--help?debug=true)
- In a pipeline: [Execute](/tar/_/echo/Hello%20World) · [Debug](/tar/_/echo/Hello%20World?debug=true)

### `tail` (Transform)

Last lines/bytes

- Just the command: [Execute](/tail) · [Debug](/tail?debug=true)
- With parameters: [Execute](/tail/--help) · [Debug](/tail/--help?debug=true)
- In a pipeline: [Execute](/tail/_/echo/Hello%20World) · [Debug](/tail/_/echo/Hello%20World?debug=true)

### `tee` (Dual)

Duplicate stream to file + stdout

- Just the command: [Execute](/tee) · [Debug](/tee?debug=true)
- With parameters: [Execute](/tee/--help) · [Debug](/tee/--help?debug=true)
- In a pipeline: [Execute](/tee/_/echo/Hello%20World) · [Debug](/tee/_/echo/Hello%20World?debug=true)

### `time` (Dual)

Measure command runtime

- Just the command: [Execute](/time) · [Debug](/time?debug=true)
- With parameters: [Execute](/time/--help) · [Debug](/time/--help?debug=true)
- In a pipeline: [Execute](/time/_/echo/Hello%20World) · [Debug](/time/_/echo/Hello%20World?debug=true)

### `timeout` (Dual)

Run a command with a time limit

- Just the command: [Execute](/timeout) · [Debug](/timeout?debug=true)
- With parameters: [Execute](/timeout/--help) · [Debug](/timeout/--help?debug=true)
- In a pipeline: [Execute](/timeout/_/echo/Hello%20World) · [Debug](/timeout/_/echo/Hello%20World?debug=true)

### `tr` (Transform)

Translate/delete characters

- Just the command: [Execute](/tr) · [Debug](/tr?debug=true)
- With parameters: [Execute](/tr/--help) · [Debug](/tr/--help?debug=true)
- In a pipeline: [Execute](/tr/_/echo/Hello%20World) · [Debug](/tr/_/echo/Hello%20World?debug=true)

### `traceroute` (Source)

Trace network path

- Just the command: [Execute](/traceroute) · [Debug](/traceroute?debug=true)
- With parameters: [Execute](/traceroute/--help) · [Debug](/traceroute/--help?debug=true)
- In a pipeline: [Execute](/traceroute/_/echo/Hello%20World) · [Debug](/traceroute/_/echo/Hello%20World?debug=true)

### `tree` (Source)

Display a directory tree

- Just the command: [Execute](/tree) · [Debug](/tree?debug=true)
- With parameters: [Execute](/tree/--help) · [Debug](/tree/--help?debug=true)
- In a pipeline: [Execute](/tree/_/echo/Hello%20World) · [Debug](/tree/_/echo/Hello%20World?debug=true)

### `uname` (Source)

System information

- Just the command: [Execute](/uname) · [Debug](/uname?debug=true)
- With parameters: [Execute](/uname/--help) · [Debug](/uname/--help?debug=true)
- In a pipeline: [Execute](/uname/_/echo/Hello%20World) · [Debug](/uname/_/echo/Hello%20World?debug=true)

### `unexpand` (Transform)

Convert spaces to tabs

- Just the command: [Execute](/unexpand) · [Debug](/unexpand?debug=true)
- With parameters: [Execute](/unexpand/--help) · [Debug](/unexpand/--help?debug=true)
- In a pipeline: [Execute](/unexpand/_/echo/Hello%20World) · [Debug](/unexpand/_/echo/Hello%20World?debug=true)

### `uniq` (Transform)

Filter adjacent duplicates

- Just the command: [Execute](/uniq) · [Debug](/uniq?debug=true)
- With parameters: [Execute](/uniq/--help) · [Debug](/uniq/--help?debug=true)
- In a pipeline: [Execute](/uniq/_/echo/Hello%20World) · [Debug](/uniq/_/echo/Hello%20World?debug=true)

### `uptime` (Source)

Uptime/load averages

- Just the command: [Execute](/uptime) · [Debug](/uptime?debug=true)
- With parameters: [Execute](/uptime/--help) · [Debug](/uptime/--help?debug=true)
- In a pipeline: [Execute](/uptime/_/echo/Hello%20World) · [Debug](/uptime/_/echo/Hello%20World?debug=true)

### `wc` (Transform)

Count lines/words/bytes

- Just the command: [Execute](/wc) · [Debug](/wc?debug=true)
- With parameters: [Execute](/wc/--help) · [Debug](/wc/--help?debug=true)
- In a pipeline: [Execute](/wc/_/echo/Hello%20World) · [Debug](/wc/_/echo/Hello%20World?debug=true)

### `wget` (Dual)

Download from URLs

- Just the command: [Execute](/wget) · [Debug](/wget?debug=true)
- With parameters: [Execute](/wget/--help) · [Debug](/wget/--help?debug=true)
- In a pipeline: [Execute](/wget/_/echo/Hello%20World) · [Debug](/wget/_/echo/Hello%20World?debug=true)

### `which` (Source)

Locate a command in PATH

- Just the command: [Execute](/which) · [Debug](/which?debug=true)
- With parameters: [Execute](/which/--help) · [Debug](/which/--help?debug=true)
- In a pipeline: [Execute](/which/_/echo/Hello%20World) · [Debug](/which/_/echo/Hello%20World?debug=true)

### `whoami` (Source)

Effective username

- Just the command: [Execute](/whoami) · [Debug](/whoami?debug=true)
- With parameters: [Execute](/whoami/--help) · [Debug](/whoami/--help?debug=true)
- In a pipeline: [Execute](/whoami/_/echo/Hello%20World) · [Debug](/whoami/_/echo/Hello%20World?debug=true)

### `xargs` (Dual)

Build/execute commands from stdin items

- Just the command: [Execute](/xargs) · [Debug](/xargs?debug=true)
- With parameters: [Execute](/xargs/--help) · [Debug](/xargs/--help?debug=true)
- In a pipeline: [Execute](/xargs/_/echo/Hello%20World) · [Debug](/xargs/_/echo/Hello%20World?debug=true)

### `xmllint` (Transform)

Parse/query/format XML

- Just the command: [Execute](/xmllint) · [Debug](/xmllint?debug=true)
- With parameters: [Execute](/xmllint/--help) · [Debug](/xmllint/--help?debug=true)
- In a pipeline: [Execute](/xmllint/_/echo/Hello%20World) · [Debug](/xmllint/_/echo/Hello%20World?debug=true)

### `xxd` (Transform)

Hex dump and reverse

- Just the command: [Execute](/xxd) · [Debug](/xxd?debug=true)
- With parameters: [Execute](/xxd/--help) · [Debug](/xxd/--help?debug=true)
- In a pipeline: [Execute](/xxd/_/echo/Hello%20World) · [Debug](/xxd/_/echo/Hello%20World?debug=true)

### `xz` (Dual)

Compress/decompress xz data

- Just the command: [Execute](/xz) · [Debug](/xz?debug=true)
- With parameters: [Execute](/xz/--help) · [Debug](/xz/--help?debug=true)
- In a pipeline: [Execute](/xz/_/echo/Hello%20World) · [Debug](/xz/_/echo/Hello%20World?debug=true)

### `yq` (Transform)

Query/transform YAML (and often JSON)

- Just the command: [Execute](/yq) · [Debug](/yq?debug=true)
- With parameters: [Execute](/yq/--help) · [Debug](/yq/--help?debug=true)
- In a pipeline: [Execute](/yq/_/echo/Hello%20World) · [Debug](/yq/_/echo/Hello%20World?debug=true)

### `zcat` (Transform)

Decompress .gz to stdout

- Just the command: [Execute](/zcat) · [Debug](/zcat?debug=true)
- With parameters: [Execute](/zcat/--help) · [Debug](/zcat/--help?debug=true)
- In a pipeline: [Execute](/zcat/_/echo/Hello%20World) · [Debug](/zcat/_/echo/Hello%20World?debug=true)

### `zip` (Dual)

Create ZIP archives

- Just the command: [Execute](/zip) · [Debug](/zip?debug=true)
- With parameters: [Execute](/zip/--help) · [Debug](/zip/--help?debug=true)
- In a pipeline: [Execute](/zip/_/echo/Hello%20World) · [Debug](/zip/_/echo/Hello%20World?debug=true)

### `unzip` (Dual)

Extract ZIP archives

- Just the command: [Execute](/unzip) · [Debug](/unzip?debug=true)
- With parameters: [Execute](/unzip/--help) · [Debug](/unzip/--help?debug=true)
- In a pipeline: [Execute](/unzip/_/echo/Hello%20World) · [Debug](/unzip/_/echo/Hello%20World?debug=true)

### `man` (Source)

Display manual pages

- Just the command: [Execute](/man) · [Debug](/man?debug=true)
- With parameters: [Execute](/man/--help) · [Debug](/man/--help?debug=true)
- In a pipeline: [Execute](/man/_/echo/Hello%20World) · [Debug](/man/_/echo/Hello%20World?debug=true)

### `tldr` (Source)

Display concise summaries of commands

- Just the command: [Execute](/tldr) · [Debug](/tldr?debug=true)
- With parameters: [Execute](/tldr/--help) · [Debug](/tldr/--help?debug=true)
- In a pipeline: [Execute](/tldr/_/echo/Hello%20World) · [Debug](/tldr/_/echo/Hello%20World?debug=true)
