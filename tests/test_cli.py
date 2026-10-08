# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Module implementing the unit tests regarding the cli.py module of spin"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path as PathlibPath
from shutil import copy, which
from typing import TYPE_CHECKING, Callable, Generator

import click
import pytest
from conftest import chdir
from path import Path

from csspin import cli, memoizer
from csspin.tree import ConfigTree

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock.plugin import MockerFixture
    from pytest import MonkeyPatch

from subprocess import check_output
from subprocess import run as subprocess_run

from csspin import Verbosity


def test_cli(cli_runner: CliRunner) -> None:
    """csspin.cli can be invoked using click"""
    result = cli_runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0


def test_secret_obfuscation(
    cli_runner: CliRunner,
    tmp_path: PathlibPath,
) -> None:
    """Test whether secrets containing interpolatable elements are hidden.
    This test also applies to secrets that do not require interpolation."""
    interpolated_secret = "pupa228lup__hey__a1337hehehoho"
    secret_from_configure = "sssssshhhitsasecret"
    args = ["--env", tmp_path, "-f", "tests/schema/test_schema_secrets.yaml", "-vv"]

    cli_runner.invoke(cli.cli, [*args, "provision"])
    res = cli_runner.invoke(cli.cli, [*args, "output-secrets"], input="y")
    assert interpolated_secret not in res.output
    assert secret_from_configure not in res.output

    res = cli_runner.invoke(cli.cli, [*args, "--dump"])
    assert interpolated_secret not in res.output
    assert secret_from_configure not in res.output


def test_cleanup(
    cli_runner: CliRunner,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: PathlibPath,
) -> None:
    (tmp_spin_data := tmp_path / "tmp_spin_data").mkdir()
    (tmp_spin_dir := tmp_path / ".spin").mkdir()
    (tmp_spin_plugins := tmp_spin_dir / "plugins").mkdir()
    (tmp_plugin := tmp_spin_plugins / "tmp_plugin").mkdir()

    monkeypatch.setenv("SPIN_DATA", tmp_spin_data)
    mocker.patch("csspin.builtin.toporun", return_value=None)

    cli_runner.invoke(cli.cli, ["--env", tmp_path, "cleanup", "--purge", "-y"])

    assert not tmp_spin_data.exists()
    assert not tmp_plugin.exists()

    tmp_spin_data.mkdir()
    monkeypatch.delenv("SPIN_DATA", raising=False)
    monkeypatch.setenv("SPIN_TREE_SPIN__DATA", tmp_spin_data)

    cli_runner.invoke(cli.cli, ["--env", tmp_path, "cleanup", "--purge", "-y"])

    assert not tmp_spin_data.exists()

    monkeypatch.delenv("SPIN_TREE_SPIN__DATA", raising=False)
    tmp_spin_data.mkdir()

    cli_runner.invoke(
        cli.cli,
        [
            "--env",
            tmp_path,
            "-p",
            f"spin.data={tmp_spin_data}",
            "cleanup",
            "--purge",
            "-y",
        ],
    )

    assert not tmp_spin_data.exists()


def write_minimal_spinfile(project_dir: PathlibPath, project_name: str) -> None:
    """Write a plugin-free spinfile.yaml so catchup stays hermetic."""
    (project_dir / "spinfile.yaml").write_text(
        f"spin:\n  project_name: {project_name}\n"
    )


def count_catchup_hooks(settings: dict) -> int:
    """Count the SessionStart handlers that run 'spin catchup'."""
    return sum(
        handler["command"] == "spin catchup"
        for group in settings["hooks"]["SessionStart"]
        for handler in group["hooks"]
    )


