# Testing Standards

This repository contains lightweight analytics helpers intended for use in dashboards and notebooks. Changes should be covered by fast, deterministic tests that verify calculation behavior, user-facing output, and integration boundaries without depending on live market data or network access.

## Goals

- Keep tests deterministic, repeatable, and safe to run locally or in CI.
- Validate financial calculations with explicit examples and edge cases.
- Protect dashboard-facing helpers from accidental API or presentation regressions.
- Prefer small unit tests over broad end-to-end tests unless a change crosses module boundaries.

## Required Checks Before Commit

Run the following checks before opening a pull request:

```bash
python -m pytest
python -m compileall .
```

If a dependency is missing in the local environment, document the exact command and failure in the pull request notes instead of skipping the check silently.

## Test Organization

- Place tests under a top-level `tests/` directory.
- Name test files after the module under test, such as `tests/test_risk_tools.py` or `tests/test_sentiment_gauge.py`.
- Use clear test names that describe the expected behavior, for example `test_profit_taker_caps_recovery_at_position_value`.
- Keep fixtures small and local to the test file unless they are shared by multiple modules.

## Unit Testing Expectations

### Risk calculations

For `risk_tools.py`, tests should cover:

- Normal recovery scenarios where the position value exceeds the initial principal.
- Partial recovery scenarios where the position value is less than the initial principal.
- Boundary inputs, including zero shares and zero initial principal.
- Validation errors for invalid prices, negative shares, and negative principal.
- Returned dataclass fields, not only a single headline value.

When comparing floating-point values, use `pytest.approx` for computed results.

### Sentiment gauge rendering

For `sentiment_gauge.py`, tests should cover:

- Score mapping from `-1.0`, `0.0`, and `1.0` to gauge values `0`, `50`, and `100`.
- Clipping behavior for values outside the supported `[-1.0, 1.0]` range.
- Stable dashboard configuration such as title text, gauge axis range, and sentiment color bands.

Tests should inspect the returned Plotly figure object directly rather than relying on screenshots.

## Integration Testing Expectations

Add integration tests when a change combines multiple helpers, introduces I/O, or adds a dashboard entry point. Integration tests should:

- Use static sample data committed with the test suite.
- Avoid live network calls and real brokerage or market-data APIs.
- Mock external services at the boundary where they enter the application.
- Verify the shape of user-facing results rather than implementation details.

## Test Data Standards

- Use small inline examples for simple calculations.
- Store larger fixtures under `tests/fixtures/` with descriptive file names.
- Do not commit secrets, account numbers, API keys, personal financial data, or proprietary market-data exports.
- Include comments for any fixture values that represent important edge cases.

## Regression Tests

Every bug fix should include a regression test that fails before the fix and passes after it. The test name should reference the behavior being protected, not an issue number alone.

## Performance and Reliability

- Keep the default test suite fast enough to run during every development cycle.
- Avoid sleeps, time-dependent assertions, and randomness.
- If randomness is necessary, use a fixed seed and assert broad invariants.
- Mark slow or optional tests explicitly so they can be excluded from the default run.

## Pull Request Checklist

Before requesting review, confirm that:

- New or changed behavior has appropriate tests.
- Existing tests pass locally or any environment limitation is documented.
- Financial examples in docs match the tested behavior.
- Error messages remain clear for dashboard or notebook users.
- No tests require private credentials, network access, or a specific local machine setup.
