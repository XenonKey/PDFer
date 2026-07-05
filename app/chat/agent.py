from anthropic import AsyncAnthropic

from app.chat.tools_impl import get_extraction_job_status
from app.chat.tools_schema import TOOLS
from app.config import settings

MAX_STEPS = 5

TOOL_REGISTRY = {
    "get_extraction_job_status": get_extraction_job_status,
}


client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def ask_about_job_status(question: str) -> str:
    """Ask about job status, Claude will return text if response.stop_reason == "end_turn" or will ask to use tool if response.stop_reason == "tool_use" """

    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_STEPS):
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            text_block = next((block for block in response.content if block.type == "text"), None)
            return text_block.text if text_block is not None else ""

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_function = TOOL_REGISTRY.get(block.name)
            if tool_function is None:
                result_text = f"Unknown tool: {block.name}"
            else:
                result_text = await tool_function(**block.input)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return "Could not get a final answer within the allotted number of steps."