class TestCatchup:
    """Tests for the 'spin catchup' builtin task."""

    def test_briefing(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
    ) -> None:
        """catchup prints the briefing even though nothing is provisioned."""
        write_minimal_spinfile(tmp_path, "catchup-test")

        with chdir(tmp_path):
            result = cli_runner.invoke(cli.cli, ["catchup"])

        assert result.exit_code == 0
        assert "catchup-test" in result.output

    @pytest.mark.parametrize(
        "agent, target",
        [
            ("claude", ".claude/settings.json"),
            ("codex", ".codex/hooks.json"),
        ],
    )
    def test_install_creates_hook_config(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
        agent: str,
        target: str,
    ) -> None:
        """--install=<agent> creates the missing config with a SessionStart hook."""
        write_minimal_spinfile(tmp_path, "catchup-test")

        with chdir(tmp_path):
            result = cli_runner.invoke(cli.cli, ["catchup", f"--install={agent}"])

        assert result.exit_code == 0
        assert count_catchup_hooks(json.loads((tmp_path / target).read_text())) == 1
        if agent == "codex":
            assert "/hooks" in result.output

    def test_install_targets_spinfile_directory(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
    ) -> None:
        """The hook lands next to the spinfile, not in the current directory."""
        write_minimal_spinfile(tmp_path, "catchup-test")
        subdir = tmp_path / "sub"
        subdir.mkdir()

        spinfile = tmp_path / "spinfile.yaml"

        with chdir(tmp_path):
            result = cli_runner.invoke(
                cli.cli,
                ["-C", str(subdir), "-f", str(spinfile), "catchup", "--install=claude"],
            )

        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "settings.json").exists()
        assert not (subdir / ".claude").exists()

    def test_install_preserves_existing_settings(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
    ) -> None:
        """Unrelated settings and other hooks survive the merge."""
        write_minimal_spinfile(tmp_path, "catchup-test")
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.parent.mkdir()
        settings_file.write_text(
            json.dumps(
                {
                    "permissions": {"allow": ["Bash(ls:*)"]},
                    "hooks": {
                        "SessionStart": [
                            {"hooks": [{"type": "command", "command": "echo hi"}]}
                        ],
                        "Stop": [{"hooks": [{"type": "command", "command": "x"}]}],
                    },
                }
            )
        )

        with chdir(tmp_path):
            result = cli_runner.invoke(cli.cli, ["catchup", "--install=claude"])

        assert result.exit_code == 0
        settings = json.loads(settings_file.read_text())
        assert settings["permissions"] == {"allow": ["Bash(ls:*)"]}
        assert "Stop" in settings["hooks"]
        assert len(settings["hooks"]["SessionStart"]) == 2
        assert count_catchup_hooks(settings) == 1

    def test_install_is_idempotent(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
    ) -> None:
        """Running --install twice does not add a second hook."""
        write_minimal_spinfile(tmp_path, "catchup-test")

        with chdir(tmp_path):
            cli_runner.invoke(cli.cli, ["catchup", "--install=claude"])
            result = cli_runner.invoke(cli.cli, ["catchup", "--install=claude"])

        assert result.exit_code == 0
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert count_catchup_hooks(settings) == 1

    def test_install_rejects_invalid_json(
        self,
        cli_runner: CliRunner,
        tmp_path: PathlibPath,
    ) -> None:
        """A broken config is reported and left untouched."""
        write_minimal_spinfile(tmp_path, "catchup-test")
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.parent.mkdir()
        settings_file.write_text("{not json")

        with chdir(tmp_path):
            result = cli_runner.invoke(cli.cli, ["catchup", "--install=claude"])

        assert result.exit_code != 0
        assert settings_file.read_text() == "{not json"


def test_find_spinfile(tmp_path: PathlibPath) -> None:
    """
    csspin.cli.find_spinfile is able to find the passed spinfile and returning
    None if not and the default location if None was passed
    """
    spinfile = os.path.normpath(f"{tmp_path}/spinfile.yaml")
    with open(spinfile, "w", encoding="utf-8") as f:
        f.write("")

    insidetree = f"{tmp_path}/a/b/c"
    os.makedirs(insidetree)
    with chdir(insidetree):
        assert cli.find_spinfile("spinfile.yaml") == spinfile
        assert cli.find_spinfile("SPIN_TEST_CLI_DOESNOTEXIST") is None
        assert cli.find_spinfile(spinfile=None) == spinfile


