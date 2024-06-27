# Conventions and Guidelines for Spin Plugins

To optimize spin's user experience and reduce the mental/memorizing
load on the developers using the spin plugins, we should strive for a
consistent user interface and behavior. To achieve it, we
introduce some conventions to be followed when programming the spin
plugins. The following sections cover the details.

**Open points**:

- Where to document the tasks? And their CLI?
- The plugins should evaluate the `spin.verbose` flag, if the tools
  provide some verbosity controls
- Consider whether prefixing the info/warning/error outputs with the
  name of the plugin is a good idea.

## General Recommendations

1. The name of the plugin should be as well descriptive as short.
   The latter is important since it is also used as the name of the
   node of the plugin-specific config-subtree, so a over-long names
   makes for unnecessarily long config-three-paths which are
   more difficult to handle on CLI etc.
   In case you're wrapping a tool, "plugin-name == task-name ==
   tool-name" makes for a good UX in many cases.

2. Choose the name of the task such that it is easy to type. It will
   be used a lot on command line. Example:

   ```bash
   $ spin pytest
   spin: cd /home/wen/src/qs/spin/cs.spin
   spin: activate /home/wen/.cache/spin/cs.spin-e8JDblce/cp39-manylinux_2_38_x86_64
   spin: pytest -k 'not slow' ./tests
   ...
   ```

