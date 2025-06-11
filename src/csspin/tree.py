# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2020 CONTACT Software GmbH
# https://www.contact-software.com/
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Disabling "union-attr" since inspect.currentframe() could return None, which
# is not the case for the implementation in this file.
# mypy: disable-error-code=union-attr

from __future__ import annotations

import inspect
import os
import re
import sys
from collections import OrderedDict, namedtuple
from types import ModuleType
from typing import TYPE_CHECKING

import ruamel.yaml
import ruamel.yaml.comments
from path import Path

from csspin import (  # pylint: disable=cyclic-import
    Verbosity,
    debug,
    die,
    interpolate1,
    warn,
)
from csspin.schema import DESCRIPTOR_REGISTRY

if TYPE_CHECKING:
    from collections.abc import Hashable
    from typing import Any, Callable, Generator, Iterable

from traceback import format_exc

KeyInfo = namedtuple("KeyInfo", ["file", "line"])
ParentInfo = namedtuple("ParentInfo", ["parent", "key"])


class ConfigTree(OrderedDict):
    """A specialization of `OrderedDict` that we use to store the
    configuration tree internally.

    `ConfigTree` has three features over `OrderedDict`: first, it
    behaves like a "bunch", i.e. items can be access as dot
    expressions (``config.myprop``). Second, each subtree is linked to
    its parent, to enable the computation of full names:

    >>> tree_keyname(parent.subtree, "prop")
    'parent->subtree->prop'

    Third, we keep track of the locations settings came from. This is
    done automatically, i.e for each update operation we inspect the
    callstack and store source file name and line number. For data
    read from another source (e.g. a YAML file), the location
    information can be updated manually via `tree_set_keyinfo`.

    Note that APIs used to access tracking information are *not* part
    of this class, as each identifier we add may clash with property
    names used.
    """

    def __init__(self: ConfigTree, *args: Any, **kwargs: dict) -> None:
        ofsframes = kwargs.pop("__ofs_frames__", 0)
        super().__init__(*args, **kwargs)
        self.__keyinfo = {}
        self.__parentinfo = None  # pylint: disable=unused-private-member
        for key, value in self.items():
            self.__keyinfo[key] = _call_location(2 + ofsframes)  # type: ignore[operator]
            if isinstance(value, ConfigTree):
                # pylint: disable=protected-access,unused-private-member
                value.__parentinfo = ParentInfo(self, key)

    def __setitem__(self: ConfigTree, key: Hashable, value: Any) -> None:
        super().__setitem__(key, value)
        _set_callsite(self, key, 3, value)

    def setdefault(self: ConfigTree, key: Hashable, default: Any = None) -> Any:
        val = super().setdefault(key, default)
        _set_callsite(self, key, 3, default)
        return val

    # __setattr__ and __getattr__ give the configuration tree "bunch"
    # behaviour, i.e. one can access the dictionary items as if they
    # were properties; this makes for a more convenient notation when
    # using the settings in code and f-like interpolation expressions.

    def __setattr__(self: ConfigTree, name: str, value: Any) -> None:
        if any(name.startswith(f"{char}_ConfigTree__") for char in ("", "_")):
            # "protected" and "private" variables must not go into the
            # dictionary, obviously.
            object.__setattr__(self, name, value)
        else:
            self[name] = value
            _set_callsite(self, name, 3, value)

    def __getattr__(self: ConfigTree, name: str) -> Any:
        if name in self:
            return self.get(name)
        raise AttributeError(f"No property '{name}'")


def tree_get_descriptor(tree: ConfigTree, key: Hashable) -> Any:
    """
    Retrieve the descriptor of a key within the configuration tree or ``None``
    if there is no schema available for this key.
    """
    if schema := getattr(tree, "_ConfigTree__schema", None):
        return schema.properties.get(key, None)
    return None


def tree_set_descriptor(
    tree: ConfigTree, key: Hashable, desc_type: Any, **kwargs: Any
) -> None:
    """Set or override descriptor of type `descriptor` to `key` property in `tree` ConfigTree.
    All additional arguments are passed to the descriptor's __init__."""
    schema = getattr(tree, "_ConfigTree__schema", None)
    if not hasattr(schema, "properties"):
        setattr(schema, "properties", ConfigTree())

    desc = desc_type(**kwargs)
    schema.properties[key] = desc
    if isinstance(tree[key], OrderedDict):
        setattr(tree[key], "_ConfigTree__schema", desc)


