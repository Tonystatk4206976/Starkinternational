# Starkinternational

Fund analytics helpers.

## Sentiment Gauge

This repo includes a Plotly helper to render a market sentiment gauge.

```python
from sentiment_gauge import display_sentiment_gauge

fig = display_sentiment_gauge(0.42)
fig.show()
```

For Streamlit:

```python
score = calculate_greed_score(headlines)
st.plotly_chart(display_sentiment_gauge(score), use_container_width=True)
```

## Profit Taker Calculator

Use `calculate_profit_taker_plan` to compute how many shares to sell in order to
recover your initial principal at the current market price.

```python
from risk_tools import calculate_profit_taker_plan

plan = calculate_profit_taker_plan(
    current_price=31.15,
    current_shares=420,
    initial_principal=10000,
)

print(plan.shares_to_sell)
print(plan.remaining_shares)
```

Optional dashboard copy for reinvestment ideas:

```python
from risk_tools import format_reinvestment_playbook

for item in format_reinvestment_playbook():
    st.write(f"- {item}")
```

> Educational tooling only — not financial advice.

## Dedalus Machines API Client

This repo includes a dependency-free Python client for Dedalus Machines in
`dedalus_machines.py`. It mirrors the public shape of the OpenAPI-generated
`dedalus-sdk` resource tree while returning plain Python dictionaries, so it can
be used in lightweight automation without adding `httpx` or `pydantic`.

```python
from dedalus_machines import DedalusMachinesClient

client = DedalusMachinesClient()  # reads DEDALUS_API_KEY

machine = client.machines.create(
    memory_mib=2048,
    storage_gib=10,
    vcpu=1,
    autosleep="30m",
)
machine_id = machine["machine_id"]

result = client.machines.executions.run_and_wait(
    machine_id=machine_id,
    command=["bash", "-lc", "python --version"],
)
print(result["output"].get("stdout", ""))
```

Supported resource helpers include:

- Machine lifecycle: `create`, `retrieve`, `update`, `list`, `iter_all`,
  `sleep`, `wake`, `watch`, `wait_for_phase`, and `delete`.
- Executions: `create`, `retrieve`, `list`, `iter_all`, `events`, `output`,
  `delete`, and the convenience `run_and_wait` helper.
- Ports/previews: `client.machines.previews.create(...)`, `retrieve`, `list`,
  and `delete`.
- SSH sessions: `client.machines.ssh.create(...)`, `retrieve`, `list`, and
  `delete`.
- Terminals: `client.machines.terminals.create(...)`, `retrieve`, `list`, and
  `delete`.
- Artifacts: `client.machines.artifacts.retrieve(...)`, `list`, and `delete`.
- Usage: `client.usage.retrieve(...)`, `machine_compute`, and
  `machine_storage`.

If you install Dedalus' official OpenAPI-generated SDK, you can use the wrapper
when you want generated models, retries, and WebSocket handling:

```python
from dedalus_machines import GeneratedDedalusMachines

client = GeneratedDedalusMachines.from_default_sdk()
for machine in client.machines.list():
    print(machine.machine_id)
```

The lightweight client defaults to `https://api.dedaluslabs.ai`, uses bearer
auth from `DEDALUS_API_KEY`, and sends requests to the generated SDK-compatible
`/v1/machines` and `/v1/usage` endpoints.
