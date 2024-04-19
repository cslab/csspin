# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#
# Disabling "union-attr" since inspect.currentframe() could return None, which
# is not the case for the implementation in this file.
# mypy: disable-error-code=union-attr

from __future__ import annotations

import inspect
import os
import re
import sys
from collections import OrderedDict, namedtuple
from typing import TYPE_CHECKING

import ruamel.yaml
import ruamel.yaml.comments

from spin import die, interpolate1  # pylint: disable=cyclic-import

if TYPE_CHECKING:
    from typing import Any, Generator, Hashable, Iterable

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
    'parent.subtree.prop'

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
        value = tree_typecheck(self, key, value)
        super().__setitem__(key, value)
        _set_callsite(self, key, 3, value)

    def setdefault(self: ConfigTree, key: Hashable, default: Any = None) -> Any:
        default = tree_typecheck(self, key, default)
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
            value = tree_typecheck(self, name, value)
            self[name] = value
            _set_callsite(self, name, 3, value)

    def __getattr__(self: ConfigTree, name: str) -> Any:
        if name in self:
            return self.get(name)
        raise AttributeError(f"No property '{name}'")


def tree_typecheck(tree: ConfigTree, key: Hashable, value: Any) -> Any:
    schema = getattr(tree, "_ConfigTree__schema", None)
    if schema:
        desc = schema.properties.get(key, None)
        if desc:
            value = desc.coerce(value)
    return value


def tree_update_key(tree: ConfigTree, key: Hashable, value: Any) -> None:
    OrderedDict.__setitem__(tree, key, value)  # type: ignore[assignment]


def _call_location(depth: int) -> KeyInfo:
    fn, lno, _, _, _ = inspect.getframeinfo(
        sys._getframe(depth)  # pylint: disable=protected-access
    )
    return KeyInfo(fn, lno)


def _set_callsite(tree: ConfigTree, key: Hashable, depth: int, value: Any) -> None:
    if hasattr(tree, "_ConfigTree__keyinfo"):
        # FIXME: Is that correct? The call location will always be this file and
        #        the following lines.
        # pylint: disable=protected-access
        tree._ConfigTree__keyinfo[key] = _call_location(depth)
    tree_set_parent(value, tree, key)  # type: ignore[arg-type]


def tree_set_keyinfo(tree: ConfigTree, key: Hashable, ki: KeyInfo) -> None:
    # FIXME: Do we need a warning or exception in case the following if
    #        statement does not pass?
    if hasattr(tree, "_ConfigTree__keyinfo"):
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
    return ".".join(path)


def tree_load(fn: str) -> ConfigTree | Any:
    yaml = ruamel.yaml.YAML()
    with open(fn, encoding="utf-8") as f:
        try:
            data = yaml.load(f)
        except ruamel.yaml.parser.ParserError as ex:
            die(f"\n{ex.problem_mark.name}:{ex.problem_mark.line+1}: {ex}")
    return parse_yaml(data, fn)


def tree_walk(config: ConfigTree, indent: str = "") -> Generator:
    """Walk configuration tree depth-first, yielding the key, its value,
    the full name of the key, the tracking information and an
    indentation string that increases by ``" "`` for each level.
    """
    for key, value in config.items():
        yield key, value, tree_keyname(config, key), tree_keyinfo(config, key), indent
        if isinstance(value, ConfigTree):
            for key, value, fullname, info, subindent in tree_walk(
                value, indent + "  "
            ):
                yield key, value, fullname, info, subindent


