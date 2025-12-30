"""Generate the bash commands reference document from shared metadata."""

from __future__ import annotations

from textwrap import dedent

from common_commands import CommandInfo


def _example_links(path: str) -> str:
    return f"[Execute]({path}) · [Debug]({path}?debug=true)"


def _example_block(command: CommandInfo) -> list[str]:
    base_path = f"/{command.name}"
    parameter_path = f"{base_path}/--help"
    pipeline_path = f"{base_path}/_/echo/Hello%20World"

    return [
        f"- Just the command: {_example_links(base_path)}",
        f"- With parameters: {_example_links(parameter_path)}",
        f"- In a pipeline: {_example_links(pipeline_path)}",
    ]


COMMAND_EXAMPLE_OVERRIDES: dict[str, list[str]] = {
    "awk": dedent(
        """
        - Default field selection (prints the first column): [Execute](/awk/%7Bprint%20$1%7D/_/printf%20%22alice%20engineer%5Cnben%20designer%5Cn%22) · [Debug](/awk/%7Bprint%20$1%7D/_/printf%20%22alice%20engineer%5Cnben%20designer%5Cn%22?debug=true)
          - Bash: `printf "alice engineer\nben designer\n" | awk '{print $1}'`
          - Output:
            ```text
            alice
            ben
            ```
        - Custom delimiter to grab the domain column: [Execute](/awk/-F%20:%20%27{print%20$2}%27/_/printf%20%22user%3Aexample.com%5Cnadmin%3Aexample.org%5Cn%22) · [Debug](/awk/-F%20:%20%27{print%20$2}%27/_/printf%20%22user%3Aexample.com%5Cnadmin%3Aexample.org%5Cn%22?debug=true)
          - Bash: `printf "user:example.com\nadmin:example.org\n" | awk -F : '{print $2}'`
          - Output:
            ```text
            example.com
            example.org
            ```
        """
    ).strip().splitlines(),
    "cut": dedent(
        """
        - Default (tab-delimited) field extraction: [Execute](/cut/-f1/_/printf%20%22name%5Ctcity%5CnAda%5CtBoston%5CnTerry%5CtDenver%5Cn%22) · [Debug](/cut/-f1/_/printf%20%22name%5Ctcity%5CnAda%5CtBoston%5CnTerry%5CtDenver%5Cn%22?debug=true)
          - Bash: `printf "name\tcity\nAda\tBoston\nTerry\tDenver\n" | cut -f1`
          - Output:
            ```text
            name
            Ada
            Terry
            ```
        - Custom delimiter for CSV-style input: [Execute](/cut/-d%20,%20-f2/_/printf%20%22user%2Cemail%5Cnanna%2Canna%40example.com%5Cnbob%2Cbob%40example.net%5Cn%22) · [Debug](/cut/-d%20,%20-f2/_/printf%20%22user%2Cemail%5Cnanna%2Canna%40example.com%5Cnbob%2Cbob%40example.net%5Cn%22?debug=true)
          - Bash: `printf "user,email\nanna,anna@example.com\nbob,bob@example.net\n" | cut -d , -f2`
          - Output:
            ```text
            email
            anna@example.com
            bob@example.net
            ```
        """
    ).strip().splitlines(),
    "head": dedent(
        """
        - Default first 10 lines: [Execute](/head/_/printf%20%221%5Cn2%5Cn3%5Cn4%5Cn5%5Cn6%5Cn7%5Cn8%5Cn9%5Cn10%5Cn11%5Cn%22) · [Debug](/head/_/printf%20%221%5Cn2%5Cn3%5Cn4%5Cn5%5Cn6%5Cn7%5Cn8%5Cn9%5Cn10%5Cn11%5Cn%22?debug=true)
          - Bash: `printf "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n" | head`
          - Output:
            ```text
            1
            2
            3
            4
            5
            6
            7
            8
            9
            10
            ```
        - Custom line count with `-n 3`: [Execute](/head/-n%203/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cndelta%5Cn%22) · [Debug](/head/-n%203/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cndelta%5Cn%22?debug=true)
          - Bash: `printf "alpha\nbeta\ngamma\ndelta\n" | head -n 3`
          - Output:
            ```text
            alpha
            beta
            gamma
            ```
        """
    ).strip().splitlines(),
    "tail": dedent(
        """
        - Default last 10 lines: [Execute](/tail/_/printf%20%221%5Cn2%5Cn3%5Cn4%5Cn5%5Cn6%5Cn7%5Cn8%5Cn9%5Cn10%5Cn11%5Cn%22) · [Debug](/tail/_/printf%20%221%5Cn2%5Cn3%5Cn4%5Cn5%5Cn6%5Cn7%5Cn8%5Cn9%5Cn10%5Cn11%5Cn%22?debug=true)
          - Bash: `printf "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n" | tail`
          - Output:
            ```text
            2
            3
            4
            5
            6
            7
            8
            9
            10
            11
            ```
        - Custom line count with `-n 2`: [Execute](/tail/-n%202/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cndelta%5Cn%22) · [Debug](/tail/-n%202/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cndelta%5Cn%22?debug=true)
          - Bash: `printf "alpha\nbeta\ngamma\ndelta\n" | tail -n 2`
          - Output:
            ```text
            gamma
            delta
            ```
        """
    ).strip().splitlines(),
    "sort": dedent(
        """
        - Default ascending sort: [Execute](/sort/_/printf%20%22banana%5Cnapple%5Cnochard%5Cn%22) · [Debug](/sort/_/printf%20%22banana%5Cnapple%5Cnochard%5Cn%22?debug=true)
          - Bash: `printf "banana\napple\nochard\n" | sort`
          - Output:
            ```text
            apple
            banana
            chard
            ```
        - Reverse sort with `-r`: [Execute](/sort/-r/_/printf%20%222%5Cn10%5Cn5%5Cn%22) · [Debug](/sort/-r/_/printf%20%222%5Cn10%5Cn5%5Cn%22?debug=true)
          - Bash: `printf "2\n10\n5\n" | sort -r`
          - Output:
            ```text
            5
            2
            10
            ```
        """
    ).strip().splitlines(),
    "sed": dedent(
        r"""
        - Default substitution (replaces first match on each line): [Execute](/sed/s/foo/bar/_/printf%20%22foo%20start%5Cnfoo%20middle%5Cnplain%5Cn%22) · [Debug](/sed/s/foo/bar/_/printf%20%22foo%20start%5Cnfoo%20middle%5Cnplain%5Cn%22?debug=true)
          - Bash: `printf "foo start\nfoo middle\nplain\n" | sed 's/foo/bar/'`
          - Output:
            ```text
            bar start
            bar middle
            plain
            ```
        - Global substitution with `g` flag: [Execute](/sed/s/-/\//g/_/printf%20%22path-with-dashes%5Cnother-path%5Cn%22) · [Debug](/sed/s/-/\//g/_/printf%20%22path-with-dashes%5Cnother-path%5Cn%22?debug=true)
          - Bash: `printf "path-with-dashes\nother-path\n" | sed 's/-/\//g'`
          - Output:
            ```text
            path/with/dashes
            other/path
            ```
        """
    ).strip().splitlines(),
    "tr": dedent(
        """
        - Default transliteration example (lowercase to uppercase): [Execute](/tr/a-z/A-Z/_/echo/hello) · [Debug](/tr/a-z/A-Z/_/echo/hello?debug=true)
          - Bash: `echo hello | tr a-z A-Z`
          - Output:
            ```text
            HELLO
            ```
        - Delete characters with `-d`: [Execute](/tr/-d%200-9/_/printf%20%22room101%5Cnlevel42%5Cn%22) · [Debug](/tr/-d%200-9/_/printf%20%22room101%5Cnlevel42%5Cn%22?debug=true)
          - Bash: `printf "room101\nlevel42\n" | tr -d 0-9`
          - Output:
            ```text
            room
            level
            ```
        """
    ).strip().splitlines(),
    "column": dedent(
        """
        - Tab-align whitespace-separated columns (default): [Execute](/column/-t/_/printf%20%22name%20age%5CnAna%2029%5CnBen%2031%5Cn%22) · [Debug](/column/-t/_/printf%20%22name%20age%5CnAna%2029%5CnBen%2031%5Cn%22?debug=true)
          - Bash: `printf "name age\nAna 29\nBen 31\n" | column -t`
          - Output:
            ```text
            name  age
            Ana   29
            Ben   31
            ```
        - Custom delimiter with `-s , -t`: [Execute](/column/-s%20,%20-t/_/printf%20%22name,city%5CnRavi,Delhi%5CnMia,Rome%5Cn%22) · [Debug](/column/-s%20,%20-t/_/printf%20%22name,city%5CnRavi,Delhi%5CnMia,Rome%5Cn%22?debug=true)
          - Bash: `printf "name,city\nRavi,Delhi\nMia,Rome\n" | column -s , -t`
          - Output:
            ```text
            name  city
            Ravi  Delhi
            Mia   Rome
            ```
        """
    ).strip().splitlines(),
    "paste": dedent(
        """
        - Combine two columns from stdin (default tab delimiter): [Execute](/paste/-/_/printf%20%22first%5Cnsecond%5Cn%22) · [Debug](/paste/-/_/printf%20%22first%5Cnsecond%5Cn%22?debug=true)
          - Bash: `printf "first\nsecond\n" | paste - -`
          - Output:
            ```text
            first<TAB>second
            ```
        - Custom delimiter with `-d ,`: [Execute](/paste/-d%20,%20-/_/printf%20%22apples%5Cnoranges%5Cn%22) · [Debug](/paste/-d%20,%20-/_/printf%20%22apples%5Cnoranges%5Cn%22?debug=true)
          - Bash: `printf "apples\noranges\n" | paste -d , - -`
          - Output:
            ```text
            apples,oranges
            ```
        """
    ).strip().splitlines(),
    "rev": dedent(
        """
        - Reverse text by line (default behavior): [Execute](/rev/_/printf%20%22loop%5Cnstar%5Cn%22) · [Debug](/rev/_/printf%20%22loop%5Cnstar%5Cn%22?debug=true)
          - Bash: `printf "loop\nstar\n" | rev`
          - Output:
            ```text
            pool
            rats
            ```
        """
    ).strip().splitlines(),
    "unexpand": dedent(
        """
        - Convert leading spaces to tabs (default tab stop every 8): [Execute](/unexpand/_/printf%20%22%20%20%20%20%20%20%20%20start%5Cn%20%20%20%20mid%5Cn%22) · [Debug](/unexpand/_/printf%20%22%20%20%20%20%20%20%20%20start%5Cn%20%20%20%20mid%5Cn%22?debug=true)
          - Bash: `printf "        start\n    mid\n" | unexpand`
          - Output:
            ```text
            <TAB>start
            <TAB>mid
            ```
        - Convert all spaces every 4 columns with `-a -t 4`: [Execute](/unexpand/-a%20-t%204/_/printf%20%22word%20%20gap%5Cnwide%20%20%20%20space%5Cn%22) · [Debug](/unexpand/-a%20-t%204/_/printf%20%22word%20%20gap%5Cnwide%20%20%20%20space%5Cn%22?debug=true)
          - Bash: `printf "word  gap\nwide    space\n" | unexpand -a -t 4`
          - Output:
            ```text
            word<TAB>gap
            wide<TAB>space
            ```
        """
    ).strip().splitlines(),
    "uniq": dedent(
        """
        - Default unique filtering (drops repeated neighbors): [Execute](/uniq/_/printf%20%22apple%5Cnapple%5Cnbanana%5Cnbanana%5Cnbanana%5Cn%22) · [Debug](/uniq/_/printf%20%22apple%5Cnapple%5Cnbanana%5Cnbanana%5Cnbanana%5Cn%22?debug=true)
          - Bash: `printf "apple\napple\nbanana\nbanana\nbanana\n" | uniq`
          - Output:
            ```text
            apple
            banana
            ```
        - Count occurrences with `-c`: [Execute](/uniq/-c/_/printf%20%22red%5Cnred%5Cnblue%5Cnblue%5Cnblue%5Cn%22) · [Debug](/uniq/-c/_/printf%20%22red%5Cnred%5Cnblue%5Cnblue%5Cnblue%5Cn%22?debug=true)
          - Bash: `printf "red\nred\nblue\nblue\nblue\n" | uniq -c`
          - Output:
            ```text
                2 red
                3 blue
            ```
        """
    ).strip().splitlines(),
    "wc": dedent(
        """
        - Default counts (lines, words, bytes): [Execute](/wc/_/printf%20%22hello%20world%5Cnsecond%20line%5Cn%22) · [Debug](/wc/_/printf%20%22hello%20world%5Cnsecond%20line%5Cn%22?debug=true)
          - Bash: `printf "hello world\nsecond line\n" | wc`
          - Output:
            ```text
                  2       4      24
            ```
        - Line-only count with `-l`: [Execute](/wc/-l/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cn%22) · [Debug](/wc/-l/_/printf%20%22alpha%5Cnbeta%5Cngamma%5Cn%22?debug=true)
          - Bash: `printf "alpha\nbeta\ngamma\n" | wc -l`
          - Output:
            ```text
            3
            ```
        """
    ).strip().splitlines(),
}