3. The code should be compliant with our
   [Python Coding Guide](https://wiki.contact.de/index.php/Python_Coding_Guide).

TBC

## Conventions for the Configuration Trees

In general:

1. Strive for compact configuration sub-trees.
2. If your plugin drives a tool and the executable name can vary for some reasons:
   use the property "exe"(?) to configure the name of the latter.
3. Plugins wrapping tools should consider providing a list of
   arguments names "args" which is appended/inserted to the command
   line calling the tool.
4. The default-values of configuration properties shipped with the
   plugins should match the need in the majority of cases.
5. When provisioning third-party packages, you usually want to pin the
   major segment of their version.

   **Reasoning**: we depend on the
   behavior of the tools and especially on their CLIs. If left unpinned,
   (major) tool updates would eventually break the plugin.
   On the other hand, we would like to avoid the tedious "raise the
   pinning to the next version" maintenance efforts.
   So, the sweet spot here is a partial pin which allows the bug fixes
   and minor changes to "flow" and avoids breaking changes. For Python dependencies,
   the compatibility operator is appropriate in many situations:

   ```
   requires=config(python=["cpplint~=1.6.7"])
   ```

Moreover, we can differentiate between two ways of modeling the
config-tree of a spin plugin:

1. "Mkinstance model" or "the cs.recipes-way"

   - We provide a configuration property for every(\*) CLI parameter of
     mkinstance
   - We compute the values of some of those to ease the usage
   - The plugin itself has some logic to call additional tools in
     certain circumstances

   This is because mkinstance is central to our development model and
   thus heavily used by developers, which want to control different
   CLI params independently.

   Pros:

   - every CLI param can be controlled easily an independently
   - automatically computed values ease the usage of the tool
   - you don't have to set every option in your spinfile,
     defaults "match" in many situations

   Cons:

   - The configuration tree is essentially bound to the CLI of the
     tool with all the negative effects (e.g. plugin breakage by
     minor changes of tools' CLI)

2. The "behave model" or "the Makefile-way"

   The taskrunner plugin is a thin layer above the tool and doesn't
   provide dedicated control for every CLI option. Instead, we provide
   generic option lists to customize the tool calls, i.e. something like:

   ```python
   defaults = config(opts=["--format=pretty", "--no-source"], tests=["tests/accepttests"])


   @task()
   def behave(cfg):
       """Run the 'behave' command."""
       sh("behave", *cfg.opts, *cfg.tests)
   ```

   If the tool has a more complex CLI with ordering constraints, we would
   provide such generic lists for every "block" in the CLI.

   Pros:

   - results in simple plugins implementations
   - results in simple configuration trees
     Cons:
   - Customizing the calls is (at least) less comfortable and readable

Most plugins should follow the second model.

## Secret Management

Often, the plugins have to deal with secrets (typically
auth-credentials) or other more-or-less sensitive information (like
names of internal infrastructure endpoints).

Those secrets obviously cannot be part of the plugin implementation,
including the configuration defaults (where they belong semantically
in many cases).

Canonical solution for that problem is pulling those secrets from the
configuration tree property and interpolating the default value from
an environment variable, i.e. something like this:

```Python
defaults = config(
...
    postgres=config(
        postgres_syspwd="{POSTGRES_SYSPWD}"
```

That way we can provide the secrets conveniently as well on CI/CD as
AWS/production as on dev-workstations. Additionally, developers have
the additional benefit to control the according configuration
properties via private unshared `.spin/global.yaml`.

TODO, discuss: naming convention for those environment variables?

## Fail Early

When triggering potentially long-running processes depending on some
conditions which may not be fulfilled, it is nice to check the latter
early and fail fast. A typical example is a missing secret, the
according check may look as below:

```
if dbms == "postgres" and not cfg.mkinstance.postgres.postgres_syspwd:
    die(f"Please provide the PostgreSQL system password in the property 'mkinstance.postgres.postgres_syspwd'")
```

## Parametrizing/Configuration of the Spin Plugin or the Underlying Tool

When we want to provide a configuration possibility for the behavior
of the spin plugin or the underlying tool, we have usually the
following choices:

1. We add a command line parameter to the plugin, for example:

   ```Python
   @task()
   def mkinstance(cfg,
                  rebuild: option("--rebuild", is_flag=True)):
   ```

2. We put a property into the config-tree of the spin plugin as below:

   ```Python
   from spin import config
   defaults = config(
       ...
       key="value"
       ...
   )
   ```

   Defaults of those are shipped in the task implementations, they can be changed
   (and persisted) in Spinfiles and can also be changed in the command
   line using the `-p <name>=value`-syntax

3. We document/demonstrate how to configure the wanted behavior in
   the configuration file template of the underlying tool, for
   instance:

   ```ini
   [isort]
   profile=black
   known_first_party=cs,cdb*
   ```

The rule of a thumb is here as follows:

1. If the according behavior should be variable **per call**, use the first
   possibility. An example for that is the CE-instance to run the tests against:

   ```bash
   $ spin pytest -I sqlite
   <tests run against SQLite>
   ...

   $ spin pytest -I postgres
   <tests run against PostgreSQL>
   ...
   ```

   This offers a more convenient syntax than setting the configuration
   properties via CLI, the example above would look like follows:

   ```bash
   $ spin -p spin.instance=sqlite pytest
   <tests run against SQLite>
   ...
   ```

   Use this method sparingly, though, to avoid overloading the CLI of
   the plugins.

   Moreover, if the task is designed to be called by a workflow
   (many/most should), then consistency with the CLI of this
   workflow and the CLIs of the other tasks called by this workflow is
   (way) more important then the individual CLI of this particular
   task. That means, if we want to introduce some switch which is
   inconsistent with the CLI of this 'task cluster' than you should
   use rather use configuration tree properties than CL parameters.

2. If the according behavior should be variable **per component** or
   **per machine**, use the first possibility (config-tree of the
   plugin). That way the components can persist the settings in the
   `spinfile.yaml` or the `global.yaml`. The config-tree properties can
   also be set per CLI per call, but the syntax is somewhat more verbose
   than in the case above, as already said.

3. If the behavior should be changed for the majority of code-bases
   and be the new 'static' default, without much necessity to vary it
   across machines/components etc. use the third possibility.

   The demonstration and inline-comments are nevertheless valuable
   for people analyzing the behavior of tools and the less numerous
   cases where behavior has to be changed.

## Provisioning

Spin tries to ease the live of developers via automating the provision
of projects requirements. This ranges from runtimes (CPython/JDK/Node)
over service-like things (Redis/Apache Solr/Traefik) down to small
third party libraries and such.

TBC

## Transparency, Behavior Consistency and "ready-to-go" Command-Lines

One of the goals of spin is to be transparent about the work it does
and to demonstrate/learn the devs now to use the underlying tools.

Therefore:

- The command lines used to make subprocess calls have to be printed
  on the standard out stream and highlighted consistently. For the
  most cases just call the spin-API `sh` like follows:

  ```Python
  from spin import sh
  sh(npm, "install", "-g", req)
  ```

  If it doesn't work for your case, try to approximate its behavior.

- Setting the environment variables should be echoed in the output,
  too. Just call the spin API as follows:

  ```Python
  from spin import setenv
  setenv(COVERAGE_PROCESS_START=cfg.behave.cov_config)
  ...
  setenv(COVERAGE_PROCESS_START=None)
  ```

- When the plugin does something meaningful and notable without
  calling a subprocess, print a note to standard output, too:

  ```Python
  from spin import info
  info(f"Create {coverage_pth_path}")
  ```

When did right, the user should be able to copy the issued command
lines, drop them into the terminal and achieve the same results.
Moreover, to have the output layed out consistently, the plugins are
discouraged to write to standard output stream directly via `print` &
Co; instead, use according spin APIs (`echo`, `info`, `warning`,
`error`, `die`).

This principle applies to the rest of spin APIs too; this makes for
`consistent behavior across the plugins. E.g. prefer `spin.rmtree`to`shutil.rmtree`.

## Prefer spin APIs

To offer consistent behavior, plugins should prefer using spin API to
similar APIs from the standard libraries and packages. E.g. prefer `spin.rmtree`
to `shutil.rmtree`.

## Performance; Memoizing

TBC

## Consider the Outside-of-CONTACT Usage

We want to address the automation demand outside CONTACT/SD, too. So,
for many spin plugins, we have to expect the usage outside CONTACT, in a
different organization with different infrastructure. That means that
the plugin should not hardcode assumptions about the location of
infrastructure services and other CONTACT specifics.

On the other hand, for productivity and consistency reasons,
maintaining and providing a set of such CONTACT- (or team-) specific
setting does make sense. So it feels like we should support such a
category of plugins, or provide a `global.yaml`-template.