def tree_dump(tree: ConfigTree) -> str:
    text = []

    def write(line: str) -> None:
        text.append(line)

    cwd = os.getcwd()
    home = os.path.expanduser("~")

    def shorten_filename(fn: str) -> str:
        if fn.startswith(cwd):
            return fn[len(cwd) + 1 :]  # noqa: E203
        if fn.startswith(home):
            return f"~{fn[len(home):]}"
        return fn

    tagcolumn = max(
        (
            len(f"{shorten_filename(info.file)}:{info.line}:")
            for _, _, _, info, _ in tree_walk(tree)
        ),
        default=0,
    )
    separator = "|"
    for key, value, _fullname, info, indent in tree_walk(tree):
        tag = f"{shorten_filename(info.file)}:{info.line}:"
        space = (tagcolumn - len(tag) + 1) * " "
        if isinstance(value, list):
            if value:
                write(f"{tag}{space}{separator}{indent}{key}:")
                blank_location = len(f"{tag}{space}") * " "
                for item in value:
                    write(f"{blank_location}{separator}{indent}  - {repr(item)}")
            else:
                write(f"{tag}{space}{separator}{indent}{key}: []")
        elif isinstance(value, dict):
            if value:
                # FIXME: Shouldn't the value be shown like for lists?
                write(f"{tag}{space}{separator}{indent}{key}:")
            else:
                write(f"{tag}{space}{separator}{indent}{key}: {{}}")
        else:
            write(f"{tag}{space}{separator}{indent}{key}: {repr(value)}")
    return "\n".join(text)


def directive_append(target: ConfigTree, key: Hashable, value: Any) -> None:
    if key not in target:
        die(f"{key=} not in passed target tree.")
    if not isinstance(target[key], list):
        die(f"Can't append {value=} to tree since {target[key]=} is not type 'list'")
    if isinstance(value, list):
        target[key].extend(value)
    else:
        target[key].append(value)


def directive_prepend(target: ConfigTree, key: Hashable, value: Any) -> None:
    if key not in target:
        die(f"{key=} not in passed target tree.")
    if not isinstance(target[key], list):
        die(f"Can't prepend {value=} to tree since {target[key]=} is not type 'list'")
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
        die("Can't merge tree's since 'target' is not type 'spin.tree.ConfigTree'")  # type: ignore[unreachable] # noqa: E501
    if not isinstance(source, ConfigTree):
        die("Can't merge tree's since 'source' is not type 'spin.tree.ConfigTree'")  # type: ignore[unreachable] # noqa: E501

    for key, value in source.items():
        if target.get(key, None) is None:
            try:
                target[key] = value
                tree_set_keyinfo(target, key, tree_keyinfo(source, key))
            except Exception:  # pylint: disable=broad-exception-caught
                die(f"Can't merge {value=} into '{target=}[{key=}]'")
        elif isinstance(value, ConfigTree):
            tree_merge(target[key], value)
    # Pass 2: process directives. Note that we need a list for the
    # iteration, as we remove directive keys on the fly.
    for clause, value in list(target.items()):
        directive, key = rpad(clause.split(maxsplit=1), 2)
        fn = globals().get(f"directive_{directive}", None)
        if fn:
            fn(target, key, value)
            del target[clause]


def tree_update(target: ConfigTree, source: ConfigTree) -> None:
    # This will *overwrite*, not fill up, like tree_merge.
    # (import here to avoid cyclic import)
    from spin import schema  # pylint: disable=cyclic-import

    for key, value in source.items():
        ki = tree_keyinfo(source, key)
        try:
            if isinstance(value, dict):
                if key not in target:
                    target[key] = ConfigTree()
                    tree_update(target[key], value)  # type: ignore[arg-type]
                    tree_set_keyinfo(target, key, ki)
                else:
                    tree_update(target[key], value)  # type: ignore[arg-type]
            else:
                target[key] = value
                tree_set_keyinfo(target, key, ki)
        except (TypeError, schema.SchemaError) as exc:
            # FIXME: Is it even possible to trigger the schema.SchemaError?
            die(f"{ki.file}:{ki.line}: cannot assign '{value}' to '{key}': {exc}")


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

    def directive_if(
        self: YamlParser,
        key: str,
        expression: str,
        value: ruamel.yaml.comments.CommentedKeyMap,
        out: ConfigTree,
    ) -> None:
        if eval(expression, self._facts):
            # We have to take care to not evaluate clauses
            # for falsy if statements -- thus
            # 'parse_yaml(v)' below, only when the
            # expression was true.
            _value = self.parse_yaml(value)
            if isinstance(_value, list):
                listout = out.setdefault("$", [])
                listout.extend(_value)
            elif isinstance(_value, dict):
                for ifk, ifv in _value.items():
                    out[ifk] = ifv
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
