# Graph Report - gghf  (2026-06-04)

## Corpus Check
- 11 files · ~4,432 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 165 nodes · 276 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 55 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6a4912d2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 14|Community 14]]

## God Nodes (most connected - your core abstractions)
1. `Database` - 33 edges
2. `Config` - 27 edges
3. `StorageManager` - 27 edges
4. `gghf Core Implementation Plan` - 17 edges
5. `Path` - 12 edges
6. `Path` - 12 edges
7. `Path` - 11 edges
8. `TestConfigDefaults` - 8 edges
9. `str` - 8 edges
10. `str` - 8 edges

## Surprising Connections (you probably didn't know these)
- `TestConfigDefaults` --uses--> `Config`  [INFERRED]
  tests/test_config.py → src/gghf/config.py
- `TestConfigFromToml` --uses--> `Config`  [INFERRED]
  tests/test_config.py → src/gghf/config.py
- `TestConfigSaveAndReload` --uses--> `Config`  [INFERRED]
  tests/test_config.py → src/gghf/config.py
- `TestConfigEnvOverride` --uses--> `Config`  [INFERRED]
  tests/test_config.py → src/gghf/config.py
- `TestDatabaseCreate` --uses--> `Database`  [INFERRED]
  tests/test_database.py → src/gghf/database.py

## Communities (11 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (18): Config, Manage gghf configuration stored as TOML.      Defaults are read from a config f, Load TOML config from disk., Root directory for HF repos and GGUF artifacts., Root directory for cached Hugging Face repositories., Root directory for generated GGUF files., Hugging Face access token., Directory for gghf configuration files. (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (15): Database, SQLite database for tracking Hugging Face models and their state., Manage a SQLite database for tracked models., Return model list with total disk usage per repo., Close the database connection., Create tables if they don't exist., Return all tracked models as a list of dicts., Path (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.47
Nodes (5): Context, callback(), main(), _main_menu(), Launch the interactive gghf menu.

### Community 3 - "Community 3"
Cohesion: 0.50
Nodes (4): _gghf_cmd(), Test that gghf --help exits with code 0 and mentions 'gghf' in output., Return the path to the gghf CLI, falling back to python -m., test_help_shows_gghf()

### Community 4 - "Community 4"
Cohesion: 0.22
Nodes (8): Filesystem helpers for storage path resolution, directory creation, and backups., Manage storage paths, directory creation, and GGUF backups., StorageManager, Path, TestStorageManagerCreateBackup, TestStorageManagerEnsureDirectories, TestStorageManagerGetModelStatus, TestStorageManagerPaths

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (10): Resolve the path for a cached HF repository., Resolve the root path for a model's GGUF artifacts., Resolve the path of the current GGUF file., Resolve the backups directory for a model., Create all directories needed for a model's HF cache and GGUF output., Copy current.gguf to backups/ with a timestamp suffix.          Raises FileNotFo, Return a summary dict for a model including sizes and existence flags., Normalise a repo_id into a safe directory name (org/repo). (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (10): bool, Remove a tracked model and its provenance records., Record a GGUF conversion event., Return all provenance records for a repo, newest first., Add a new tracked model., Return a dict for the given repo_id, or None., Update the HF commit hash and the updated_at timestamp., Update the status of a tracked model. (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (17): gghf Core Implementation Plan, Task 10: Model Status and Rich Tables, Task 11: Interactive TUI — Menu System, Task 12: Direct CLI Commands, Task 13: Private Repository Support, Task 14: Storage Warning Before Conversion, Task 15: Integration Tests and End-to-End Smoke Test, Task 16: Packaging and Installation Verification (+9 more)

## Knowledge Gaps
- **22 isolated node(s):** `Context`, `str`, `Path`, `bool`, `int` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 1` to `Community 6`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `StorageManager` connect `Community 4` to `Community 5`, `Community 7`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `Database` (e.g. with `Path` and `TestDatabaseAddModel`) actually correct?**
  _`Database` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Config` (e.g. with `TestConfigDefaults` and `.test_default_config_dir()`) actually correct?**
  _`Config` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `StorageManager` (e.g. with `Path` and `TestStorageManagerCreateBackup`) actually correct?**
  _`StorageManager` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Return the path to the gghf CLI, falling back to python -m.`, `Test that gghf --help exits with code 0 and mentions 'gghf' in output.`, `Context` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08780487804878048 - nodes in this community are weakly interconnected._