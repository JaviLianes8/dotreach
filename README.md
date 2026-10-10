# dotreach

Typed, zero-dependency get/set/delete/has on nested dicts and lists by dotted path.

## Install

```
pip install dotreach
```

## Usage

```python
import dotreach

data = {"user": {"name": "Ada", "roles": ["admin", "editor"]}}

dotreach.get(data, "user.name")            # "Ada"
dotreach.get(data, "user.roles.0")         # "admin"  (integers index sequences)
dotreach.get(data, "user.roles.-1")        # "editor" (negative indices work)
dotreach.get(data, "user.age", default=0)  # 0        (no default: raises KeyError)

dotreach.has(data, "user.roles.1")         # True

dotreach.set(data, "user.age", 36)         # missing dict keys are created
dotreach.set(data, "user.roles.0", "owner")

dotreach.delete(data, "user.roles.1")
dotreach.delete(data, "user.nope", missing_ok=True)
```

Mapping segments are always treated as keys and sequence segments as integer
indices, so there is no ambiguity: `get({"0": "x"}, "0")` returns `"x"`, while
`get(["x"], "0")` returns the first element. Strings and bytes are never indexed
into. Need a different delimiter? Pass `sep`:

```python
dotreach.get({"a": {"b": 1}}, "a/b", sep="/")  # 1
```

## Why

Reaching into JSON-shaped data by a single string path is a common need, but the
existing options all ask for a compromise:

- `glom` is powerful but heavy: it pulls in `boltons`, `attrs` and `face`, and its
  spec language is far more than a dotted lookup.
- `python-benedict` wraps every dict and drags a large dependency tree (slugify,
  requests, and more under its extras) for what is often a one-line need.
- `dpath` is dependency-free but path-oriented in a clunky way: slash-and-glob
  paths and a search-style API rather than a plain `get(obj, "a.b.0.c", default)`.
- `dotty_dict` and `scalpl` take the wrapper-object route and have not shipped a
  release since 2022 and 2021 respectively.

`dotreach` is the small, maintained middle: four plain functions, full type hints
checked under `mypy --strict`, ships `py.typed`, no runtime dependencies, and one
unambiguous rule for how a segment is read. Reach for it when you want dotted-path
access to nested data and nothing else.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
