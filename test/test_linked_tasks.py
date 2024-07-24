from pathlib import Path
import unittest

from defusedxml.ElementTree import fromstring
import pytest
import requests_mock

import tableauserverclient as TSC
from tableauserverclient.models.linked_tasks_item import LinkedTaskItem, LinkedTaskStepItem, LinkedTaskFlowRunItem

asset_dir = (Path(__file__).parent / "assets").resolve()

GET_LINKED_TASKS = asset_dir / "linked_tasks_get.xml"


class TestLinkedTasks(unittest.TestCase):
    def setUp(self) -> None:
        self.server = TSC.Server("http://test", False)
        self.server.version = "3.15"

        # Fake signin
        self.server._site_id = "dad65087-b08b-4603-af4e-2887b8aafc67"
        self.server._auth_token = "j80k54ll2lfMZ0tv97mlPvvSCRyD0DOM"

        self.baseurl = self.server.linked_tasks.baseurl

    def test_parse_linked_task_flow_run(self):
        xml = fromstring(GET_LINKED_TASKS.read_bytes())
        task_runs = LinkedTaskFlowRunItem._parse_element(xml, self.server.namespace)
        assert 1 == len(task_runs)
        task = task_runs[0]
        assert task.flow_run_id == "e3d1fc25-5644-4e32-af35-58dcbd1dbd73"
        assert task.flow_run_priority == 1
        assert task.flow_run_consecutive_failed_count == 3
        assert task.flow_run_task_type == "runFlow"
        assert task.flow_id == "ab1231eb-b8ca-461e-a131-83f3c2b6a673"
        assert task.flow_name == "flow-name"

    def test_parse_linked_task_step(self):
        xml = fromstring(GET_LINKED_TASKS.read_bytes())
        steps = LinkedTaskStepItem.from_task_xml(xml, self.server.namespace)
        assert 1 == len(steps)
        step = steps[0]
        assert step.id == "f554a4df-bb6f-4294-94ee-9a709ef9bda0"
        assert step.stop_downstream_on_failure
        assert step.step_number == 1
        assert 1 == len(step.task_details)
        task = step.task_details[0]
        assert task.flow_run_id == "e3d1fc25-5644-4e32-af35-58dcbd1dbd73"
        assert task.flow_run_priority == 1
        assert task.flow_run_consecutive_failed_count == 3
        assert task.flow_run_task_type == "runFlow"
        assert task.flow_id == "ab1231eb-b8ca-461e-a131-83f3c2b6a673"
        assert task.flow_name == "flow-name"

    def test_parse_linked_task(self):
        tasks = LinkedTaskItem.from_response(GET_LINKED_TASKS.read_bytes(), self.server.namespace)
        assert 1 == len(tasks)
        task = tasks[0]
        assert task.id == "1b8211dc-51a8-45ce-a831-b5921708e03e"
        assert task.num_steps == 1
        assert task.schedule is not None
        assert task.schedule.id == "be077332-d01d-481b-b2f3-917e463d4dca"

    def test_get_linked_tasks(self):
        with requests_mock.mock() as m:
            m.get(self.baseurl, text=GET_LINKED_TASKS.read_text())
            tasks, pagination_item = self.server.linked_tasks.get()

        assert 1 == len(tasks)
        task = tasks[0]
        assert task.id == "1b8211dc-51a8-45ce-a831-b5921708e03e"
        assert task.num_steps == 1
        assert task.schedule is not None
        assert task.schedule.id == "be077332-d01d-481b-b2f3-917e463d4dca"
