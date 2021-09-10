==============
 Provisioning
==============

1. Get somehow to spin (this is mostly installing Python and then ``pip install spin``

2. Setup your machine to *build* the project. This requires `sudo`
   privileges. ``spin --provision-machine`` will emit a list of
   commands that are tailored for the host.

   .. code-block:: console

      $ spin --provision-build-machine | sudo sh

3. Setup user-level, project dependencies. This will not require sudo
   privileges, but install stuff locally, either using pre-installed
   environment management tools like `pyenv`, or installing to a cache
   managed by `spin`.

   .. code-block:: console

      $ spin --provision

   Said cache is put into ``~/.spin`` (better :envvar:`XDG_OPEN`). The
   cache location can be set to some other place, e.g. when preparing
   a Docker image for building (that way, those dependencies external
   to the project don't have to be pulled from the users's home
   directory).

4. Provisioning also creates (for Python projects), a virtualenv
   directory. This is currently in-tree, but should be configurable to
   live out-of-tree (leaving the question, how to make such an
   environment known to followup calls to `spin`, if it can't be
   computed from properties like Python ABI, platform etc.). One
   option would be an approache like the one `CMake` uses: create an
   environment, and then run tools from there (or -- in the case of
   `CMake` -- direct the tool to use it: ``cmake --build
   <directory>``.

5. Do the **edit-compile-test** cycle; perhaps include tools like
   `git` and issue tracking stuff to manage branches, messages for
   commits and reviews etc.

6. **Doing a release**, including tagging, bumping version numbers
   etc.

7. Either support **manual release builds and uploads**, including
   matrix, or do that via CI. This includes build, verification/test,
   packaging into wheels or other distribution formats, creating
   Docker images and publishing those to package servers.


Use Cases
=========

* **Provision system-level build-time requirements**; this starts from
  inside a project. The project's ``spinfile.yaml`` directly, and
  indirectly the plugins, that ``spinfile.yaml`` loads, declare
  system-level requirements for different operating systems and
  distributions. E.g. on a Debian system, ``apt`` packages are
  declared. `spin` then generates a set of commands that have to be
  run to make the requirements available.

  Here is a sketch of how projects declares its system-level
  requirements:

  .. code-block:: yaml

     ...
     linux:
       build:
         debian: [build-essential, zlib-dev, libkrb5, ...]
         alpine: [gcc, krb5-dev, zlib2, ...]
       run:
         debian: [libaio]

  On a Debian system, spin would emit the following:

  .. code-block:: console

     $ spin --system-build-requirements
     apt install build-essential zlib-dev libkrb5 libaio ...
     $ # To actually do this, pipe it so sudo
     $ spin --system-build-requirements | sudo sh

  Whereas on an Alpine system, it would look like so:

  .. code-block:: console

     $ spin --system-build-requirements
     apk add gcc krb5-dev zlib2 ...

* Windows would probably need some scripting (refere to
  win-build-docker project).

* This can also be used when **creating a Docker image for building**
  the project (this is a duty of the project, as it cannot be known
  generally what the project requires).

  .. code-block:: docker

     FROM <also-comes-from-project?>
     ...
     # Somehow make sure, that an appropriate version of Python is
     # installed in this image
     ...
     # Install spin
     RUN pip install -q spin
     # All set to provision dependencies to the image
     RUN spin --system-build-requirements | sh

* **Provision system-level runtime requirements** (is this
  questionable?); this would be required to build runtime images from
  the project, which is probably worthwhile; OTOH this would also
  require to somehow transport runtime requiremens from *installed*
  packages to other projects. Can be done by building ``FROM
  ...``. E.g.

  * `cs.platform` creates a runtime container:

    .. code-block:: console

       $ spin docker build
       ... creates cs.platform:16.0

    Some app builds an image based on that:

    .. code-block:: docker

       FROM cs.platform:16.0
       # This image will have everything to run cs.platform, and also
       # spin, as that was required to build the container and we
       # didn't delete it above.
       RUN  spin --runtime-requirements | sh
