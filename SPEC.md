# Project Specification

## Goal

Test that Spec-Gate can create a tiny Python feature and verify it with pytest.

## Tasks

- [x] Create greeting utility: Inside the configured work directory, create `specgate_demo.py` with a function `build_greeting(name: str) -> str` that returns `Hello, {name}!`. Also create `test_specgate_demo.py` with a pytest test that verifies `build_greeting("Ada")` returns `Hello, Ada!`.
- [x] Add excited greeting utility: Inside the configured work directory, update `specgate_demo.py` with a function `build_excited_greeting(name: str) -> str` that returns `Hello, {name}!!!`. Also create or update `test_specgate_demo.py` with pytest tests for both `build_greeting("Ada")` returning `Hello, Ada!` and `build_excited_greeting("Ada")` returning `Hello, Ada!!!`.
- [x] Add polite greeting utility: Inside the configured work directory, update `specgate_demo.py` with a function `build_polite_greeting(name: str) -> str` that returns `Good day, {name}.`. Also update `test_specgate_demo.py` with a pytest test that verifies `build_polite_greeting("Ada")` returns `Good day, Ada.`.

