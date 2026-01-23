# Development and Contributing Guide

This document provides instructions for users, developers, and maintainers who
want to share ideas, report issues, contribute code, or create releases for
the csspin project.

The csspin repository is hosted on a private GitLab instance, while the
repository itself is mirrored to [GitHub](https://github.com/cslab/csspin) for
public visibility (https://github.com/cslab/csspin).

## Development Prerequisites

Make sure you have the following installed:

- [pre-commit](https://pypi.org/project/pre-commit/) or
  [prek](https://pypi.org/project/prek/)
- System requirements as documented in the [documentation](doc/installation.rst)

## Contribution Guidelines

Please follow the guidelines below when contributing to the csspin project.

### Reporting Issues

Reporting bugs and proposing features is an important part of the development
process, so please feel free to report any issues you encounter _before_
proposing code contributions.

External contributors should use the [GitHub
repository](https://github.com/cslab/csspin/issues) for reporting issues while
CONTACT Software Group GmbH internal contributors can use the GitLab issue
tracker.

### Code Contributions

Code contributions are welcome from both internal and external contributors.
Please follow these steps considering code contributions:

1. If you are planning to work on a new feature or bugfix, please make sure to
   create an issue first. This avoids duplicate work and helps identify the if
   the change is aligned with the project's goals. Discuss the proposed changes
   in the issue and get it approved by a maintainer.
2. After the issue is created, assigned, and agreed upon, work on your changes
   in the forked repository (for external contributors) or new branch (for
   CONTACT-internal contributions). Once the implementing is started or done,
   create a pull or merge request _draft_ targeting the master branch, linking
   the related issue, and assigning yourself.
3. Before marking the request as ready for review, make sure to address all of
   the following points:
   - [ ] All tests pass
   - [ ] All pre-commit hooks pass
   - [ ] Relevant tests have been added or updated (if necessary)
   - [ ] The documentation has been updated (if necessary)
   - [ ] The code is sufficiently documented (docstrings, comments, etc.)
   - [ ] The changes adhere to the project's coding standards including:
     - Pre-Commit hooks and their configuration
     - Standards and best practices as described csspin's documentation
     - CONTACT-internal coding guidelines (mostly covered by pre-commit
       hooks, but the reviewer might ask for additional changes)
   - [ ] Take your time to prepare the code and merge/pull request description
         before marking the request as ready for review. A well-prepared request
         will save a lot of time during the review process.
4. Mark the request as ready for review and assign a reviewer (usually a
   maintainer).
5. Wait for the review to be completed. Address any feedback provided by the
   reviewer.
6. Once the review is approved and all checks pass, the request can be merged
   into the master branch. This is usually done by one of the maintainers. (For
   pull requests from external contributors on GitHub, a maintainer will take
   over the changes and create a corresponding merge request on GitLab, as the
   GitHub repository is only the push mirror target.)

The following example demonstrates the typical workflow for contributing code to
csspin:

1. Create an issue, discuss the proposed changes, and get it approved.
2. Fork the repository (GitHub) or create a new branch (GitLab).
3. `git clone <your-fork-or-repo-url> csspin && cd csspin && pre-commit install`
4. `uv venv venv && source venv/bin/activate && uv pip install -e .` (to set up
   the development environment)
5. Implement the changes (code, tests, documentation, etc.).
6. Run tests to ensure everything works as expected, e.g. via `spin test`
7. Commit your changes with descriptive messages and ensure all pre-commit
   hooks pass.
8. Create a pull or merge request targeting the master branch, linking the
   related issue, documenting changes and considerations, and assigning
   yourself.
9. Mark the request as ready for review and assign a reviewer.
10. Address any feedback from the reviewer.
11. Once approved, a maintainer will merge or take over the request.

## Release Procedure

> This section is only relevant for maintainers of the csspin project.

The version scheme used is major.minor.patch while following the well-known
standards at CONTACT (https://wiki.contact.de/index.php/Versionsnummer).

Releases are created by csspin maintainers within the GitLab instance hosting
this repository.

Steps to create a release:

0. Preparations
   - Verify that all relevant changes are merged into the master branch, which
     is the source for all releases.
   - Also make sure that the latest non-scheduled master pipeline is green.
   - Ensure that release related merge request and issues are labeled and closed
     properly.
   - If there is a milestone, make sure that all tasks are done.

1. Create the release notes by opening a new merge request at the csspin
   repository in GitLab targeting the master branch and adding a new section to
   the `doc/relnotes.rst` file. Follow the instructions given in that file
   regarding the format of the release notes. Once the merge request is reviewed
   and approved, merge it into master.

2. After the release notes have been merged and the master pipeline is green,
   create the actual release within GitLab by creating a new tag with the scheme
   "v<major>.<minor>.<patch>" (e.g. "v2.1.0" for version 2.1.0).

3. Hit "Create tag" ✨

4. [optional] If the change need to be distributed within the
   [cetest](https://code.contact.de/qs/images/cetest) image, follow the release
   procedure there.

5. Announce the release via
   https://community.contact-software.com/c/news-and-announcements/releases/11
   channel. Don't forget to set the tags "ptm" and "csspin" for better
   visibility.

6. [optional] Create a Demo It! demonstrating the latest improvements of csspin.
