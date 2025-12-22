Status: ✅ Implemented. Command servers, docs, and boot images updated.

Add a new document in docs/bash_commands.md that lists all commands and their roles.

For each command listed below.
- Add a bash server to reference_templates
- Add the command to the dockerfile
- Include the reference server in the default boot image
- Only include the reference server in the read-only boot image if the command can't be used to produce side effects on the system
- Document the command in docs/bash_commands.md
  - include the command name and brief description
  - include at least one example using just the command
  - include an example using parameters if the command has parameters
  - include at least one example using the command in a URL pipeline
  - all examples should include links to execute them and view the output
  - all examples should include debug links
  - all examples should have corresponding tests

Make sure the document includes at least one example pipeline with 3 commands.

| Command      | Brief description                                    | Role      |
| ------------ | ---------------------------------------------------- | --------- |
| `awk`        | Pattern scanning and text processing language        | Transform |
| `base64`     | Encode/decode Base64                                 | Transform |
| `basename`   | Strip directory/suffix from a path                   | Transform |
| `bc`         | Arbitrary-precision calculator                       | Transform |
| `bzip2`      | Compress/decompress bzip2 data                       | Dual      |
| `cat`        | Concatenate files / pass stdin through               | Source    |
| `column`     | Align text into columns                              | Transform |
| `comm`       | Compare two **sorted** files line-by-line            | Transform |
| `csvtool`    | Inspect/transform CSV                                | Transform |
| `curl`       | Transfer data from URLs                              | Dual      |
| `cut`        | Extract fields/columns from lines                    | Transform |
| `date`       | Print/format date/time                               | Source    |
| `df`         | Show filesystem space usage                          | Source    |
| `diff`       | Show differences between files/streams               | Transform |
| `dig`        | DNS query tool                                       | Source    |
| `dirname`    | Strip last path component                            | Transform |
| `dmesg`      | Kernel ring buffer messages                          | Source    |
| `docker`     | Container CLI (query or mutate)                      | Dual      |
| `du`         | Disk usage for files/dirs                            | Source    |
| `echo`       | Print arguments                                      | Source    |
| `env`        | Print env or run command with env                    | Dual      |
| `expand`     | Convert tabs to spaces                               | Transform |
| `expr`       | Evaluate simple expressions / string ops             | Transform |
| `file`       | Identify file type by content                        | Source    |
| `find`       | Locate files; can also execute actions               | Dual      |
| `fold`       | Wrap lines to a width                                | Transform |
| `free`       | Memory usage summary                                 | Source    |
| `git`        | VCS; log/diff and also mutates repo                  | Dual      |
| `grep`       | Filter lines by regex                                | Transform |
| `gunzip`     | Decompress gzip                                      | Dual      |
| `gzip`       | Compress/decompress gzip                             | Dual      |
| `head`       | First lines/bytes                                    | Transform |
| `hexdump`    | Hex/ASCII dump                                       | Transform |
| `host`       | DNS lookup tool                                      | Source    |
| `hostname`   | Print hostname                                       | Source    |
| `id`         | User/group identity info                             | Source    |
| `ifconfig`   | Show/configure interfaces (legacy)                   | Dual      |
| `ip`         | Show/configure networking (iproute2)                 | Dual      |
| `jobs`       | List shell jobs                                      | Source    |
| `join`       | Join two files on a key field                        | Transform |
| `jq`         | Query/transform JSON                                 | Transform |
| `journalctl` | Query systemd journal logs                           | Source    |
| `kubectl`    | Kubernetes CLI (query or mutate cluster)             | Dual      |
| `md5sum`     | Hash/check MD5 digests                               | Transform |
| `mktemp`     | Create temp file/dir and print its name              | Dual      |
| `netstat`    | Network connections/routes (legacy)                  | Source    |
| `nl`         | Number lines                                         | Transform |
| `nslookup`   | DNS lookup tool                                      | Source    |
| `od`         | Octal/hex dump                                       | Transform |
| `paste`      | Merge lines as columns                               | Transform |
| `perl`       | Run Perl (often for text processing)                 | Transform |
| `pgrep`      | Find process IDs by match                            | Source    |
| `ping`       | Probe reachability/latency                           | Source    |
| `printenv`   | Print environment variables                          | Source    |
| `printf`     | Formatted output                                     | Source    |
| `ps`         | Process listing                                      | Source    |
| `pwd`        | Print working directory                              | Source    |
| `python`     | Run Python (often for data/text processing)          | Transform |
| `readlink`   | Print symlink target / resolve paths                 | Transform |
| `realpath`   | Canonicalize absolute path                           | Transform |
| `rev`        | Reverse characters per line                          | Transform |
| `rg`         | ripgrep recursive search                             | Transform |
| `sed`        | Stream editor                                        | Transform |
| `seq`        | Generate numeric sequences                           | Source    |
| `sha256sum`  | Hash/check SHA-256 digests                           | Transform |
| `sort`       | Sort lines                                           | Transform |
| `ss`         | Socket statistics                                    | Source    |
| `stat`       | Detailed file metadata                               | Source    |
| `strings`    | Extract printable strings from binary                | Transform |
| `systemctl`  | Query/control services (often queried in one-liners) | Dual      |
| `tar`        | Create/extract archives; can stream to stdout        | Dual      |
| `tail`       | Last lines/bytes                                     | Transform |
| `tee`        | Duplicate stream to file + stdout                    | Dual      |
| `time`       | Measure command runtime                              | Dual      |
| `timeout`    | Run a command with a time limit                      | Dual      |
| `tr`         | Translate/delete characters                          | Transform |
| `traceroute` | Trace network path                                   | Source    |
| `uname`      | System information                                   | Source    |
| `unexpand`   | Convert spaces to tabs                               | Transform |
| `uniq`       | Filter adjacent duplicates                           | Transform |
| `uptime`     | Uptime/load averages                                 | Source    |
| `wc`         | Count lines/words/bytes                              | Transform |
| `wget`       | Download from URLs                                   | Dual      |
| `whoami`     | Effective username                                   | Source    |
| `xargs`      | Build/execute commands from stdin items              | Dual      |
| `xmllint`    | Parse/query/format XML                               | Transform |
| `xxd`        | Hex dump and reverse                                 | Transform |
| `xz`         | Compress/decompress xz data                          | Dual      |
| `yq`         | Query/transform YAML (and often JSON)                | Transform |
| `zcat`       | Decompress .gz to stdout                             | Transform |
| `zip`        | Create ZIP archives                                  | Dual      |
| `unzip`      | Extract ZIP archives                                 | Dual      |
| `man`        | Display manual pages                                 | Source    |
| `tldr`       | Display concise summaries of commands                | Source    |