def tree_set_types(tree: ConfigTree, key: Hashable, types: Iterable[str]) -> None:
    """Set element's type"""
    if desc := tree_get_descriptor(tree, key):
        desc.type = list(types)


def tree_typecheck(tree: ConfigTree, key: Hashable, value: Any) -> Any:
    if desc := tree_get_descriptor(tree, key):
        return desc.coerce(value)
    return value


def tree_types(tree: ConfigTree, key: Hashable) -> list:
    """Retrieve the types of a specific key within the configuration tree."""
    if desc := tree_get_descriptor(tree, key):
        return desc.type  # type: ignore[no-any-return]
    return []


def tree_sanitize(cfg: ConfigTree) -> None:
    """Walk through the tree recursively to interpolate all str and Path
    values while enforcing types.

    Enforcing types after interpolation enables defining values that can be
    interpolated to non-string and non-path objects.

    NOTE: This implementation doesn't work for lists containing objects. So far
          there is no use-case for having config trees within lists.
    """

    def enforce_typecheck(
        cfg_: ConfigTree,
        keys: list,
        value: str | Path,
        ki: KeyInfo,
    ) -> None:
        if len(keys) == 1:
            cfg_[keys[0]] = tree_typecheck(cfg_, keys[0], value)
            tree_set_keyinfo(cfg_, keys[0], ki)
        else:
            enforce_typecheck(cfg_[keys[0]], keys[1:], value, ki)

    interpolateable = (str, Path)
    for _, value, fullname, ki, _, _, _ in tree_walk(cfg):
        if (
            isinstance(value, interpolateable)
            and (value := interpolate1(value))
            or (
                isinstance(value, list)
                and (
                    value := [
                        interpolate1(val) if isinstance(val, interpolateable) else val
                        for val in value
                    ]
                )
            )
        ):
            enforce_typecheck(
                cfg_=cfg,
                keys=fullname.split("->"),
                value=value,
                ki=ki,
            )


def tree_update_key(tree: ConfigTree, key: Hashable, value: Any) -> None:
    OrderedDict.__setitem__(tree, key, value)  # type: ignore[assignment]


def _call_location(depth: int) -> KeyInfo:
    fn, lno, _, _, _ = inspect.getframeinfo(
        sys._getframe(depth)  # pylint: disable=protected-access
    )
    return KeyInfo(fn, lno)


def _set_callsite(tree: ConfigTree, key: Hashable, depth: int, value: Any) -> None:
    if hasattr(tree, "_ConfigTree__keyinfo"):
        # pylint: disable=protected-access
        tree._ConfigTree__keyinfo[key] = _call_location(depth)
    tree_set_parent(value, tree, key)  # type: ignore[arg-type]


def tree_set_keyinfo(tree: ConfigTree, key: Hashable, ki: KeyInfo) -> None:
    tree._ConfigTree__keyinfo[key] = ki  # pylint: disable=protected-access


def tree_keyinfo(tree: ConfigTree, key: Hashable) -> KeyInfo:
    if key not in tree:
        die(f"{key=} not in configuration tree.")

    return tree._ConfigTree__keyinfo[key]  # type: ignore[no-any-return] # pylint: disable=protected-access


def tree_set_parent(tree: ConfigTree, parent: ConfigTree, name: str) -> None:
    if hasattr(tree, "_ConfigTree__parentinfo"):
        tree._ConfigTree__parentinfo = ParentInfo(  # pylint: disable=protected-access
            parent, name
        )


def tree_keyname(tree: ConfigTree, key: str) -> str:
    if key not in tree:
        raise AttributeError(f"{key=} not in {tree=}")

    path = [key]
    parentinfo = tree._ConfigTree__parentinfo  # pylint: disable=protected-access
    while parentinfo:
        path.insert(0, parentinfo.key)
        parentinfo = (
            parentinfo.parent._ConfigTree__parentinfo  # pylint: disable=protected-access
        )
    return "->".join(path)


