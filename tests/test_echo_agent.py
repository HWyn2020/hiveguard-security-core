"""Tests for the example echo agent."""
import asyncio

from examples.echo_agent import EchoAgent
from framework.agents.base_agent import BaseAgent


def test_echo_agent_is_base_agent_subclass():
    assert issubclass(EchoAgent, BaseAgent)


def test_echo_agent_instantiation():
    a = EchoAgent("echo-1", agent_type="echo", port=0)
    assert a.agent_id == "echo-1"
    assert a.agent_type == "echo"
    assert a.port == 0


def test_echo_agent_echoes_payload():
    a = EchoAgent("echo-1", agent_type="echo", port=0)
    result = asyncio.new_event_loop().run_until_complete(
        a.process_task({"message": "hello"})
    )
    assert result["echo"] == {"message": "hello"}
    assert result["processed_by"] == "echo-1"


def test_echo_agent_handles_empty_task():
    a = EchoAgent("echo-1", agent_type="echo", port=0)
    result = asyncio.new_event_loop().run_until_complete(a.process_task({}))
    assert result["echo"] == {}
    assert result["processed_by"] == "echo-1"
