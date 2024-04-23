# Organization and Distribution of Spin Plugins

Spin -- or more precise its "core" -- is designed to be essentially
bare of user-facing functionality, all "interesting" stuff happening
in the plugins. The core and the plugins have in general different
authors and distinct livecycles. Consequently, they should be
distributed separately.

This is not the case yet because of convenience and lack of a sound
concept. This text strives to change the latter; the goal is to gain
understanding for how to organize the plugins, their repositories and
the packages they're distributed in, such that as well the
writing/maintaining as the consumption of them is effective and
efficient.

## The Proposal

Core idea: we cluster the plugins by tech-stack they're dealing with,
in the first place. We put every cluster in its own repository,
maintain and distribute them together.

The current set of plugins (`src/spin/builtin/` and `qs/spin-plugins`)
should be pulled apart like this (first level are clusters, second
the plugins):

**spin-python**:

- `pytest` (spin-plugins)
- `behave` (spin-plugins)
- `python` (builtin)
- `nosetest` (builtin)
- `flake8` (builtin)
- `devpi` (builtin)
- `piptools` (builtin)
- `radon` (builtin)
- task `run` (builtin/**init**.py)
- task `env` (builtin/**init**.py)
- task `shell` (builtin/**init**.py)

**spin-ce**:

- `ce_services` (spin-plugins)
- `mkinstance` (spin-plugins)

**spin-java**:

- `java` (builtin)
- `maven` (builtin)

**spin-frontend**:

- `node` (builtin)

**spin-cpp**:

- `cpp_check` (builtin)
- `cpp_lint` (builtin)
- `scons` (builtin. For cs.threed and cs.workspaces)

**spin-vcs**:

- `vcs` (builtin)
- `pre-commit` (builtin)
- `git` (builtin)
- `gitlab` (builtin)

_Note_: `pre-commit` and `gitlab` may not fit perfectly here, but
surely better than in other clusters.

**spin-docs**:

- `sphinx` (builtin)

The second clustering criterion would be "by-org-unit": different
organizational units differ as well by the processes they use as the
domain(s) they're addressing, and this is obviously reflected in their
tools usage. Based on this criterion, we define the following cluster:

**spin-consd**:

- `stdworkflows` (builtin)
- `preflight` (builtin): probably obsolete

We expect as well the first as the second set of 'clusters' to grow.

Then there is another group of tasks which are neither tech-stack nor
org-unit-specific. Moreover, at least part of them (`run`, `env`,
`shell`?) doesn't even feel as optional. Therefore, I propose to leave
them builtin into the core:

- task `system-provision`
- task `distro` (do we need this at all?)
- group `global` and its tasks (?)

As for the rest:

- `cache` (builtin): belongs into `scons`?
- `build` (builtin): belongs `stdworkflows`
- `pytest` (builtin): obsoleted by `pytest` (spin_plugins)
- `buildout`: obsolete?
- `ce15`: obsolete (my 3-years old attempt)
- `eggs`: obsolete (my 3-years old attempt)

That way, we would get ~10 repositories each hosting a set of related
plugins. Of course, that will cause some redundancy in their
boilerplate, which will (or will not, I'm not sure) lead to increased
maintenance efforts. So we may decide to put together some clusters in
one (or a couple) repositories to reduce them, and create more that
one package from those repositories.

The packages should be uploaded on and consumed from ConPI. Index candidates are:

- https://packages.contact.de/tools/misc: here we put such stuff, mostly.
  It isnt interited by the app-indices though
- https://packages.contact.de/tools/stable: this one is.
  But it has another purpuse, at least originally (namely pinning some
  TP versions if we had trouble with new ones)
- A completely new one?

## Distribution to Customers/Partners/...

If things work out and spin as the new taskrunner implementation will
be successful, the parties outside @C would ask to use it. What are
the potential distribution channels?

1. **Transfer per mail/USB-stick/Cloud-Storage/whatever to the
   customer and make them consume them from the filesystem**: is not
   acceptable nowadays. People won't accept such archaic processes, it
   would make us look stupid as a software vendor.

2. **Own PyPI open to the customers/partners**: We already try that with ...,
   it causes some technical headache and synchronizing overhead but
   overall this way would be acceptable.

3. **Releasing on PyPI**: Spin core and -- to a significant degree --
   its plugins deal with OSS technology and tools. Its code doesn't (or
   at least isn't supposed to) contain secrets. So it doesn't feel like
   a completely stupid idea to publish the core and the subset of plugins
   which are interested for customers/partners directly on pypi.org.

This is a topic for the months to come, though.

## Other Considered Clustering Alternatives

1. **Keeping the status quo**

   Not really an alternative. Mentioned just for completeness.

2. **Each plugin in an own repository (and package)**

   Each plugin is put into an own repository and is distributed
   separately.

   **Pros**:

   - This offers maximum flexibility for the composition of
     what-to-be-pull configurations

   **Cons**:

   - Lots of redundancy.
   - The change process is severely slowed down. The maintainers will
     have to do lots of small MRs.

3. **One repository && package for all plugins**

   We put everything (all from `src/spin/builtin` and all from
   `qs/tooling/spin_plugins` into one repository and distribute everything
   in one package.

   **Pros**:

   - ?

   **Cons**:

   - Nut much gain over the status quo, actually.