def tree_load(fn: str) -> ConfigTree | Any:
    yaml = ruamel.yaml.YAML()
    with open(fn, encoding="utf-8") as f:
        try:
            data = yaml.load(f)
        except ruamel.yaml.parser.ParserError as ex:
            die(f"\n{ex.problem_mark.name}:{ex.problem_mark.line + 1}: {ex}")
    return parse_yaml(data, fn)


def tree_walk(config: ConfigTree, indent: str = "") -> Generator:
    """Walk configuration tree depth-first, yielding:
    - Key
    - Value
    - Full name of the key
    - Tracking information
    - Types
    - Indentation string that increases by ``"  "`` for each level
    - Descriptor
    """
    for key, value in sorted(config.items()):
        yield key, value, tree_keyname(config, key), tree_keyinfo(
            config,
            key,
        ), tree_types(config, key), indent, tree_get_descriptor(config, key)
        if isinstance(value, ConfigTree):
            for key, value, fullname, info, types, subindent, desc in tree_walk(
                value, indent + "  "
            ):
                yield key, value, fullname, info, types, subindent, desc


def tree_dump(tree: ConfigTree) -> str:
    """Print the configuration tree in a human-readable format."""
    text = []

    grey, reset = "\033[90m", "\033[0m"

    def write(line: str, internal: bool = False) -> None:
        output = f"{grey}{line}{reset}" if internal else line
        text.append(output)

    cwd = os.getcwd()
    home = os.path.expanduser("~")

    def shorten_filename_line(info: KeyInfo) -> str:
        if (
            tree.verbosity < Verbosity.DEBUG
            and Path(info.file).absolute().dirname()
            == Path(__file__).absolute().dirname()
        ):
            return "csspin"

        if info.file.startswith(cwd):
            return f"{info.file[len(cwd) + 1 :]}:{info.line}"  # noqa: E203
        if info.file.startswith(home):
            return f"~{info.file[len(home):]}:{info.line}"
        return f"{info.file}:{info.line}"

    filterout = (DESCRIPTOR_REGISTRY["object"], ModuleType)
    tagcolumn = max(
        (
            len(shorten_filename_line(info) + ":")
            for _, _, _, info, _, _, _ in tree_walk(tree)
        ),
        default=0,
    )
    separator = "|"

    def build_tree_dump(tree: ConfigTree, key_prefix: str = "", ind: str = "") -> None:
        """Build the tree dump of passed configuration tree.

        :param tree: The tree to iterate through
        :param key_prefix: The prefix of the keys (only applicable for recursive
            calls to align with the top-level data type, e.g. "list")
        :param ind: Additional indention for the output
        """

        for key, value, _, info, types, indent, _ in tree_walk(tree):
            is_internal = "internal" in types
            if is_internal and not tree.verbosity > Verbosity.NORMAL:
                continue
            indent += ind
            key = key_prefix + key

            tag = shorten_filename_line(info) + ":"
            space = (tagcolumn - len(tag) + 1) * " "

            if isinstance(value, filterout):
                continue

            if isinstance(value, list):
                if value:
                    write(f"{tag}{space}{separator}{indent}{key}:", is_internal)
                    blank_location = len(f"{tag}{space}") * " "
                    for item in value:
                        if isinstance(item, filterout):
                            continue

                        if isinstance(item, str):
                            write(
                                f"{blank_location}{separator}{indent}  - {repr(item)}",
                                is_internal,
                            )
                        elif isinstance(item, ConfigTree):
                            build_tree_dump(item, key_prefix="- ", ind=indent + "  ")
                else:
                    write(f"{tag}{space}{separator}{indent}{key}: []", is_internal)
            elif isinstance(value, dict):
                if value:
                    write(f"{tag}{space}{separator}{indent}{key}:", is_internal)
                else:
                    write(f"{tag}{space}{separator}{indent}{key}: {{}}", is_internal)
            else:
                write(
                    f"{tag}{space}{separator}{indent}{key}: {repr(value)}", is_internal
                )

    build_tree_dump(tree)
    return "\n".join(text)


def directive_append(target: ConfigTree, key: Hashable, value: Any) -> None:
    if key not in target:
        die(f"{key=} not in passed target tree.")
    if not isinstance(target[key], list):
        die("Can't append value to tree since it's target not type 'list'")
    if isinstance(value, list):
        target[key].extend(value)
    else:
        target[key].append(value)


