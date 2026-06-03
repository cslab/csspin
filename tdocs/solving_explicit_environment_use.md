# Ensuring explicit and intentional environment use aka "Operation Wuseldusel"

Assumption: One `spinfile.yaml` results in a _single_ environment.

## Definitions

Environments:

- spin-environment aka "in-process environment"
  - Plugins (plugin code) run in this environment
  - `run` runs in here if csspin-python is not present

- `csspin-python.python` environment (which updates the spin environment) aka
  "subprocess environment"
  - `spin.sh` runs in here
  - `run` runs in here if csspin-python is present
  - `extra_tasks` should run in here since init hooks have been executed before
    `script` and `spin` is executed

Project Context: Subprocess environment

## Problem

- `run` and `extra_tasks` must run in the subprocess environment this is
  currently done implicitly via `spin.sh` and the `init`-hook of
  `csspin-python.python`

## Requirements

- The environment that `spin run` and `extra_tasks[*].script` runs in must be
  provided by `spin.subprocess_environment` to keep the current implicit default
  behavior.

## Ideas

1. csspin-python sets `spin.subprocess_environment = "<func that does the job,
e.g. csspin.python.python::doit>"`; its default is `None` or `NullContext`.
   This callable might be a context manager.
2. This callable is then used by `spin.sh` to use the desired environment.
3. `spin.sh` will be giftet a new parameter that prevents this behavior. So the
   subprocess environment is only used when needed.
