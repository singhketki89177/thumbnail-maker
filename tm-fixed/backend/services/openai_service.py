import base64

from openai import AsyncOpenAI

from backend.config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_thumbnails(
    prompt: str,
    style_prompt: str,
    headshot_url: str,
) -> bytes:
    """
    Generate a thumbnail image via the OpenAI Responses API with the
    image_generation built-in tool.  Returns raw PNG bytes.
    """
    full_prompt = (
        f"{style_prompt}\n\n"
        f"User request: {prompt}\n\n"
        "IMPORTANT: The generated thumbnail MUST prominently feature "
        "the person shown in the provided reference headshot photo. "
        "Keep their likeness accurate."
    )

    # client.responses.create is a coroutine — must be awaited
    response = await client.responses.create(
        model="gpt-4.1",          # mainline vision model that supports image_generation tool
        input=[
            {
                "role": "user",
                "content": [
                    # `image_url` is the correct key (not `url`)
                    {"type": "input_image", "image_url": headshot_url},
                    {"type": "input_text",  "text": full_prompt},
                ],
            }
        ],
        tools=[
            {
                "type": "image_generation",
                # size and quality are valid tool params; do NOT set `model` here —
                # the Responses API selects the image model automatically.
                "size": "1536x1024",
                "quality": "high",
                "output_format": "png",
            }
        ],
    )

    for item in response.output:
        if item.type == "image_generation_call" and item.result:
            return base64.b64decode(item.result)

    raise RuntimeError("OpenAI returned no image_generation_call result")
