import base64
from typing import Literal

from openai import OpenAI


ImageFmts = Literal["jpeg", "jpg", "png", "webp", "gif"]


class OpenAIClient:

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key)

    def run_chat_completion_with_image(
        self,
        message: str,
        base64_image: str,
        model: str = "gpt-4o-mini",
        image_format:ImageFmts  = "jpeg",
        max_tokens: int = 2048,
    ):
        """Run the OpenAI chat completion with an image

        Parameters
        ----------
        message :
          The prompt to send for chat completion together with the image
        base64_image :
          The image data as a base64 string
        model :
            The model to use. The default is the gpt-4o-mini model.
        image_format :
            The format of the image. The default is "jpeg". Currently supports
            "jpeg", "jpg", "png", "webp", "gif". GIF images cannot be animated.
        max_tokens :
            The maximum number of tokens to generate for chat completion. One
            token is roughly one word in plain text, however it can be more per
            word in some cases. The default is 150.

        Returns
        -------
        :
            The response from OpenAI as a string.
        """
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                # Supports PNG, JPEG, WEBP, non-animated GIF
                                "url": f"data:image/{image_format};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0]


# encode an image file
def encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
