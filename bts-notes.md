cs.spin's documentation

> remove most workflow reference as it is not part of cs.spin anymore, this must
> be documented within spin_consd.

1. About spin
   > mostly keep the current stuff

- what is spin, what problem solves it
- Spin's plugin system
  - mention the QS-maintained plugin-packages
- How to provision a project (short)
- FAQ

2. Installing cs.spin

   > just update to match current state

3. Using spin
   > mostly update the current stuff

- shorten the introduction (+ note that spin itself does almost nothing)
- Writing spinfile.yaml
  - Importing plugins (merge with "Plugins" section)
  - Local plugins
  - Plugin-packages
  - Interpolation
  - Extra tasks
    > drop "System Dependencies" and "Plugins" section
  - Build rules
- Sample global.yaml
- Environment variables
- Troubleshooting
  - Order of property overriding

4. Plugin development guide

- Plugin life-cycle
  - keep as is + add the diagram from tdocs/architecture.md
- Developing plugins
  > mostly keep the current stuff
  - add code-block with init, configure, provision, finalize_provision, cleanup
    and task
- Plugin schema
  - Remove spin's internal schema reference
  - demonstrate short schema on dummy plugin
  - list the available types + internal
  - mention to not add "requires" to schema
- Using spin's API
  - Demonstrate:
    - Interpolation
    - Automatic interpolation
    - Property access

5. Command-line reference

6. Plugin API reference

7. Schema reference

> drop "Release Notes" section or generate automatically + make it last section

TODO:- create a configuration tree section and link all config tree references to it

NOTES:

- kubernetes via kubespray
- rancher zum verwalten - auf einem externen host im container?
- conpi war gepinnt auf einen node? Wie wurde das nun behoben?
