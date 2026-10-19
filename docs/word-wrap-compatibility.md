# Commit-message word-wrap compatibility

This JavaScript dependency is used by `cz-conventional-changelog` 1.2.0 to format
developer commit messages. It is separate from the Python Kipp package and its
dependency modernization/publication. The dependency PR retains word-wrap
1.2.2 -> 1.2.4, with Python source/requirements and existing Python CI unchanged
from master `9d984b5e4397a93059205165606870fa4ad89e48`.

The adapter explicitly requests width 100, empty indent, newline and trim. Its
normal messages, scopes, header limit, body/footer bytes and prompt choices are
covered with the real adapter and an in-memory prompt; no Git commit occurs.
The upstream default indent changes from two spaces to empty, but this caller's
explicit indent preserves its output. Raw default behavior is tested explicitly.

The old trailing-space regex can block on spaces followed by a nonbreaking
space. The initial 120,000-space fixture exceeded a two-second child-process
bound under both tested Nodes; the new dependency completed and retained the
exact bytes. The persistent regression uses 500,000 spaces to keep the negative
control decisive on faster CI machines, with the same two-second process bound,
bounded output and exact complete-message byte/hash assertions. The ordinary
whitespace control passes both graphs. This is bounded regression acceptance,
not an unbounded performance guarantee or a rewrite of commit content.

The original graph passes 13 controls and fails only that regression; candidate
passes all 14. CI checks the expected old failure rather than ignoring errors.
Frozen Yarn 1.22.22 installs disable lifecycle scripts and verify both manifests
remain unchanged. Node 22 and 24 are the qualified test runtimes.

Toolchain caveat: both dependency manifests declare Node >=0.10.0, but 1.2.4
contains ES2015 `let`/`const`/arrow syntax. Parsing confirms the old source is
ES5-compatible while the candidate requires ES2015 syntax. Do not infer legacy
Node support from that stale engine declaration; no minimum-runtime promise is
added to Kipp. Old Node versions, interactive terminals, Python release/runtime
acceptance and publication are outside these JavaScript checks.

Run `node --test tests/js/word-wrap.test.cjs` after the frozen install. The root
`npm test` remains an inherited failing placeholder; it is not claimed as a
passing suite. Source rollback is this dev-tool/test change; no runtime data,
credentials, publication, security settings or package release is involved.
