from dynamic_agents.models.domain import RunRecord


def test_run_repository_round_trip(repository) -> None:
    record = RunRecord(run_id="run_1", request_id="req_1")
    repository.save_run(record)
    assert repository.get_run("run_1").request_id == "req_1"
