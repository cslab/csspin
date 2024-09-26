# Contains Miscellaneous Spin-Related Technical Decisions

## 1. Data Normalization / Sanity-Checks

Data normalization/sanitizing belongs close to the input channels
and should _not_ -- quite obviously -- be scattered across the
whole code. What are our input channels?

- projects `spinfile.yaml`
- users `global.yaml`
- Command line property parameters via CL (`-p <prop>`)
- `SPIN_ENV_PROP_bla` environment variables (in the future, probably)

For these "channels", we:

- Implement sanity checks in the descriptor classes in
  `schema.py`. These know the data type and ensure that an integer
  value has been passed for a property with the type int etc. The
  paths have to be normalized here.

- Note:

  1.  Property trees may contain callables. This is currently the case
      e.g. for the mkinstance plugin. These are to be evaluated in the configure-hook,
      which leads to better DevEx as we see the resulting values in
      `spin debug`.
  2.  The tree may contain objects of type "internal": those are
      undocumented, used by the implementation and have to ignored
      in this context. If general, such usages should be avoided:
      for passing around an object in the same module a global
      object should be in in most cases the better choice.

To further ease the usage of the property tree,

Another "input channel" are environment-vars and the CLI arguments, which
we read the code, both in the core and in the plugins. In this
situation, the respective code is then responsible for the sanity
checks / normalization etc.

The plugins can of course also have any other input sources. Here applies
the same logic as above: the plugins are responsible for the necessary
normalization/sanitizing of the inputs.

## 2. Which string interpolation to use in which situations?

- Situation 1:

  ```
  def bla(cfg, ...):
      info("lala {python.interpreter}")
  ```

  - more complex than the f-string interpolation
  - needs spin knowledge
  - can handle nested interpolation

  Alternatively, in the variant below:

  ```
  def bla(cfg, ...):
      info(f"lala {cfg.python.interpreter}")
  ```

  - the f-string are simpler and commonly known
  - doesn't avoid the call of `interpolation` though
  - can handle nested interpolation due to the mentions interpolation call

- Situation 2:

  ```
  def blub(...):
      info("lala {python.interpreter}")
  ```

  Here, we have no other choice, as we don't have the access to the
  ConfigTree-object

## 3. Whats the value of having Path-objects in the ConfigTree-object instead of strings, anyway?

We could use the type knowledge from the schemas to do the input
validation and path normalizing but put resulting strings into the
tree in the end. All other things being equal, this would be the
better choice, because of lower complexity.

Things aren't equal though; we have the benefit of directly using the
Path-Methods like:

```
cfg.spin.cache / dir / file
```

instead of

```
Path(cfg.python.cache) / dir / file
```

That isn't a big benefit however; and we might revise this decision on
further findings.

## 4. On removing linting plugins

Originally, we planned the linting plugins (flake8, pylint, ...) not
only to wrap the linters but also to ship the standard configuration for
those, and to reuse them from the IDEs etc. Shipping the linters
configurations would then reduce the boilerplate, make sure everybody
uses they same configuration settings etc.

This doesn't feel right anymore for multiple reasons.

There are at least two major context for linting: pre-commit and
IDEs. Both are widely adopted @C. In both 'the setup' is expected to
be standard and the configuration be in standard locations. We could
try to bend things for both cases, but it doesn't feel very smart;
rather, it feels like swimming against the flow.

Which would leave the possibility to provision the configuration files into
those standard locations, or to modify setup.cfg/pyproject.toml.
Which is also weird, and would stand in the way of component-
specific changes etc. So no happy end here, too.

Calling pre-commit from spin or vice versa doesn't feel good either.

At the end, we probably will leave all those contexts and
implementations -- i.e. pre-commit, IDE-addons, spin -- separate, let
them call the tools independently, and make sure to push the relevant
configuration into setup.cfg/pyproject.toml to behave them the same in
all contexts.

Or not; we'll see. To bother moving them around we'll remove them for now
and re-add later if necessary.

## 5. The Environment as Input Channel for cs.spin

> Draft and ideas; mostly copied from docs/userman.rst

cs.spin provides a command-line interface as documented in
`docs/cliref.rst`. Besides that, passing options to spin, called
tasks/plugins as well as modifying the configuration tree via the environment is
a crucial feature which is implemented using different approaches:

- **`SPIN_`-prefix**:
  - Used to modify the options directly passed to cs.spin itself.
  - Utilizes click's `auto_envvar_prefix` feature, which allows integration
    and adjustment of cs.spin's command-line interface (CLI) options via
    environment variables.
  - Is subject of the natural limitation of assigning values to a property,
    which could be assigned by multiple values at once, i.e., `SPIN_P` can
    only used once: `SPIN_P="pytest.opts=-vv"`.