def directive_prepend(target: ConfigTree, key: Hashable, value: Any) -> None:
    if key not in target:
        die(f"{key=} not in passed target tree.")
    if not isinstance(target[key], list):
        die("Can't prepend value to tree since it's target is not type 'list'")
    if isinstance(value, list):
        target[key][0:0] = value
    else:
        target[key].insert(0, value)


def directive_interpolate(target: ConfigTree, key: Hashable, value: Any) -> None:
    tree_update_key(target, key, interpolate1(value))


def rpad(seq: list, length: int, padding: int | None = None) -> list:
    """Right pad a sequence to become at least `length` long with `padding` items.

    Post-condition ``len(rpad(seq, n)) >= n``.

    Example:

    >>> rpad([1], 3)
    [None, None, 1]

    """
    while True:
        pad_length = length - len(seq)
        if pad_length > 0:
            seq.insert(0, padding)
        else:
            break
    return seq


def tree_merge(target: ConfigTree, source: ConfigTree) -> None:
    """Merge the 'source' configuration tree into 'target'.

    Merging is done by adding values from 'source' to 'target' if they
    do not yet exist. Subtrees are merged recursively. In a second
    pass, special keys of the form "directive key" (i.e. separated by
    space) in 'target' are processed. Supported directives include
    "append" for adding values or lists to a list, and "interpolate"
    for replacing configuration variables.
    """
    if not isinstance(target, ConfigTree):
        die("Can't merge tree's since 'target' is not type 'csspin.tree.ConfigTree'")  # type: ignore[unreachable] # noqa: E501
    if not isinstance(source, ConfigTree):
        die("Can't merge tree's since 'source' is not type 'csspin.tree.ConfigTree'")  # type: ignore[unreachable] # noqa: E501

    if not hasattr(target, "_ConfigTree__schema") and hasattr(
        source, "_ConfigTree__schema"
    ):
        setattr(
            target,
            "_ConfigTree__schema",
            source._ConfigTree__schema,  # pylint: disable=protected-access
        )

    for key, value in source.items():
        if target.get(key, None) is None:
            try:
                target[key] = value
                tree_set_keyinfo(target, key, tree_keyinfo(source, key))
            except Exception:  # pylint: disable=broad-exception-caught
                debug(format_exc())
                die(f"Can't merge {value=} into '{target=}[{key=}]'")
        elif isinstance(value, ConfigTree):
            tree_merge(target[key], value)


def tree_apply_certain(tree: ConfigTree, keys: Iterable[str] | None = None) -> None:
    """Apply directives to ceratin keys

    :param target: The target tree
    :type target: ConfigTree
    :param keys: The keys, to which directives must be applied.
        Default value is None, what makes the function apply
        directives to all keys without exceptions. Alternatively,
        empty Iterable will result in not applying any directives.
    :type keys: Iterable[str] | None"""

    # Note that we need a list for the iteration, as we remove directive keys on
    # the fly.
    for clause, value in list(tree.items()):
        directive, key = rpad(clause.split(maxsplit=1), 2)
        if keys is not None and key not in keys:
            continue
        if fn := globals().get(f"directive_{directive}", None):
            fn(tree, key, value)
            del tree[clause]


def tree_apply_directives(tree: ConfigTree) -> None:
    """Recursively walking through the tree and processing directives"""

    tree_apply_certain(tree)

    for _, value, _, _, types, _, _ in tree_walk(tree):
        if isinstance(value, ConfigTree) and "internal" not in types:
            tree_apply_directives(value)


