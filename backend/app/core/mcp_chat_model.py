from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from mcp.types import ModelPreferences, SamplingMessage, TextContent
from app.core.mcp_context import mcp_session_var

class MCPChatModel(BaseChatModel):
    model_name: str = "mcp-client-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("MCPChatModel does not support synchronous generation.")

    @property
    def _llm_type(self) -> str:
        return "mcp-chat-model"

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        mcp_messages = []
        system_prompt = ""
        for msg in messages:
            if isinstance(msg, SystemMessage):
                if isinstance(msg.content, str):
                    system_prompt += msg.content + "\n"
            elif isinstance(msg, HumanMessage):
                mcp_messages.append(
                    SamplingMessage(
                        role="user",
                        content=TextContent(type="text", text=str(msg.content))
                    )
                )
            elif isinstance(msg, AIMessage):
                mcp_messages.append(
                    SamplingMessage(
                        role="assistant",
                        content=TextContent(type="text", text=str(msg.content))
                    )
                )

        max_tokens = kwargs.get("max_tokens", 1000)
        session = mcp_session_var.get()
        if not session:
            raise RuntimeError("No active MCP session found in context.")

        try:
            response = await session.create_message(
                messages=mcp_messages,
                system_prompt=system_prompt if system_prompt else None,
                model_preferences=ModelPreferences(),
                max_tokens=max_tokens,
                stop_sequences=stop
            )

            # Extract content from response
            text_content = ""
            if hasattr(response, 'content') and response.content:
                if isinstance(response.content, TextContent):
                    text_content = response.content.text
                elif isinstance(response.content, str):
                    text_content = response.content
                elif hasattr(response.content, '__iter__') and not isinstance(response.content, str):
                    texts = []
                    for block in response.content:
                        if hasattr(block, 'text'):
                            texts.append(block.text)
                        elif isinstance(block, dict) and 'text' in block:
                            texts.append(block['text'])
                    text_content = "".join(texts)
                elif hasattr(response.content, 'text'):
                    text_content = response.content.text
                else:
                    text_content = str(response.content)

            message = AIMessage(content=text_content)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

        except Exception as e:
            raise RuntimeError(f"MCP sampling failed: {e}")
