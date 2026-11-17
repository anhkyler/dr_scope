import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hello import main  # noqa: E402


def test_hello_prints(capsys):
    main()
    assert "Hello World" in capsys.readouterr().out
