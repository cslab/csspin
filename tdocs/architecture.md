# The Architecture of cs.spin

The following diagram schematically visualizes the action spin performs during a
call using `--cleanup`, `--provision`, a task, or a combination of those.

```mermaid
graph LR
    start(((entry))) --> load_configuration_files
    load_configuration_files --> |cleanup: yes| cleanup__
    cleanup__ --> |provision: no| end1(((end)))
    cleanup__ --> |provision: yes| load_configuration_files
    build_tree__ --> |provision: no; task: no| end1
    build_tree__ --> |provision: no; task: yes| task__
    load_configuration_tree__ --> |provision: yes| provision["Provision Plugins - Calling provision()"]
    provision --> |task: no| end1
    provision --> |task: yes| task__
    task__ --> end1

    subgraph load_configuration_tree__[Load Configuration Tree]
        install_dependencies__
        load_configuration_files[Load Configuration Files]
        load_configuration_files --> |cleanup: no/done| build_tree__
        modify_tree__ --> install_dependencies
        install_dependencies --> sanitize_tree__

        subgraph build_tree__[Build Tree]
            load_builtin_plugins[Load Built-In Plugins] -->
            install_dependencies__
            install_dependencies__ --> modify_tree__
            install_dependencies["Configure Plugins - Calling configure()"]

            subgraph install_dependencies__[Install Dependencies]
                install_plugin_packages[Install Plugin Packages] -->
                install_plugins[Install Plugins]
                install_plugins --> tpp[Install TPP and cs.*]
            end
            subgraph modify_tree__[Modify Tree]
                direction LR
                apply_environment[Environment Variables] -->
                apply_cli[Command-Line Parameters]
            end
            subgraph sanitize_tree__[Sanitize Tree]
                interpolate_all_values[Interpolate/resolve all Values] -->
                enforce_typecheck[Enforce Typecheck]
            end
        end
    end

    subgraph task__[Task]
        init["Calling init()"] --> task[Calling the task]
    end
    subgraph cleanup__[Cleanup]
        cleanup__a["Cleanup Plugins - Calling cleanup()"]
        cleanup__a --> cleanup__b[Purge Plugin Directory]
    end
```
