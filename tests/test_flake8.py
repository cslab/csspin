from click.testing import CliRunner
from spin.cli import cli
from wheel import pep425tags

def test_flake8():
    runner = CliRunner()
    result = runner.invoke(cli, ["--debug", "flake8", "--exit-zero", "./tests"])
    assert result.exit_code == 0
    assert result.output.startswith("spin")
