from typing import Any, Dict, List, Optional, Literal, Mapping, cast
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage, FunctionMessage, ChatMessage
import langchain_openai.chat_models.base as _base_module


_original_convert_dict_to_message = _base_module._convert_dict_to_message
_original_convert_message_to_dict = _base_module._convert_message_to_dict


def _patched_convert_dict_to_message(_dict: Mapping[str, Any]) -> BaseMessage:
    """Convert dictionary to message, with reasoning_content support."""
    role = _dict.get("role")
    name = _dict.get("name")
    id_ = _dict.get("id")
    
    if role == "user":
        return HumanMessage(content=_dict.get("content", ""), id=id_, name=name)
    
    if role == "assistant":
        content = _dict.get("content", "") or ""
        additional_kwargs: dict = {}
        
        if function_call := _dict.get("function_call"):
            additional_kwargs["function_call"] = dict(function_call)
        
        if reasoning := _dict.get("reasoning_content"):
            additional_kwargs["reasoning_content"] = reasoning
        
        tool_calls = []
        invalid_tool_calls = []
        if raw_tool_calls := _dict.get("tool_calls"):
            for raw_tool_call in raw_tool_calls:
                try:
                    tool_calls.append(_base_module.parse_tool_call(raw_tool_call, return_id=True))
                except Exception as e:
                    invalid_tool_calls.append(
                        _base_module.make_invalid_tool_call(raw_tool_call, str(e))
                    )
        if audio := _dict.get("audio"):
            additional_kwargs["audio"] = audio
        
        return AIMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            name=name,
            id=id_,
            tool_calls=tool_calls,
            invalid_tool_calls=invalid_tool_calls,
        )
    
    if role in ("system", "developer"):
        additional_kwargs = {"__openai_role__": role} if role == "developer" else {}
        return SystemMessage(
            content=_dict.get("content", ""),
            name=name,
            id=id_,
            additional_kwargs=additional_kwargs,
        )
    
    if role == "function":
        return FunctionMessage(
            content=_dict.get("content", ""), name=cast(str, _dict.get("name")), id=id_
        )
    
    if role == "tool":
        additional_kwargs = {}
        if "name" in _dict:
            additional_kwargs["name"] = _dict["name"]
        return ToolMessage(
            content=_dict.get("content", ""),
            tool_call_id=cast(str, _dict.get("tool_call_id")),
            additional_kwargs=additional_kwargs,
            name=name,
            id=id_,
        )
    
    return ChatMessage(content=_dict.get("content", ""), role=role, id=id_)


def _patched_convert_message_to_dict(message: BaseMessage, api="chat/completions") -> dict:
    """Convert message to dict, with reasoning_content support."""
    message_dict = _original_convert_message_to_dict(message, api)
    
    if isinstance(message, AIMessage):
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            message_dict["reasoning_content"] = reasoning
    
    return message_dict


class MiMoChatOpenAI(ChatOpenAI):
    """支持mimo模型reasoning_content的ChatOpenAI"""
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        _base_module._convert_dict_to_message = _patched_convert_dict_to_message
        _base_module._convert_message_to_dict = _patched_convert_message_to_dict
        try:
            result = super()._generate(messages, stop, run_manager, **kwargs)
        finally:
            _base_module._convert_dict_to_message = _original_convert_dict_to_message
            _base_module._convert_message_to_dict = _original_convert_message_to_dict
        
        return result
