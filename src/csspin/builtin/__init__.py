# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2020 CONTACT Software GmbH
# https://www.contact-software.com/
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Plugins that come with spin. These don't have to be installed
through a plugin package and are always available.
"""

import importlib.metadata
import importlib.util
import json
import shlex
import sys
import textwrap
import time
import urllib.request

import click
import distro
from path import Path

from csspin import (
    abspath,
    argument,
    confirm,
    debug,
    die,
    echo,
    exists,
    memoizer,
    mkdir,
    option,
    parse_version,
    readtext,
    rmtree,
    run_script,
    run_spin,
    sh,
    task,
    toporun,
    tree,
    warn,
    writetext,
)
from csspin.cli import (
    APPEND_PROP,
    PREPEND_PROP,
    PROP,
    commands,
    finalize_cfg_tree,
    install_plugin_packages,
    load_plugins_into_tree,
)

CATCHUP_COMMAND = "spin catchup"

# Project-local hook config per agent.
AGENT_HOOK_FILES = {
    "claude": Path(".claude/settings.json"),
    "codex": Path(".codex/hooks.json"),
}


@task("run", add_help_option=False)
def exec_shell(ctx: click.Context, args: list[str]) -> None:
    """Run a shell command in the project context."""
    if not args:
        die("Use of run is not possible without arguments.")
    if "--help" == args[0]:
        subcommand_obj = commands.get_command(ctx, "run")  # type: ignore[attr-defined]
        click.echo(subcommand_obj.get_help(ctx))
    else:
        sh(shlex.join(args), shell=True)


def pretty_descriptor(parent: str, name: str, descriptor, rst: bool) -> str:  # type: ignore[no-untyped-def]
    types = getattr(descriptor, "type", ["any"])
    default = getattr(descriptor, "default", None)
    if name:
        if parent:
            name = f"{parent}.{name}"
        if rst:
            joined_types = " ".join(types)
            decl = f".. py:data:: {name}\n   :type: '{joined_types}'\n"
            if default:
                decl += f"   :value: '{default}'\n"
            if hasattr(descriptor, "noindex") or "object" in types:
                decl += "   :noindex:\n"
        else:
            joined_types = ", ".join(types)
            decl = f"{name}: [{joined_types}]"
            if default:
                decl += f" = '{default}'"
        helptext = getattr(descriptor, "help", "")
        if not helptext.endswith("\n"):
            helptext += "\n"
        decl += f"\n{helptext}\n"
    else:
        decl = "================\nSchema Reference\n================\n\n"
    return decl


@task()
def schemadoc(  # type: ignore[no-untyped-def]
    cfg,
    outfile: option(  # type: ignore[valid-type]
        "-o",
        "outfile",
        default="-",  # noqa: F722
        type=click.File("w"),
        help="Write output into FILENAME.",  # noqa: F722
    ),
    full: option(  # type: ignore[valid-type]
        "--full",
        default=True,
        type=click.BOOL,
        help="Show schema documentation for the whole ConfigTree.",  # noqa: F722
    ),
    rst: option(  # type: ignore[valid-type]
        "--rst",
        is_flag=True,
        default=False,
        help="Print the schema documentation in rst format.",  # noqa: F722
    ),
    select: argument(  # type: ignore[valid-type]
        type=click.STRING,
        default="",  # noqa: F722
        callback=lambda ctx, param, value: value.split(".") if value else "",
    ),
) -> None:
    """Print the schema definitions for spin."""

    def do_docwrite(parent: str, name: str, desc, ignore=tuple()):  # type: ignore[no-untyped-def]
        fullname = f"{parent}.{name}" if parent else name
        if fullname in ignore:
            return

        outfile.write(pretty_descriptor(parent, name, desc, rst))
        properties = getattr(desc, "properties", {})
        for prop, descr in properties.items():
            do_docwrite(fullname, prop, descr, ignore)

    schema = cfg.schema

    ignore = []
    if not full:
        for import_spec in cfg.loaded:
            if "csspin." in import_spec:
                continue
            import_spec = tuple(import_spec.split("."))
            plugin_name = import_spec[-1]
            ignore.append(plugin_name)

    arg = ""
    for arg in select:
        schema = schema.properties.get(arg)
    parent = "" if len(select) < 2 else ".".join(select[:-1])
    do_docwrite(parent, arg, schema, ignore)


class TaskDefinition:
    def __init__(self, definition: dict) -> None:
        self._definition = definition

    def __call__(self) -> None:
        env = self._definition.get("env", None)
        run_spin(self._definition.get("spin", []))
        run_script(self._definition.get("script", []), env)


def configure(cfg) -> None:  # type: ignore[no-untyped-def]
    """
    Grab explicitly defined tasks from the configuration tree and add them as
    subcommands.
    """
    for clause_name in ("extra_tasks", "tasks"):
        for task_name, task_definition in cfg.get(clause_name, {}).items():
            task(task_name, help=task_definition.get("help", ""))(
                TaskDefinition(task_definition)
            )


def merge_dicts(a: dict, b: dict) -> None:
    for k, v in b.items():
        if k in a:
            # We support lists and strings in system_requirements;
            # this is not very robust, though.
            if isinstance(v, list):
                a[k].extend(v)
            else:
                a[k] = " ".join((a[k], v))
        else:
            a[k] = v


def get_distro() -> dict:
    dinfo = distro.info()
    if sys.platform == "win32":
        dinfo["id"] = "windows"
        winver = sys.getwindowsversion()
        dinfo["version"] = f"{winver.major}.{winver.minor}.{winver.build}"
    return dinfo  # type: ignore[no-any-return]


@task("system-provision", noenv=True)
def do_system_provisioning(  # type: ignore[no-untyped-def]
    cfg,
    distroargs: argument(nargs=-1),  # type: ignore[valid-type]
) -> None:
    """Prints system requirements for the host.

    Usage:
        spin system-provision [<distro> [<version>]]

    This will output a script on stdout, that uses OS package managers like apt,
    yum etc. to install system-level dependencies for the project. The output
    can for example be piped into a sudo shell.
    """
    warn(
        "The 'system-provision' subcommand is deprecated and will be removed in"
        " a future release. Please refer to the 'System requirements' section"
        " in csspin's documentation."
    )
    # Install the plugins and build the full config tree
    install_plugin_packages(cfg)
    load_plugins_into_tree(cfg)
    finalize_cfg_tree(cfg)

    if distroargs:
        distroname = distroargs[0]
    else:
        dinfo = get_distro()
        distroname = dinfo["id"]

    # Check system requirements of individual plugins
    out: dict = {}
    supported = True
    for pi in cfg.spin.topo_plugins:
        defaults = cfg.loaded[pi].defaults
        if defaults.get("requires") and defaults.requires.get("system"):
            system_requirements = defaults.requires.system
            if distroname not in system_requirements.keys():
                warn(
                    f"The '{pi}' plugin does not officially support"
                    f" {distroname}. You can see which packages to"
                    " manually install by running 'spin system-provision debian'"
                )
                supported = False
            else:
                merge_dicts(out, system_requirements.get(distroname, []))

    # Check system requirements defined within the configuration tree, usually
    # defined the projects' spinfile.yaml.
    if cfg.system_requirements.keys():
        if distroname not in cfg.system_requirements.keys():
            warn(
                "This project does not officially support"
                f" {distroname}. You can see which packages to manually"
                " install by running 'spin system-provision debian'"
            )
            supported = False
        else:
            merge_dicts(out, cfg.system_requirements.get(distroname, []))

    for line in out.get("before", []):
        print(line)

    for syscmd in ("apt", "choco"):
        if (package_list := out.get(syscmd, [])) and supported:
            print(f"{syscmd} install -y {' '.join(package_list)}")

    for line in out.get("after", []):
        print(line)


@task("distro", noenv=True)
def distro_task(cfg) -> None:  # type: ignore[no-untyped-def]
    """Print the distro information."""
    dinfo = get_distro()
    print(f"distro={repr(dinfo['id'])} version={parse_version(dinfo['version'])}")


def check_for_updates(cfg) -> None:  # type: ignore[no-untyped-def]
    if not cfg.spin.check_for_updates:
        return

    with memoizer(cfg.spin.data / "csspin_update_check.memo") as m:
        current_time = time.time()
        timestamps = m.items()
        last_checked = timestamps[-1] if timestamps else 0
        if current_time - last_checked < cfg.spin.version_check_ttl:
            return

        headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
        try:
            request = urllib.request.Request(
                "https://pypi.org/simple/csspin/", headers=headers
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                latest_version = json.loads(response.read())["versions"][-1]
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
        ) as exc:
            debug(f"Could not check for a new csspin version: {exc}")
            return
        m.clear()
        m.add(current_time)

    current_version = importlib.metadata.version("csspin")

    if parse_version(latest_version) > parse_version(current_version):
        warn(
            "A new release of csspin is available:",
            f"{click.style(current_version, fg='red')} ->"
            f" {click.style(latest_version, fg='green')}",
        )
        warn("Consider updating to the latest version.")


@task("provision", noenv=True)
def provision(cfg) -> None:  # type: ignore[no-untyped-def]
    """
    Create or update a development environment.
    """
    # Install the plugins and build the full config tree
    install_plugin_packages(cfg)
    load_plugins_into_tree(cfg)
    finalize_cfg_tree(cfg)

    toporun(cfg, "provision")
    toporun(cfg, "finalize_provision")

    check_for_updates(cfg)


@task(noenv=True, short_help="Clean up project-local resources.")
def cleanup(  # type: ignore[no-untyped-def]
    cfg,
    purge: option(  # type: ignore[valid-type]
        "--purge",
        is_flag=True,
        help="Removes spin plugin data.",  # noqa: F722
    ),
    skip_confirmation: option(  # type: ignore[valid-type]
        "-y",
        "--yes",
        "skip_confirmation",
        is_flag=True,
        help="Skip confirmation when using --purge.",  # noqa: F722
    ),
) -> None:
    """
    Clean up project-local resources that have been provisioned by spin, e.g.
    virtual environments and {project_root}/.spin. Also deletes {spin.data}
    if --purge is passed.
    """
    # Load the plugins as far as they are available.
    load_plugins_into_tree(cfg, cleanup=True)
    # Can't use finalize_cfg_tree here, because it would execute all plugins configure hooks,
    # which might not be available during cleanup
    tree.tree_update_properties(  # pylint: disable=duplicate-code
        cfg,
        PROP,
        PREPEND_PROP,
        APPEND_PROP,
    )

    cfg.spin.data = abspath(cfg.spin.data)

    if (
        purge
        and not skip_confirmation
        and not (
            confirm(
                f"You are about to delete all plugin's data in {cfg.spin.data}."
                " Continue?"
            )
        )
    ):
        return

    # Do not configure and sanitize in case of cleanup, since plugin
    # packages may not be installed, causing AttributeErrors in case of
    # accessing not-initialized plugins via "cfg." as well as failures due
    # to interpolation against property tree keys that does not exist.

    toporun(cfg, "cleanup", reverse=True)
    rmtree(cfg.spin.spin_dir / "plugins")

    if purge:
        rmtree(cfg.spin.data)


def _build_catchup_briefing(cfg) -> str:  # type: ignore[no-untyped-def]
    """Assemble the markdown briefing printed by 'spin catchup'."""
    spec = importlib.util.find_spec("csspin")
    install_location = spec.submodule_search_locations[0]  # type: ignore[union-attr,index]

    return textwrap.dedent(f"""\
        # {cfg.spin.project_name} uses spin

        spin (csspin) is a pluggable task runner: it provisions the tools this
        project needs into `{cfg.spin.spin_dir}`, and turns every task and
        workflow its plugins define into a `spin <task>` command. Everything
        below reflects what spin (version {cfg.spin.version}) knows about this
        project's `{cfg.spin.spinfile.name}` right now. Some projects keep more
        than one spinfile (selected via `spin -f <name>`). If so, this briefing
        is specific to `{cfg.spin.spinfile.name}` alone, so check for others
        before assuming it's the only one. To get the briefing for another
        spinfile, run `spin -f <name> catchup`.

        If `{cfg.spin.spin_dir}` does not exist yet, run `spin provision` first.
        Plugin tasks (e.g. `spin pytest`) only exist once the project is
        provisioned.

        ## How spin fits together

        `{cfg.spin.spinfile.name}` is the source of truth for what gets
        installed and how tasks behave. Editing it changes nothing until `spin
        provision` runs again. Provisioning also installs and configures
        whatever plugins the file lists (e.g. a Python or Node toolchain, test
        runners), each contributing its own tasks and configuration section.

        `{cfg.spin.spin_dir}` holds everything spin manages for this project:
        plugin packages, managed tool installs, virtual environments. spin
        populates it (`spin provision`) and tears it down (`spin cleanup`).
        Manual edits or installs there tend to produce a broken state that
        neither command will detect or fix.

        Run tools through spin: `spin <task>` for whatever the project defines
        (e.g. `spin pytest`, `spin build`), or `spin run <exe>` for a one-off
        command that should still execute inside spin's managed environment
        (e.g. `spin run python -m pip list`). A tool called by its bare name
        (e.g. python, or pytest ) outside of spin may resolve to a different,
        unmanaged copy, if one happens to be on `PATH` at all.

        `spin --help` only lists the tasks available right now. After editing
        `{cfg.spin.spinfile.name}` and reprovisioning, run `spin --help` again
        to see what's new.

        ## Finding specifics

        - `spin <task> --help`: options and defaults for one task, e.g. `spin
          pytest --help`.
        - `spin schemadoc [<path>]`: documents csspin's configuration tree
          (every property the schema defines, not only the ones set in
          `{cfg.spin.spinfile.name}`), e.g. `spin schemadoc python.version`.
        - `spin --dump`: the fully interpreted configuration in effect. This can
          be large, so pipe it through `grep <property>` for a specific value
          instead of reading all of it.
        - `{cfg.spin.spin_dir}/plugins`: where installed plugin packages live.
        - {install_location}: where spin's own sources are installed, for
          inspecting how the plugin/task system works directly.
        """)


def _install_catchup_hook(cfg, agent: str) -> None:  # type: ignore[no-untyped-def]
    """
    Add a SessionStart hook running 'spin catchup' to the agent's project
    config. Creates the config file if it is missing.
    """
    target = cfg.spin.spinfile.absolute().parent / AGENT_HOOK_FILES[agent]
    settings = {}
    try:
        if exists(target):
            settings = json.loads(readtext(target))
        groups = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
        already_installed = any(
            handler.get("command") == CATCHUP_COMMAND
            for group in groups
            for handler in group.get("hooks", [])
        )
    except (json.JSONDecodeError, AttributeError, TypeError) as ex:
        die(
            f"{target} is not a valid hook config, not touching it: {ex}", resolve=False
        )

    if already_installed:
        echo(f"{target} already runs '{CATCHUP_COMMAND}' on session start.")
    else:
        groups.append(
            {
                "matcher": "startup|resume|clear|compact",
                "hooks": [{"type": "command", "command": CATCHUP_COMMAND}],
            }
        )
        mkdir(target.parent)
        writetext(target, json.dumps(settings, indent=4) + "\n")
        echo(f"Added a SessionStart hook running '{CATCHUP_COMMAND}' to {target}.")

    if agent == "codex":
        warn(
            "Codex only runs project hooks once the project's .codex/ layer is"
            " trusted and the hook is reviewed. Run '/hooks' in Codex to trust it."
        )


@task("catchup", noenv=True)
def catchup(  # type: ignore[no-untyped-def]
    cfg,
    install: option(  # type: ignore[valid-type]
        "--install",
        type=click.Choice(sorted(AGENT_HOOK_FILES)),
        help="Add a session start hook running 'spin catchup' to the"  # noqa: F722
        " project's config for the given agent.",
    ),
) -> None:
    """
    Print a briefing for agentic coding tools about this project's spin setup.
    """
    if install:
        _install_catchup_hook(cfg, install)
        return

    print(_build_catchup_briefing(cfg))
