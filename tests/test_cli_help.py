from cli import print_help


def test_print_help_includes_debug_flag(capsys):
    print_help()
    captured = capsys.readouterr()
    assert "--debug" in captured.out