def tree_update(target: ConfigTree, source: ConfigTree, keep: str | tuple = ()) -> None:
    """This will *overwrite*, not fill up, like tree_merge.

    Key-Value pairs with origin global.yaml will not be updated.

    :param target: The target tree which is to be modified
    :type target: ConfigTree
    :param source: The tree containing the files to insert into the target tree
    :type source: ConfigTree
    :param keep: Ignore keys with KeyInfo.file equals values in ``keep``,
        defaults to ()
    :type keep: str | tuple, optional
    """

    if not isinstance(keep, (str, tuple)):
        raise TypeError("keep must be type 'str' or 'tuple'.")

    # import csspin.schema here to avoid cyclic import
    from csspin import schema  # pylint: disable=cyclic-import

    if (
        isinstance(keep, str) and (keep := (keep,))
    ) or "global.yaml" not in keep:  # pylint: disable=condition-evals-to-constant
        keep += ("global.yaml",)

    for key, value in source.items():
        ki = tree_keyinfo(source, key)
        if "internal" in tree_types(target, key) and tree_keyinfo(
            target, key
        ).file.removesuffix("_schema.yaml") != ki.file.removesuffix(".py"):
            # Ensure that only plugin defaults can override internal properties.
            die(f"Can't override internal property {key}")
        try:
            if isinstance(value, dict):
                if key not in target:
                    target[key] = ConfigTree()
                    tree_update(target[key], value, keep=keep)  # type: ignore[arg-type]
                    tree_set_keyinfo(target, key, ki)
                else:
                    tree_update(target[key], value, keep=keep)  # type: ignore[arg-type]
            elif key not in target or (
                (ki_file := tree_keyinfo(target, key).file)
                and all(pattern not in ki_file for pattern in keep)
            ):
                target[key] = value
                tree_set_keyinfo(target, key, ki)
        except (TypeError, schema.SchemaError) as exc:
            debug(format_exc())
            die(f"{ki.file}:{ki.line}: cannot assign '{value}' to '{key}': {exc}")


def tree_update_properties(
    cfg: ConfigTree,
    override_properties: Iterable[str] = (),
    prepend_properties: Iterable[str] = (),
    append_properties: Iterable[str] = (),
) -> None:
    """Modify the configuration tree, by overriding, prepending and
    appending settings to existing properties.

    Properties must be a tuple of strings in the format "some.key=new_value".
    """

    def modify_property(prop: str, func: Callable) -> None:
        """Modify a config tree value using given func"""
        try:
            fullname, value = prop.split("=", 1)
        except ValueError:
            debug(format_exc())
            die(f"Value assignment to {prop} invalid (hint: {prop}=foo)")

        path = list(fullname.split("."))
        scope = cfg
        while len(path) > 1:
            try:
                scope = getattr(scope, path.pop(0))
            except AttributeError:
                debug(format_exc())
                warn(f"Can't set unknown property '{fullname}' - skipping!")
                return
        if path[0] not in scope:
            warn(f"Can't set unknown property '{fullname}' - skipping!")
            return

        if "internal" in tree_types(scope, path[0]):
            die(f"Can't override internal property {prop}")

        func(scope, path[0], ruamel.yaml.YAML().load(interpolate1(value)))
        # Set the value source to "command-line"
        tree_set_keyinfo(scope, path[0], KeyInfo("command-line", "0"))

    # Update the configuration tree based on environment variables
    for prop in (
        f"{key.replace('SPIN_TREE_', '').replace('__', '.').lower()}={value}"
        for (key, value) in os.environ.items()
        if key.startswith("SPIN_TREE_")
    ):
        modify_property(prop, setattr)

    # Update the configuration tree based on passed -p, --pp and --ap
    for prop in override_properties:
        modify_property(prop, setattr)
    for prop in prepend_properties:
        modify_property(prop, directive_prepend)
    for prop in append_properties:
        modify_property(prop, directive_append)


# Variable references are names prefixed by '$' (like $port, $version,
# $name etc.)
RE_VAR = re.compile(r"\$(\w+)")


