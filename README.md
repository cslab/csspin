# cs.spin

Spin is a task runner that aims so solve the problem of standardizing
workflows for many similar projects. It does this by encapsulating
task definitions in Python packages and automating the provisioning of
development sandboxes and dependencies.

Documentation: http://qs.pages.contact.de/spin/cs.spin

## CPython Support Policies

Our CPython support policy for cs.spin aligns with the official CPython release
schedule, encompassing versions 3.9 through 3.12 (so far).

## Release Procedure

The version scheme used is major.minor.patch while following the well-known
standards @CONTACT (https://wiki.contact.de/index.php/Versionsnummer).
Steps to create a release:

0. Preparations

   - Verify that all relevant changes are merged into the master branch, which
     is the source for all releases.
   - Also make sure that the latest non-scheduled master pipeline is green.
   - Ensure that release related merge request and issues are labeled and closed
     properly.
   - If there is a milestone, make sure that all tasks are done.

1. Enter the Repository within GitLab > Releases > New Release, select the
   master branch and desired tag. Further down, enter the release notes
   including a list of changes (e.g. mention resolved issue + link related MR)
   and further information that might be useful. Make sure to align the style of
   the release notes to those of previous releases.

2. Hit "Create release" ✨

3. [optional] If the change need to be distributed within the
   [cetest](https://code.contact.de/qs/images/cetest) image, follow the release
   procedure there.

4. [optional] Create a DemoIT! demonstrating the latest improvements of cs.spin.