def render_bash_commands_markdown(commands: list[CommandInfo]) -> str:
    """Render the docs/bash_commands.md content."""

    lines: list[str] = [
        "# Bash command servers",
        "",
        "This document lists all bash-based servers, their roles, and quick links to run them. ",
        "Use `_` as a placeholder argument when you want to chain input without passing options to the command.",
        "",
        "## At-a-glance roles",
        "",
        "| Command | Role | Description |",
        "| --- | --- | --- |",
    ]

    for command in commands:
        lines.append(
            f"| `{command.name}` | {command.role} | {command.description} |"
        )

    lines.extend(
        [
            "",
            "## Example 3-command pipeline",
            "",
            "Pipeline URLs execute from right to left. The example below uppercases text using three commands:",
            "",
            "- `echo` provides the input",
            "- `rev` reverses the string",
            "- `tr` translates lowercase to uppercase",
            "",
        ]
    )

    pipeline_path = "/tr/a-z%20A-Z/rev/_/echo/hello"
    lines.append(f"- Pipeline: {_example_links(pipeline_path)}")
    lines.append("")

    lines.append("## Command reference")
    lines.append("")

    for command in commands:
        lines.append(f"### `{command.name}` ({command.role})")
        lines.append("")
        lines.append(command.description)
        lines.append("")
        example_lines = COMMAND_EXAMPLE_OVERRIDES.get(command.name)
        if example_lines:
            lines.extend(example_lines)
        else:
            lines.extend(_example_block(command))
        lines.append("")

    return dedent("\n".join(lines)).strip() + "\n"
