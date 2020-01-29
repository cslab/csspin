from click.testing import CliRunner
from spin.cli import cli
from wheel import pep425tags

def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
