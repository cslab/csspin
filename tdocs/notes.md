# State and Refactoring Needs of the Plugins

This captures the results of an evaluation, whether and which plugins
have to be refactored.

## Java-Stuff

- `java`:
  - works quite well (tm), after looking/trying it superficially
  - provisioning works
- `maven`:
  - works basically, after looking/trying it superficially
- setting the JAVA_HOME and extending PATH could be put into the
  `venv/activate` script. Downside: complexity-increase if we have to
  differentiate between the variants (`python venv is used`
  vs. `python venv is not used`). Question: Is the second case not
  entirely academic?

**Summary**: Kind of okayisch.

## Linters

- `cppcheck` (**removed**):

  - foremost: how to integrate this with pre-commit?
  - dependency on package from ConPI, have to deal with that somehow.

- `cpplint` (**removed**):

  - TODO: test on the platform
  - foremost: same as above: how to integrate this with pre-commit?

- `flake8` (**removed**):

  - determination of the changeset is wrong, when there are deleted files,
    files in the index etc.
  - pre-commit integration

**Summary**:

- [x] first, we have to develop a concept of how to integrate
      the linter plugins with the pre-commit stuff.
- [x] we decided to not maintain linting plugins, workflows or tasks. See
      tdocs/plugin_distribution.md

## Provisioning-heavy stuff

- `node`:
  - provisioning is broken, the model has to be changed
    (issues recorded). This has to be solved first.
- `piptools`:
  - provisioning broken, the model has to be changed
    (issues recorded)
- `python`:
  - also affected by the necessary provisioning reworking
  - :wheel should be subcommand?
  - used heavily

**Summary**: fix provisioning issue first. Then look at the details.

## The Rest

- `portwheel` (**removed**):

  - unused, not important, removed. Can be regained later if necessary.

- `pre-commit` (**removed**):

  - the name is inconsistent with the tool name

- `preflight` (**removed**):

  - obsolete, removed

- `stdworkflows`:

  - incomplete. Defining standard workflows is a work item on its own.

- `pytest`:

  - obsolete, but used for spin. Will be replaced later by `tooling/spin_plugins`

- `radon`:

  - nice small tool. Can stay...

- `scons`:

  - provisioning works
  - where do we want to use it? cs.workspaces? cs.threed? Shouldn't they be
    better migrated cmake?
  - the task cache is obsolete. It only made sense for the 15.x platform.
  - not sure whether this all actually works

- `shell` (**removed**):

  - move to builtin? Its very basic and not tech-stack specific
  - not sure what it should do and whats the difference to env

- `sphinx`:

  - only necessary for the own (spin) documentation, as it seems.
    Degrade to an unshared plugin, unless more use cases are
    detected.

- `vcs`:

  - currently only used by the linters. If we ditch them, this will be
    obsolete.
  - If we dont: the concept of this service should be documented

- `devpi`:

  - incomplete, broken, but probably useful to connect
    to package.contact.de, to fetch the resources from
    16.0-dev etc

- `gitlab-ci`:

  - essentially an empty wrapper, but worth to explore

**Summary**: lots of small reworking necessary, nothing especially troublesome