class YamlParser:
    def __init__(self: YamlParser, fn: str, facts: dict, variables: dict) -> None:
        self._facts = {
            "win32": sys.platform == "win32",
            "darwin": sys.platform == "darwin",
            "linux": sys.platform.startswith("linux"),
            "posix": os.name == "posix",
            "nt": os.name == "nt",
        }
        self._var = {}

        self._facts.update(facts)
        self._var.update(variables)
        self._fn = fn

    def parse_yaml(
        self: YamlParser,
        data: str | int | list | dict | ruamel.yaml.comments.CommentedKeyMap | None,
    ) -> ConfigTree | int | str | list | ruamel.yaml.comments.CommentedKeyMap | None:
        if isinstance(data, str):
            return self.parse_str(data)
        elif isinstance(data, list):
            return self.parse_list(data)
        elif isinstance(data, dict):
            return self.parse_dict(data)
        return data

    def parse_str(self: YamlParser, data: Any) -> str:
        def replacer(mo: re.Match) -> str:
            return self._var.get(mo.group(1))  # type: ignore[return-value]

        return RE_VAR.sub(replacer, data)

    def parse_list(self: YamlParser, data: Iterable) -> list:
        return [self.parse_yaml(x) for x in data]

    def parse_dict(
        self: YamlParser, data: ruamel.yaml.comments.CommentedKeyMap
    ) -> ConfigTree | None:
        if not data:
            data = {}
        config = ConfigTree(data)
        for key, value in data.items():
            key = self.parse_yaml(key)
            if " " in key:
                # This is a directive -- lookup the appropriate
                # handler to process it
                directive, expression = key.split(" ", 1)
                method = getattr(self, "directive_" + directive, self.parse_key)
                method(key, expression, value, config)
            else:
                self.parse_key(key, key, value, config)
            if hasattr(config, key):
                if isinstance(value, dict):
                    tree_set_parent(config[key], config, key)

                ki = KeyInfo(self._fn, data.lc.key(key)[0] + 1)
                tree_set_keyinfo(config, key, ki)

        # If parsing this dict resulted in a list (which can happen by
        # using e.g. if), the result has been stored under the magic
        # key '$' and we return that instead of the parsed dict.
        if "$" in config:
            config = config["$"]
        # if the config is empty, it should be replaced by None
        if len(config) == 0:
            config = None  # type: ignore[assignment]
        return config

    def directive_var(
        self: YamlParser,
        key: str,
        expression: str,
        value: ruamel.yaml.comments.CommentedKeyMap,
        out: ConfigTree,
    ) -> None:
        _value = self.parse_yaml(value)
        if isinstance(_value, int):
            # re.sub works with str only
            _value = str(_value)
        self._var[expression] = _value
        del out[key]

    def parse_key(
        self: YamlParser,
        key: str,
        expression: str,
        value: ruamel.yaml.comments.CommentedKeyMap,
        out: ConfigTree,
    ) -> None:
        _value = self.parse_yaml(value)
        if isinstance(_value, str):
            self._var[expression] = _value
        out[key] = _value


def parse_yaml(
    yaml_file: Any,
    fn: str,
    facts: dict | None = None,
    variables: dict | None = None,
) -> Any:
    facts = facts if facts else {}
    variables = variables if variables else {}
    yamlparser = YamlParser(fn, facts, variables)
    return yamlparser.parse_yaml(yaml_file)


def tree_extract_secrets(cfg: ConfigTree) -> set[str]:
    """Return a set of strings from ConfigTree whose descriptors are of type 'secret'"""
    secrets = set()
    exceptions = ("", None)  # Calling replace on these strings can brake the output

    for _, value, _, _, _, _, desc in tree_walk(cfg):
        if isinstance(desc, DESCRIPTOR_REGISTRY["secret"]):
            if value not in exceptions:
                secrets.add(str(value))

    return secrets


def tree_inherit_internal(cfg: ConfigTree, parent_internal: bool = False) -> None:
    """Walk through the tree and make all subtrees
    inherit parent's `internal` property"""
    INTERNAL_TYPE = "internal"

    for key, value in cfg.items():
        if not tree_get_descriptor(cfg, key):
            continue

        types = tree_types(cfg, key)
        internal = INTERNAL_TYPE in types

        if parent_internal and not internal:
            types.append(INTERNAL_TYPE)
            tree_set_types(cfg, key, types)

        if isinstance(value, ConfigTree):
            tree_inherit_internal(value, internal or parent_internal)


def tree_ensure_descriptors(cfg: ConfigTree) -> None:
    """Create descriptors for those elements of config tree,
    which are not defined in schema.yaml"""
    if not getattr(cfg, "_ConfigTree__schema", None):
        return

    for key, value in cfg.items():
        if not tree_get_descriptor(cfg, key):
            desc_name = type(value).__name__.lower()
            if desc_name not in DESCRIPTOR_REGISTRY:
                desc_name = "object"

            desc_type = DESCRIPTOR_REGISTRY[desc_name]
            tree_set_descriptor(cfg, key, desc_type, description={"type": [desc_name]})

        if isinstance(value, ConfigTree):
            tree_ensure_descriptors(value)