def test_find_spinfile_failing(
    tmp_path: PathlibPath,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    csspin.cli.find_spinfile raises an exception if no spinfile could be found
    """
    from subprocess import PIPE

    # help case
    result = subprocess_run(
        ["spin", "-C", str(tmp_path), "--help"],
        text=True,
        stdout=PIPE,
        stderr=PIPE,
        check=False,
    )
    assert "spin: warning: No configuration file found" in result.stderr

    # no local spinfile found + passed spinfile not found
    result = subprocess_run(
        ["spin", "-C", str(tmp_path), "-f", "spinfile.yaml", "provision"],
        text=True,
        stdout=PIPE,
        stderr=PIPE,
        check=False,
    )
    assert "spin: error: spinfile.yaml not found" in result.stderr

    # not help and no spinfile found nor passed
    result = subprocess_run(
        ["spin", "-C", str(tmp_path), "provision"],
        text=True,
        stdout=PIPE,
        stderr=PIPE,
        check=False,
    )
    assert "spin: error: No configuration file found" in result.stderr


def test_load_plugin(
    cfg_spin_dummy: ConfigTree,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    csspin.cli.load_plugin loads valid plugins into the tree if they're not
    already present
    """
    # TODO: Test to add a package that ships unloaded requirements.

    from types import ModuleType

    cfg_spin_dummy.verbosity = Verbosity.DEBUG

    # load plugin that is already present in the tree
    plugin = cli.load_plugin(cfg_spin_dummy, "csspin.builtin")
    captured = capsys.readouterr()

    assert isinstance(plugin, ModuleType)
    assert "import plugin csspin.builtin" in captured.out
    assert "add subtree" not in captured.out

    # load plugin that is not present in the tree
    assert not cfg_spin_dummy.loaded.get("csspin_dummy.dummy")
    cli.load_plugins_into_tree(cfg=cfg_spin_dummy)
    captured = capsys.readouterr()

    assert "import plugin csspin_dummy.dummy" in captured.out
    assert cfg_spin_dummy.loaded.get("csspin_dummy.dummy")

    # load plugin that does not exist
    with pytest.raises(
        ModuleNotFoundError,
        match="Plugin foo could not be loaded, it may need to be provisioned",
    ):
        cli.load_plugin(cfg_spin_dummy, import_spec="foo")


def test_reverse_toposort(cfg: ConfigTree) -> None:
    """
    csspin.cli.reverse_toposort returns a list containing the passed 'nodes' in
    the expected order while failing when passing cycles
    """
    graph = {
        "csspin.builtin": ["csspin.builtin.shell"],
        "csspin.builtin.shell": ["csspin.builtin.data"],
        "csspin.builtin.data": [],
    }
    result = cli.reverse_toposort(nodes=graph.keys(), graph=graph)

    # Ensure that the origin graph is not modified by calling reverse_toposort.
    assert graph == {
        "csspin.builtin": ["csspin.builtin.shell"],
        "csspin.builtin.shell": ["csspin.builtin.data"],
        "csspin.builtin.data": [],
    }

    assert result == [
        "csspin.builtin.data",
        "csspin.builtin.shell",
        "csspin.builtin",
    ]

    graph = {"foo": ["bar"], "bar": ["foo"]}
    with pytest.raises(click.Abort, match="dependency graph has at least one cycle"):
        cli.reverse_toposort(nodes=graph.keys(), graph=graph)


def test_base_options() -> None:
    """csspin.cli.base_options can be used to equip functions with defined"""

    def command() -> None:
        return "hello earth"

    decorated_command = cli.base_options(command)
    assert isinstance(decorated_command, Callable)
    assert vars(decorated_command).get("__click_params__")
    assert command() == "hello earth"  # check if command is still callable


def test_group_with_aliases() -> None:
    """
    csspin.cli.GroupWithAliases is able to assign new command aliases and return
    existing ones
    """
    grouper = cli.GroupWithAliases()
    assert not grouper._aliases  # pylint: disable=protected-access

    def command() -> None:
        pass

    cmd = click.command(command)
    grouper.register_alias(alias="foo", cmd_object=cmd)
    assert grouper._aliases == {"foo": cmd}  # pylint: disable=protected-access

    with click.Context(cmd) as ctx:
        assert grouper.get_command(ctx=ctx, cmd_name="foo") is cmd


def test_find_plugin_packages(cfg: ConfigTree) -> None:
    """
    csspin.cli.find_plugin_packages returns a generator which items are the
    expected 'plugin_packages' of the passed configuration tree
    """
    result = cli.find_plugin_packages(cfg)
    assert isinstance(result, Generator)
    assert not list(result), "Result should not have length > 0"

    packages = ["flake8", "pytest"]
    cfg["plugin_packages"] = packages
    assert list(cli.find_plugin_packages(cfg)) == packages


def test_yield_plugin_import_specs(cfg: ConfigTree) -> None:
    """csspin.cli.yield_plugin_import_specs returns the expected plugins"""
    result = cli.yield_plugin_import_specs(cfg)

    assert isinstance(result, Generator)
    assert not list(result), "Result should not have length > 0"

    cfg["plugins"] = ["foo"]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo"]

    cfg["plugins"] = [{"foo": ["bar", "baz"]}]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo.bar", "foo.baz"]

    cfg["plugins"] = [{"foo": ["bar", "baz"]}, "buz"]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo.bar", "foo.baz", "buz"]


def test_load_config_tree_basic(
    tmp_path: PathlibPath,
    minimum_yaml_path: str,
) -> None:
    """
    csspin.cli.load_config_tree returns a valid configuration tree with all
    expected attributes set (Verbosity.NORMAL)
    """

    with chdir(tmp_path):
        spinfile = tmp_path / "spinfile.yaml"
        copy(minimum_yaml_path, spinfile)

        cfg = cli.load_minimal_tree(spinfile=spinfile, envbase=tmp_path)

        assert cfg.spin.spinfile == spinfile
        assert cfg.spin.project_root == spinfile.dirname()
        assert cfg.spin.project_name == tmp_path.basename()
        assert cfg.spin.spin_dir == tmp_path / ".spin"

        assert (tmp_path / ".spin" / ".gitignore").is_file()
        with open(tmp_path / ".spin" / ".gitignore", "r", encoding="utf-8") as f:
            assert f.read() == "# Created by spin automatically\n*\n"

        assert isinstance(cfg.loaded, ConfigTree)
        assert cfg.loaded.get("csspin.builtin")
        assert len(cfg.loaded) == 1  # no other/global plugins loaded
        assert cfg.plugin_paths == []


def test_load_plugins_into_tree(
    mocker: MockerFixture,
    tmp_path: PathlibPath,
    minimum_yaml_path: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    csspin.cli.load_config_tree returns a valid configuration tree with all
    expected attributes set (quiet + provision)
    """
    mock_echo = mocker.patch("csspin.echo")
    with chdir(tmp_path):
        spinfile = tmp_path / "spinfile.yaml"
        copy(minimum_yaml_path, spinfile)

        cfg = cli.load_minimal_tree(
            spinfile=spinfile,
            cwd=tmp_path,
            envbase=tmp_path,
            verbosity=Verbosity.DEBUG,
        )
        cli.load_plugins_into_tree(cfg)
        captured = capsys.readouterr()

        assert cfg.foo == "bar"
        assert cfg.spin.project_root == spinfile.dirname()
        assert cfg.spin.project_name == tmp_path.basename()
        assert cfg.spin.spin_dir == tmp_path / ".spin"
        assert cfg.spin.spin_dir / "plugins" in sys.path

        assert os.path.isfile(tmp_path / ".spin" / ".gitignore")
        with open(tmp_path / ".spin" / ".gitignore", "r", encoding="utf-8") as f:
            assert f.read() == "# Created by spin automatically\n*\n"
        mock_echo.assert_called_with("mkdir -p", tmp_path.absolute() / ".spin")

        assert isinstance(cfg.loaded, ConfigTree)
        assert cfg.loaded.get("csspin.builtin")
        assert len(cfg.loaded) == 1  # no other/global plugins loaded
        assert cfg.plugin_paths == []
        assert "loading project plugins:" in captured.out
        assert "  import plugin csspin.builtin" in captured.out
        assert "  add subtree builtin" in captured.out


def test_plugin_directives(
    monkeypatch: MonkeyPatch,
    dummy_yaml_path: str,
    spin_config_patch: str,
):
    monkeypatch.setenv("SPIN_CONFIG", spin_config_patch)
    monkeypatch.setenv("SPIN_DISABLE_GLOBAL_YAML", "")

    cfg = cli.load_minimal_tree(
        spinfile=dummy_yaml_path,
        cwd=os.getcwd(),
        verbosity=Verbosity.DEBUG,
    )
    cli.load_plugins_into_tree(cfg)

    assert "csspin-python" in cfg.plugin_packages
    assert cfg.loaded.get("csspin_dummy.dummy")
    assert cfg.loaded.get("csspin_dummy.dummy2")


def test_install_plugin_packages(
    mocker: MockerFixture,
    cfg: ConfigTree,
    tmp_path: PathlibPath,
    trivial_plugin_path: Path,
) -> None:
    """
    csspin.cli.install_plugin_packages executes is able to install plugin packages
    """
    cfg.spin.spin_dir = tmp_path
    plugin_dir = cfg.spin.spin_dir / "plugins"
    mocker.patch(
        "csspin.cli.find_plugin_packages", return_value=(str(trivial_plugin_path),)
    )
    cli.install_plugin_packages(cfg)

    assert (plugin_dir / "trivial-1.0.0.dist-info").is_dir()
    assert (plugin_dir / "packages.memo").is_file()
    with memoizer(plugin_dir / "packages.memo") as m:
        assert m.check(trivial_plugin_path)


def test_spin_version() -> None:
    """Ensuring that spin --version prints the correct version of spin"""
    import importlib.metadata as importlib_metadata

    expected_version = importlib_metadata.version("csspin")
    output = check_output(["spin", "--version"], text=True)
    assert expected_version in output


def _shell_complete(
    comp_words: str, comp_cword: int, cwd: PathlibPath | None = None
) -> set[str]:
    """Helper method for spin shell complete tests"""
    env = {
        **os.environ,
        "_SPIN_COMPLETE": "bash_complete",
        "COMP_WORDS": comp_words,
        "COMP_CWORD": str(comp_cword),
    }
    output = check_output(["spin"], env=env, cwd=cwd, text=True)
    return {line.split(",", 1)[1] for line in output.splitlines() if line}


@pytest.mark.parametrize(
    "comp_words,comp_cword,expected",
    [
        ("spin provi", 1, {"provision"}),
        ("spin sbom", 2, {"assemble", "build", "enrich", "quality"}),
        ("spin prov", 2, set()),
        ("spin --", 1, {"--generate-shell-completion", "--verbose", "--version"}),
    ],
    ids=["command", "subcommand", "incomplete", "all-options"],
)
def test_spin_shell_complete(
    comp_words: str, comp_cword: int, expected: set[str]
) -> None:
    """Ensuring that spin shell completion suggests commands and subcommands"""
    assert expected <= _shell_complete(comp_words, comp_cword)


def test_spin_shell_complete_missing_spinfile(tmp_path: PathlibPath) -> None:
    """Check if autcomplete suggests top-level options without a spinfile"""
    assert "--version" in _shell_complete("spin -f no_spinfile.yaml --ver", 3)
    assert _shell_complete("spin -f no_spinfile.yaml provi", 3) == set()


# Real shell command completion for command line in $TEST_SPIN_COMPLETE_LINE.
_SHELL_DRIVERS = {
    "bash": [
        "bash",
        "--norc",
        "--noprofile",
        "-c",
        textwrap.dedent("""
            source <(spin --generate-shell-completion bash)
            COMP_WORDS=($TEST_SPIN_COMPLETE_LINE); [[ $TEST_SPIN_COMPLETE_LINE == *" " ]] && COMP_WORDS+=("")
            COMP_CWORD=$((${#COMP_WORDS[@]} -1))
            _spin_completion spin
            printf "%s\\n" "${COMPREPLY[@]}"
        """),
    ],
    "zsh": [
        "zsh",
        "-f",
        "-c",
        textwrap.dedent("""
            compdef() { :; }
            compadd() { print -rl -- "${(@P)${@[-1]}}"; }
            _describe() { local c; for c in ${(@P)3}; do print -r -- "${c%%:*}"; done; }
            source <(spin --generate-shell-completion zsh)
            words=("${(@s: :)TEST_SPIN_COMPLETE_LINE}"); CURRENT=${#words}
            _spin_completion
        """),
    ],
    "fish": [
        "fish",
        "--no-config",
        "-c",
        textwrap.dedent("""
            spin --generate-shell-completion fish | source
            complete -C "$TEST_SPIN_COMPLETE_LINE" | string split -f1 \\t; or true
        """),
    ],
    "powershell": [
        "pwsh",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        textwrap.dedent("""
            . ([scriptblock]::Create((spin --generate-shell-completion powershell) -join "`n"))
            $line = $env:TEST_SPIN_COMPLETE_LINE
            $result = TabExpansion2 -inputScript $line -cursorColumn $line.Length
            $result.CompletionMatches.CompletionText
        """),
    ],
}


@pytest.mark.parametrize("shell", _SHELL_DRIVERS)
@pytest.mark.parametrize(
    "line,expected",
    [
        ("spin provi", {"provision"}),
        ("spin sbom ", {"assemble", "build", "enrich", "quality"}),
        ("spin --ver", {"--verbose", "--version"}),
        ("spin --", {"--generate-shell-completion", "--verbose", "--version"}),
        ("spin -", {"-C", "-q", "-v", "--dump"}),
        ("spin loremipsum", set()),
    ],
    ids=[
        "command",
        "subcommand",
        "option",
        "all-options",
        "single-dash",
        "unknown-command",
    ],
)
def test_spin_shell_complete_e2e(shell: str, line: str, expected: set[str]) -> None:
    """Ensuring that the generated completion script works in each shell"""
    driver = _SHELL_DRIVERS[shell]
    if sys.platform == "win32" and shell != "powershell":
        pytest.skip(f"{shell} can't reach the venv's spin on Windows")
    if not which(driver[0]):
        pytest.skip(f"{driver[0]} is not installed")

    env = {
        **os.environ,
        "PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"],
        "TEST_SPIN_COMPLETE_LINE": line,
    }
    output = check_output(driver, env=env, text=True)
    assert expected <= set(output.splitlines())