- **`SPIN_TREE_`-prefix**
  - Dedicated to defining and modifying configuration tree entries via
    environment variables (i.e. affecting how tasks calling tools). This method
    mirrors the effect of passing configuration parameters using the `-p`
    option directly via CLI.
  - Accessing nested elements, e.g. `pytest.opts` is possible via double
    underscores: `SPIN_TREE_PYTEST__OPTS="[-m, not slow]"`.
  - Limitations are given by the circumstance that due to accessing nested
    properties via double underscore, configuration tree keys, that begin or end
    with single or multiple underscores as well as those that include multiple
    underscores in order can't be modified like this. Same counts for keys that
    can't be represented as environment variable.
- **`SPIN_<plugin-name>_`-prefix** (idea):
  - Similar to the `SPIN_`-prefix, but designed to affect options passed to a
    called task/plugin. `SPIN_MKINSTANCE_REBUILD=True spin mkinstance` equals
    `spin mkinstance --rebuild`.

Constrains for property-key naming are not enforced, since most special cases
do not occur in practice, as plugins define their part of the config tree using
`config()` whereas the Python syntax permits assignments like
`config(foo.bar="value")` and `config(1foo="value")`.

## 6. Node Provisioning using with and without nodeenv

Thy nodeenv Python package is used to provision NodeJS from sources, while the
version to use must be defined by `node.version`. The node plugin additionally
provides the usage of a local NodeJS installation, via the `node.use` property.
For this we don't rely on nodeenv, since it does not support using a local
NodeJS installation on Windows. To be consistent on our main OS systems, we copy
the Node executable in both cases, while creating a symlink to the npm
executable on non-Windows. On Windows however, symlinks require higher
permissions, so we instead decided to let the node plugin create a CMD script
that calls npm.cmd of the existing installation.

## 7. Verbosity levels

Currently, there are two configuration properties which control the
verbosity level of spin and its plugins:

`/quiet={True, False}` and `/verbose={0|1|2}`

`/quiet` is set via CL option '-q, --quiet' and `/verbose` via CL
option `-v, --verbose`. Some code places use the one, some the other
setting. Also, there is `/quietflag` which is either `''` or `-q`
depending on the value of `/quiet`.

The proposal is to unify these similar concepts as follows:

1. There is one property `verbosity` which has the following values:

   - `-1`: means `quiet`
   - `0`: means `normal`
   - `1`: means `verbose`
   - `2`: means `more verbose` or `debug`

   Side note: To have the code more readable, we probably should use an
   `enum` here. Hereby:

   - `quiet` means "no output at all". This mode is
     e.g. necessary/handy if you want to pass the output to some
     other tool which expects which is picky about the input (e.g. it
     expects a parsable JSON). That in turn means that everything
     as well the core as the plugins have to evaluate
     `verbosity` in routines printing to stdout/err, which is most
     easily done via usage the function `spin.echo`. We cannot make
     every tool silent without doing more complex things like
     capturing all the output, so in the usage case above just
     separate the provision and the task-run spin calls.
   - `normal` is just the normal amount of verbosity: The CL-calls are
     echoed to stdout, warning and errors (if any) are printed to
     stderr. Which means that `spin.echo()`, `spin.warn()` and
     `spin.error()` are all enabled.
   - `verbose`: as normal, but `spin.info()` is enabled, too.
   - `more verbose` or `debug`: same as `verbose`, but `spin.debug()` is
     enabled, too.

2. We implement `spin.debug()` mentioned above and replace
   logging.debug()-usages with calls to this API. This is a more
   simpler and consistent model as the current one, where we use two
   different mechanisms to generate output.

3. We leave the CLI as is, but make `-q` and `-v` mutually exclusive.

4. We throw `/quietflag` away: tools have different CLI and its for
   the according task to evaluate `verbosity` and control its tool in
   the proper way.

5. As well the core as the plugins use the same verbosity
   level. Moreover, the plugins have to evaluate the verbosity level
   and map it in a suitable way to the verbosity level of the
   according tools they call.

6. If the user wants different verbosity for different spin
   activities, she should make different calls. As an example,
   if you want just the task to run in very verbose mode but not
   the provisioning, instead of:

   ```
   spin -vv --provision pytest
   ```

   you call:

   ```
   spin -q --provision
   spin -vv pytest
   ```

   It this isn't doable for technical reasons: well, bad luck.

7. We move the property `verbosity` to the `/spin`-subtree?

## 8. Extending the CLI

When extending the CLI we want to make sure that spin keeps being consistent and
uses the best practices we find in the field.

1. A (sub-)command (aka task) should do one thing. This could be "setup X", "run
   the tests".
2. If your task does multiple unrelated things, it should be split into multiple
   tasks. However, if those tasks do different things but are somewhat related
   to each other - using `spin.group` might be a good idea.
3. Flags and options should only change the way how tasks achieve their goal.
4. If you have a task that does something semantically equal to an existing
   tasks, you can make use of workflows.

This changes some parts of the current implementation of cs.spin, especially the
--provision and --cleanup flags, as they violate 8.3, as the thing that spin
_does_ is provide a way to run tasks of plugins. Thus, we'll be reimplementing
the CLI such that we'll have a provision and a cleanup task.
