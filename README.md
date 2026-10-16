# dotreach

Typed, zero-dependency access to nested dicts and lists by dotted path: get, set,
delete, has, pop, flatten, unflatten, wildcard matching, non-mutating updates, and a
`dotreach` command for JSON on the shell.

## Install

```
pip install dotreach
```

Python 3.10 or newer, no runtime dependencies.

## Usage

```python
import dotreach

data = {"user": {"name": "Ada", "roles": ["admin", "editor"]}}

dotreach.get(data, "user.name")            # 'Ada'
dotreach.get(data, "user.roles.0")         # 'admin'  (integers index sequences)
dotreach.get(data, "user.roles.-1")        # 'editor' (negative indices work)
dotreach.get(data, "user.age", default=0)  # 0        (no default: PathNotFoundError)
dotreach.has(data, "user.roles.1")         # True

dotreach.set(data, "user.age", 36)  # missing dict keys are created
dotreach.set(data, "user.roles.0", "owner")
dotreach.delete(data, "user.roles.1")
dotreach.delete(data, "user.nope", missing_ok=True)
data                                # {'user': {'name': 'Ada', 'roles': ['owner'], 'age': 36}}
```

Mapping segments are always keys and sequence segments are integer indices, so there
is no ambiguity: `get({"0": "x"}, "0")` returns `"x"`, while `get(["x"], "0")` returns
the first element. Strings and bytes are never indexed into.

### Paths

A path is a dotted string or a sequence of segments. Sequences take exact keys, so
they reach keys that contain dots and non-string keys:

```python
dotreach.get({"a.b": {1: "x"}}, ("a.b", 1))     # 'x'
dotreach.get({"a": {"b": 1}}, "a/b", sep="/")   # 1 (custom separator)
dotreach.get({"a.b": 1}, r"a\.b", escape=True)  # 1 (backslash escapes the separator)
dotreach.join_path(["files", "report.pdf"])     # 'files.report\\.pdf'
dotreach.split_path(r"files.report\.pdf")       # ['files', 'report.pdf']
```

### More operations

```python
cfg = {"server": {"port": 8080}}
port: int = dotreach.get_as(cfg, "server.port", int)  # 8080, checked and typed for mypy
dotreach.pop(data, "user.age")                        # 36 (removed and returned)
dotreach.setdefault(data, "user.prefs.theme", "dark") # 'dark'

dotreach.set({}, "tags.0.name", "x", create_lists=True)  # {'tags': [{'name': 'x'}]}

dotreach.set_copy(data, "user.name", "Lin")["user"]["name"]  # 'Lin', data is untouched
dotreach.delete_copy((1, (2, 3)), "1.0")                     # (1, (3,)), tuples work too

dotreach.flatten({"db": {"host": "x", "ports": [5432]}})
# {'db.host': 'x', 'db.ports.0': 5432}
dotreach.unflatten({"db.host": "x", "db.ports.0": 5432}, create_lists=True)
# {'db': {'host': 'x', 'ports': [5432]}}
dotreach.glob({"users": [{"name": "Ada"}, {"name": "Lin"}]}, "users.*.name")
# {'users.0.name': 'Ada', 'users.1.name': 'Lin'}
```

`walk` and `leaves` iterate every leaf path lazily, at any depth. Errors are typed
`DotreachError`s naming the path, the failing segment and its position, and each one
also subclasses a built-in error (`KeyError`, `TypeError`, `IndexError`,
`ValueError`), so the `except` clauses written for the 0.1 release keep working.

See the [guide](https://github.com/JaviLianes8/dotreach/blob/main/GUIDE.md) for every
function, option and rule, and the
[changelog](https://github.com/JaviLianes8/dotreach/blob/main/CHANGELOG.md) for what
changed in 1.0.0.

## Command line

With `data.json` holding `{"user": {"name": "Ada", "roles": ["admin", "editor"]}}`:

```
dotreach get user.name data.json              "Ada"
dotreach get user.name --raw data.json        Ada
dotreach has user.roles.0 data.json           exit 0 if present, 1 if not
dotreach set user.age 36 -i data.json         edit the file in place
dotreach delete user.roles.-1 data.json
dotreach glob 'user.*' data.json
dotreach flatten data.json | dotreach unflatten --create-lists
curl -s https://example.com/api | dotreach get items.0.id
```

Input is a file or standard input; output is JSON on stdout; errors go to stderr with
exit code 1. Run `dotreach --help` for every option.

## Why

Reaching into JSON-shaped data by a single string path is a common need. The existing
options, as published on PyPI:

- `glom` is powerful but heavier than a lookup: it depends on `boltons`, `attrs` and
  `face`, and its spec language goes far beyond dotted paths.
- `python-benedict` wraps dicts in its own class and depends on `python-slugify` and
  `typing_extensions`, with many more packages behind its extras.
- `dpath` is dependency-free and has globbing, but uses slash-separated paths and a
  search-oriented API rather than a plain `get(obj, "a.b.0.c", default)`.
- `dotty_dict` and `scalpl` take the wrapper-object route; their latest releases
  date from 2022 and 2021.

`dotreach` is the small middle: plain functions over your own dicts and lists, full type
hints checked under `mypy --strict`, `py.typed`, no runtime dependencies, one
unambiguous rule for how a segment is read, and a CLI for the same operations.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/dotreach/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
