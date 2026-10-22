"""Exercise the real stream/bridge path without relying on patch-only helpers."""
import asyncio
import json
from unittest.mock import MagicMock

import httpx
import pytest

from litellm.completion_extras.litellm_responses_transformation.handler import ResponsesToCompletionBridgeHandler
from litellm.completion_extras.litellm_responses_transformation.transformation import LiteLLMResponsesTransformationHandler
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.llms.chatgpt.responses.transformation import ChatGPTResponsesAPIConfig
from litellm.responses.streaming_iterator import ResponsesAPIStreamingIterator, SyncResponsesAPIStreamingIterator
from litellm.types.utils import ModelResponse


class QuietSync(SyncResponsesAPIStreamingIterator):
    def _handle_logging_completed_response(self):
        pass


class QuietAsync(ResponsesAPIStreamingIterator):
    def _handle_logging_completed_response(self):
        pass


def sse_body(event_kind, authoritative=False):
    item = {"type": "message", "id": "msg_audit", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": "AUDIT_OK", "annotations": []}]}
    first = ({"type": "response.output_item.done", "output_index": 0, "item": item}
             if event_kind == "item" else {"type": "response.output_text.done", "output_index": 0,
             "content_index": 0, "item_id": "msg_audit", "text": "AUDIT_OK"})
    completed = {"type": "response.completed", "response": {
        "id": "resp_audit", "object": "response", "created_at": 1700000000,
        "status": "completed", "model": "gpt-5.4", "error": None,
        "output": [item] if authoritative else [],
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}}
    return "".join("data: " + json.dumps(event) + "\n\n" for event in (first, completed))


async def replay(asynchronous, raw, save_raw=False):
    log = MagicMock(spec=Logging)
    log.model_call_details = {"litellm_params": {}}
    if save_raw:
        log.model_call_details["original_response"] = raw
    log.start_time = None
    log.completion_start_time = None
    provider = ChatGPTResponsesAPIConfig.__new__(ChatGPTResponsesAPIConfig)
    response = httpx.Response(200, headers={"content-type": "text/event-stream"}, text=raw)
    cls = QuietAsync if asynchronous else QuietSync
    iterator = cls(response=response, model="gpt-5.4", responses_api_provider_config=provider,
                   logging_obj=log, custom_llm_provider="chatgpt", request_data={})
    bridge = ResponsesToCompletionBridgeHandler()
    result = (await bridge._collect_response_from_stream_async(iterator) if asynchronous
              else bridge._collect_response_from_stream(iterator))
    return LiteLLMResponsesTransformationHandler().transform_response(
        model="gpt-5.4", raw_response=result, model_response=ModelResponse(), logging_obj=log,
        request_data={}, messages=[], optional_params={}, litellm_params={}, encoding=None)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("event_kind", ["item", "text"])
def test_stream_bridge_recovers_empty_terminal_output(asynchronous, event_kind):
    result = asyncio.run(replay(asynchronous, sse_body(event_kind)))
    assert result.choices[0].message.content == "AUDIT_OK"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_stream_bridge_preserves_populated_terminal_output(asynchronous):
    result = asyncio.run(replay(asynchronous, sse_body("item", authoritative=True)))
    assert result.choices[0].message.content == "AUDIT_OK"


@pytest.mark.parametrize("event_kind", ["item", "text"])
def test_older_buffered_parser_already_recovers_output(event_kind):
    provider = ChatGPTResponsesAPIConfig.__new__(ChatGPTResponsesAPIConfig)
    result, error = provider._extract_completed_response_from_sse(sse_body(event_kind))
    assert error is None
    assert result.output_text == "AUDIT_OK"


def test_older_bridge_fallback_works_when_raw_sse_is_available():
    result = asyncio.run(replay(False, sse_body("item"), save_raw=True))
    assert result.choices[0].message.content == "AUDIT_OK"
