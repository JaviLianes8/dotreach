# dotreach 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to dotreach. PyPI has 0.1.0; `main` holds the
unreleased 0.2.0 improvement round, so everything since 0.1.0 ships in 1.0.0.

Progress:
- [x] Branch `release/1.0.0` created from `main` (unreleased 0.2.0, 73081b0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: RFC 6901 fetched live, glom, jmespath and PyPI 0.1.0 as oracles (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.1.0, every Python (items 8, 10, 13, 14)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Gates (item 15), final run
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.2.0 (before any change)

Fresh clone of `main` (73081b0) on Elena's PC, CPython 3.14.2: `ruff format --check .`,
`ruff check .` and `mypy --strict src tests` exit 0; `pytest` 127 passed; no doctests ran.

Defects found in 0.2.0 by reading and then reproducing:

- `walk`, `leaves`, `flatten`, `glob`, `set_copy` and `delete_copy` recursed, so a structure
  or path a few thousand levels deep raised `RecursionError`.
- `glob` with several `**` segments re-explored the same nodes once per way of splitting the
  depth between them: 40 `**` over a 60-level chain did not finish.
- A segment of more than 4300 digits crashed with a bare `ValueError` from `int()`.
- Error messages quoted the whole path, so a 1 MB path produced a 1 MB message.
- `flatten` and `glob` collisions and cycles raised a plain `ValueError`, not a typed error.
- `set` silently replaced a tuple held in a dict with a new dict (data loss), but raised on a
  number held in a list; `delete` reported a value held in a tuple as not found.
- With `escape=True`, a separator containing a backslash made paths ambiguous.
- The command printed a traceback for input nested too deeply for `json`, and on a closed
  output pipe; `--indent -1` was accepted.
- README: the custom separator example was wrong (`get({"a/b": 1}, "a/b", sep="/")` raises),
  and its links were relative, which break on PyPI.

## API review (item 1)

Kept: the 23 public names of 0.2.0 with their signatures and defaults, and the four 0.1.0
functions with theirs. Added `StructureError` (24 names). Behaviour changes for 1.0.0, all in
CHANGELOG and the GUIDE: one write rule for `set` (non-containers replaced wherever they sit,
read-only containers refused, `set_copy` rebuilds them); read-only containers refused by
`delete`/`pop`; `StructureError` for cycles and render collisions; bounded messages; backslash
separators refused when escaping; `join_path` refuses non-`str`/`int` segments; errors show and
pickle as `dotreach.<Name>`; `unflatten` typed `dict[str, Any]` for string paths and
`dict[Any, Any]` otherwise; CLI `--indent` limited to 0..64, deep input and closed pipes handled.

## Ground truth (item 7)

- RFC 6901, fetched from https://www.rfc-editor.org/rfc/rfc6901.txt on 2026-10-16 (13037 bytes,
  sha256 in `tests/upstream/MANIFEST.json`, re-fetched by `scripts/fetch_upstream.py`, never
  committed). `tests/test_rfc6901.py` parses the example document and both example tables
  (JSON string and URI fragment forms, 22 pointers) out of the fetched text, decodes each pointer
  as the RFC says, and requires `get`, `has`, escaped string paths, `flatten` and `unflatten` to
  agree. Documented differences: leading zeros and negative indices accepted, no whole-document
  path.
- glom 25.12.0 and jmespath 1.1.0 (installed in a throwaway venv, never dependencies) as
  independent oracles in `tests/test_oracles.py`: 300 seeded random documents, over 2000 exact
  paths compared with `glom.Path`, plain string paths with `glom`'s own parser, every leaf and
  its negative-index form with jmespath, and over 500 one-level wildcards against jmespath
  projections. Differences found and documented: glom indexes into strings and its `int()`
  accepts `" 0"`, `"+1"` and `"1_0"`; jmespath projections drop nulls.
- PyPI 0.1.0 as an oracle (`tests/test_upgrade.py`, `DOTREACH_V01`): `get`, `has`, `set` and
  `delete` on 400 seeded documents and over 3000 string paths give the same results and the
  same built-in error families, except the documented `set` change (a non-container inside a
  list is now replaced instead of raising `TypeError`), which the test checks case by case.
- Python's own item access (`functools.reduce(operator.getitem)`) as the oracle in the seeded
  property tests (`tests/test_fuzz.py`).

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: 500 seeded random documents per property (leaf read-back by segments
and escaped string, flatten/unflatten round trip, `set_copy` equals `set` on a deep copy and
never mutates, `delete_copy` equals `delete`, `**` finds every leaf, split/join inverses for
six separators, random text paths raise only `DotreachError` with messages under 300
characters). `tests/test_hostile.py`: 100,000-level dict and list chains through every
function in under 10 s each, 40 `**` in one pattern, shared subtrees, cycles, 100,000-digit
indices, 1 MB paths and keys (messages under 200 characters), JSON nested 200,000 deep through
the command, a closed output pipe through a real subprocess.

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Wheel and sdist built from a clean clone at 154f05a: `twine check --strict` passes on both.
  Wheel: the 12 modules, `py.typed`, LICENSE, entry point. Sdist: `src`, every test, the RFC
  manifest (not the RFC), the fetch script, README, GUIDE, CHANGELOG, CONTRIBUTING, LICENSE,
  `requirements-dev.txt`; no notes, reports or caches.
- `tests/test_e2e.py` builds the wheel, installs it in a fresh venv and drives the installed
  `dotreach` script by subprocess (files, stdin, `-i`, pipes, `--version`, `--help`). With
  `DOTREACH_E2E_PYPI=1` it installs 0.1.0 from PyPI into a venv, checks it, upgrades it in
  place to the built wheel and checks the library and the script again: passed on Elena's PC.
- The suite (doctests and e2e aside, which need `src`) run from the extracted sdist with `src`
  removed, so it imports the installed wheel, with the RFC, glom, jmespath and 0.1.0 oracles
  present: 169 passed, none skipped, on CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and
  3.14.2 free-threaded (every interpreter on this PC from `requires-python` up).

## Author mutation round (item 18)

46 mutants over every module, each applied alone to a fresh clone of the pushed branch on
Elena's PC, suite (oracles included) run with `-x` and a 900 s limit. 38 killed at once; M05,
M41 and M42 survived and got contracts in a4cd9f6, then were confirmed killed; M36, M44, M45
were rerun at a4cd9f6 (a malformed mutant and one wheel build error in the first run); M01,
M27 and M46 are argued equivalent.

| Mutant | Module | Change | Killed by |
| --- | --- | --- | --- |
| M01 | `_path.py` | bool segment accepted as index | equivalent: `bool` segments are refused by path parsing before any index is read |
| M02 | `_path.py` | negative text indices dropped | `_core.py::dotreach._core.get` |
| M03 | `_path.py` | isdigit instead of isdecimal | `test_contract_edges.py::test_index_rule_is_decimal_text_with_an_optional_minus` |
| M04 | `_path.py` | huge digit guard removed | `test_hostile.py::test_huge_numbers_as_indices_are_simply_out_of_range` |
| M05 | `_path.py` | huge negative sign lost | survived round 1; killed by `test_hostile.py::test_huge_numbers_as_indices_are_simply_out_of_range` |
| M06 | `_path.py` | escaped backslash not honoured | `test_contract.py::test_path_helpers_round_trip` |
| M07 | `_path.py` | multi-char separator advance off | `test_fuzz.py::test_split_inverts_join_for_random_segments[::]` |
| M08 | `_path.py` | backslash separator accepted | `test_contract_edges.py::test_a_separator_with_a_backslash_is_refused_only_when_escaping` |
| M09 | `_path.py` | bool segment accepted in path | `test_contract_edges.py::test_join_path_takes_only_str_and_int_segments` |
| M10 | `_path.py` | strings indexed into | `_walk.py::dotreach._walk.flatten` |
| M11 | `_path.py` | out of range resolves | `test_cli.py::test_has_uses_the_exit_code` |
| M12 | `_errors.py` | message bound lifted | `test_contract_edges.py::test_message_quotes_are_bounded_but_attributes_are_whole` |
| M13 | `_errors.py` | KeyError args not the path | `__init__.py::dotreach.PathNotFoundError` |
| M14 | `_errors.py` | StructureError not a ValueError | `test_contract_edges.py::test_structure_error_is_a_value_error_for_collisions_and_cycles` |
| M15 | `_core.py` | get returns sentinel instead of raising | `__init__.py::dotreach.DotreachError` |
| M16 | `_core.py` | bool accepted as int | `test_contract.py::test_get_as_contract` |
| M17 | `_core.py` | get_as missing returns sentinel | `test_contract.py::test_get_as_contract` |
| M18 | `_write.py` | negative next segment builds list | `test_write.py::test_set_create_lists_negative_next_segment_makes_a_dict` |
| M19 | `_write.py` | append without create_lists | `test_fuzz.py::test_set_copy_equals_set_on_a_deep_copy_and_never_mutates` |
| M20 | `_write.py` | negative write index refused | `test_upgrade.py::test_the_four_original_functions_behave_as_in_0_1` |
| M21 | `_write.py` | tuple replaced again | `test_contract_edges.py::test_set_and_set_copy_follow_one_rule_for_values_on_the_path` |
| M22 | `_write.py` | fresh container from wrong segment | `_walk.py::dotreach._walk.unflatten` |
| M23 | `_delete.py` | delete read-only not refused | `test_contract_edges.py::test_delete_names_read_only_containers_even_with_missing_ok` |
| M24 | `_delete.py` | missing_ok inverted | `_delete.py::dotreach._delete.delete` |
| M25 | `_delete.py` | delete index zero missed | `_delete.py::dotreach._delete.pop` |
| M26 | `_copy.py` | named tuple length change kept | `test_regressions.py::test_named_tuple_length_change_becomes_plain_tuple` |
| M27 | `_copy.py` | set_copy negative index raw | equivalent: a negative index addresses the same slot in list and tuple assignment |
| M28 | `_copy.py` | set_copy appends without create_lists | `test_fuzz.py::test_set_copy_equals_set_on_a_deep_copy_and_never_mutates` |
| M29 | `_copy.py` | delete_copy missing returns a copy | `test_copy_walk.py::test_delete_copy_on_lists_tuples_and_missing` |
| M30 | `_walk.py` | empty containers not leaves | `_walk.py::dotreach._walk.walk` |
| M31 | `_walk.py` | walk cycle check removed | suite hangs in `test_copy_walk.py::test_walk_rejects_cycles` (900 s limit) |
| M32 | `_walk.py` | shared subtree taken as cycle | `test_copy_walk.py::test_shared_subtrees_are_not_cycles` |
| M33 | `_walk.py` | flatten collision ignored | `__init__.py::dotreach.StructureError` |
| M34 | `_walk.py` | unflatten shares empty containers | `test_regressions.py::test_unflatten_never_shares_empty_containers_with_the_input` |
| M35 | `_walk.py` | unflatten duplicate leaf allowed | `test_copy_walk.py::test_unflatten_conflicts` |
| M36 | `_glob.py` | double star needs a level | `test_contract.py::test_glob_contract` (round 1 run had a malformed mutant; rerun) |
| M37 | `_glob.py` | glob keeps negative index | `test_contract.py::test_glob_contract` |
| M38 | `_glob.py` | glob memo removed | suite hangs in `test_hostile.py::test_many_double_stars_do_not_multiply_the_work` (900 s limit) |
| M39 | `_glob.py` | glob cycle check removed | `test_contract_edges.py::test_structure_error_is_a_value_error_for_collisions_and_cycles` |
| M40 | `_glob.py` | glob collision ignored | `test_regressions.py::test_glob_refuses_colliding_render` |
| M41 | `_commands.py` | windows closed pipe reported | survived round 1; killed by `test_cli.py::test_a_reader_that_went_away_ends_quietly[22]` |
| M42 | `_commands.py` | raw prints non-strings | survived round 1; killed by `test_cli.py::test_get_prints_json_and_raw` |
| M43 | `_commands.py` | has always 0 | `test_cli.py::test_has_uses_the_exit_code` |
| M44 | `_commands.py` | deep input traceback | `test_hostile.py::test_the_command_reports_input_nested_too_deeply` (rerun; round 1 stopped on a wheel build error) |
| M45 | `_cli.py` | indent unchecked | `test_hostile.py::test_the_command_refuses_an_unusable_indent[-1]` (rerun) |
| M46 | `_cli.py` | pipe flush not silenced | equivalent on Windows: the failed write drops the buffer, so the exit flush has nothing left (subprocess test exits 1 quietly either way) |

## QA lenses (item 19)

Pending.

## Gates (item 15)

Pending final run.
