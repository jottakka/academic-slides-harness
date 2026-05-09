# Planning, Execution, and Review Rules

Use this workflow for non-trivial changes in the harness.

1. Restate the goal and identify the affected subsystem.
2. Write or update tests before production code.
3. Run the targeted failing test and confirm the failure is meaningful.
4. Implement the smallest production change that satisfies the test.
5. Run targeted tests, then the full non-live gate.
6. Review changed files for unrelated churn, missing structured outputs, and weak tests.
7. Report commands run, failures fixed, skipped live checks, and residual risk.

Tests are weak when they only assert that a function was called, only cover a mock, or do not prove a behavior the project relies on.
