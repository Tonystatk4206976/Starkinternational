from __future__ import annotations

import unittest

from dedalus_machines import DedalusMachinesClient, DedalusMachinesConfig


class RecordingDedalusMachinesClient(DedalusMachinesClient):
    def __init__(self, responses):
        super().__init__(DedalusMachinesConfig(api_key="test-key", base_url="https://example.test"))
        self.calls = []
        self.responses = list(responses)

    def request(self, method, path, *, body=None, query=None, headers=None, stream=False):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "body": body,
                "query": query,
                "headers": headers,
                "stream": stream,
            }
        )
        return self.responses.pop(0)


class DedalusMachinesClientTests(unittest.TestCase):
    def test_machine_lifecycle_paths_match_generated_sdk(self):
        client = RecordingDedalusMachinesClient([
            {"machine_id": "dm-1"},
            {"machine_id": "dm-1"},
            {"items": [], "next_cursor": None},
            {"machine_id": "dm-1"},
            {"machine_id": "dm-1"},
        ])

        client.machines.create(memory_mib=2048, storage_gib=10, vcpu=1, autosleep="30m")
        client.machines.retrieve(machine_id="dm-1")
        client.machines.list(limit=50)
        client.machines.sleep(machine_id="dm-1")
        client.machines.wake(machine_id="dm-1")

        self.assertEqual(
            [(call["method"], call["path"]) for call in client.calls],
            [
                ("POST", "/v1/machines"),
                ("GET", "/v1/machines/dm-1"),
                ("GET", "/v1/machines"),
                ("POST", "/v1/machines/dm-1/sleep"),
                ("POST", "/v1/machines/dm-1/wake"),
            ],
        )
        self.assertEqual(client.calls[0]["body"]["autosleep"], "30m")
        self.assertEqual(client.calls[2]["query"], {"cursor": None, "limit": 50})

    def test_nested_resource_paths_match_generated_sdk(self):
        client = RecordingDedalusMachinesClient([{}, {}, {}, {}, {}, {}])

        client.machines.previews.create(machine_id="dm-1", port=8000, protocol="http")
        client.machines.ssh.create(machine_id="dm-1", public_key="ssh-ed25519 AAA")
        client.machines.terminals.create(machine_id="dm-1", height=24, width=80, shell="/bin/bash")
        client.machines.artifacts.retrieve(machine_id="dm-1", artifact_id="art-1")
        client.usage.machine_compute(granularity="day", machine_id="dm-1")
        client.usage.machine_storage(machine_id="dm-1")

        self.assertEqual(
            [(call["method"], call["path"]) for call in client.calls],
            [
                ("POST", "/v1/machines/dm-1/previews"),
                ("POST", "/v1/machines/dm-1/ssh"),
                ("POST", "/v1/machines/dm-1/terminals"),
                ("GET", "/v1/machines/dm-1/artifacts/art-1"),
                ("GET", "/v1/usage/machines/compute"),
                ("GET", "/v1/usage/machines/storage"),
            ],
        )

    def test_run_and_wait_attaches_execution_output(self):
        client = RecordingDedalusMachinesClient([
            {"execution_id": "ex-1", "status": {"phase": "running"}},
            {"execution_id": "ex-1", "status": {"phase": "succeeded"}},
            {"stdout": "hello\n", "stderr": "", "exit_code": 0},
        ])

        result = client.machines.executions.run_and_wait(
            machine_id="dm-1",
            command=["echo", "hello"],
            poll_interval_s=0,
        )

        self.assertEqual(result["status"]["phase"], "succeeded")
        self.assertEqual(result["output"]["stdout"], "hello\n")
        self.assertEqual(
            [(call["method"], call["path"]) for call in client.calls],
            [
                ("POST", "/v1/machines/dm-1/executions"),
                ("GET", "/v1/machines/dm-1/executions/ex-1"),
                ("GET", "/v1/machines/dm-1/executions/ex-1/output"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
