# dotreach improvement round

A ranked list of substantial, coherent improvements, written for the unreleased 0.2.0
round. Every item was additive at the time; the 1.0.0 release later changed a few
behaviours on purpose, listed in CHANGELOG.md.

## Starting point

0.1 offered four functions over dotted string paths: `get` (with default or
`KeyError`), `set` (auto-creating intermediate dicts), `delete` (with `missing_ok`) and
`has`, plus a custom `sep`. There was no way to reach a key that contains the
separator or a non-string key, errors did not say which segment failed, lists could
not be grown, nothing iterated or reshaped the data, there was no non-mutating write,
no typed read, and no command line entry point.

## Ranked improvements

1. **Typed errors that name the failing segment.** `DotreachError` with
   `PathNotFoundError` (`KeyError`), `PathTypeError` (`TypeError`), `PathIndexError`
   (`IndexError`) and `InvalidPathError` (`ValueError`). Each carries `.path`,
   `.segment` and `.position` and a readable message. `PathNotFoundError.args[0]`
   stays the path, exactly like the old bare `KeyError(path)`.
2. **Complete path syntax.** Sequence paths (`("a.b", 0)`) reach keys with dots and
   `int` keys with zero ambiguity. Opt-in backslash escaping (`escape=True`) for
   string paths, with `split_path` / `join_path` as exact inverses. Opt-in so that a
   0.1 path containing a backslash keeps its meaning.
3. **Growing lists on write.** `create_lists=True` on `set` makes missing
   intermediates lists when the next segment is an index, and appends at `len`.
   Off by default to keep 0.1 behaviour (`set({}, "a.0", 1)` still gives a dict).
4. **Non-mutating writes.** `set_copy` and `delete_copy` copy only the containers on
   the path (structural sharing), never touch the input, and work through tuples,
   named tuples and read-only mappings that in-place writes cannot enter.
5. **Leaf iteration, flatten and unflatten.** `walk` (lossless segment tuples),
   `leaves` (string paths), `flatten` (refuses silent key collisions) and `unflatten`
   (refuses conflicting paths, optional list rebuilding). Empty containers are leaves
   so JSON round-trips exactly. Self-containing structures raise instead of
   recursing forever.
6. **Wildcards.** `glob` with `*` (one level) and `**` (any depth), returning concrete
   paths, which is what you need for "every user's email" queries.
7. **Typed and dict-style helpers.** `get_as(obj, path, int)` checks the type and is
   typed `T` for the checker (with overloads for the default). `pop` and `setdefault`
   mirror the `dict` methods for nested data.
8. **A real CLI.** `dotreach get|has|set|delete|glob|flatten|unflatten` over JSON from
   a file or stdin, with `--raw`, `--default`, `--string`, `-i` in place,
   `--create-lists`, `--sep`, `--escape`, `--indent`, runnable examples in `--help`,
   errors on stderr with exit 1, and `has` usable in shell conditionals.
9. **Bug fix.** A segment of non-decimal digit characters (for example `"²"`) crashed
   with `ValueError` on a list; it now simply does not resolve.
10. **Documentation and proof.** Docstrings with examples on every public function, a
    `GUIDE.md` covering every rule, a contract test over the whole public promise, and
    an end to end test that builds the wheel, installs it into a fresh virtual
    environment and drives the installed `dotreach` script.

## Considered and left out

- Attribute access on arbitrary objects: blurs the one rule for how a segment is read.
- Implicit escaping by default: would change the meaning of existing paths.
- Slices and filter expressions: that is a query language, which `glom` and
  `jmespath` already cover well; `glob` covers the common wildcard need.
