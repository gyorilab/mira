import base64
from typing import Literal, Optional, Union, List

from openai import OpenAI


ImageFmts = Literal["jpeg", "jpg", "png", "webp", "gif"]
ALLOWED_FORMATS = ["jpeg", "jpg", "png", "webp", "gif"]
MAX_TOKENS = 2048


class OpenAIClient:

    def __init__(
            self, 
            api_key: str = None, 
            model: str = "gpt-4o-mini", 
            temperature: float = None,
            max_completion_tokens: int = MAX_TOKENS
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        # instructions, systerm_prompt, reasoning
 
    def _track_usage(
            self, 
            response
    ) -> None:
        """Accumulate token usage from a response object.
 
        Parameters
        ----------
        response :
            The raw response object returned by chat.completions.create.
        """
        if response.usage:
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens


    def _add_response_schema(
        self,
        kwargs: dict,
        schema: dict | None,
        strict: bool = True,
    ) -> None:
        """Add the response format schema to the kwargs for chat completion

        Parameters
        ----------
        kwargs :
            The kwargs to pass to chat completion
        schema :
            The schema to use for the response format. 
        strict :
            Whether to enforce the schema strictly.
        """
        if schema is None:
            return

        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": schema,
                "strict": strict,
            },
        }

    def reset_token_counts(self):
        """Reset the session token counters to zero."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        
    def run_chat_completion(
        self,
        message: str,
        schema: Optional[dict] = None,
        strict: Optional[bool] = True,
    ):
        """Run the OpenAI chat completion

        Parameters
        ----------
        message :
          The prompt to send for chat completion
        schema :
            The schema to use for the response format.
        strict :
            Whether to enforce the schema strictly.

        Returns
        -------
        :
            The response from OpenAI as a string.
        """

        content = [
                    {
                        "type": "text",
                        "text": message,
                    }
                ]
        
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        self._add_response_schema(kwargs, schema, strict)
        response = self.client.chat.completions.create(**kwargs)
        self._track_usage(response)
        return response.choices[0]

    def run_chat_completion_with_image(
        self,
        message: str,
        image_format: Union[ImageFmts, List[ImageFmts]],
        base64_image: Union[str, List[str]],
        schema: Optional[dict] = None,
        strict: Optional[bool] = True,
    ):
        """Run the OpenAI chat completion with an image or a list of images

        Parameters
        ----------
        message :
          The prompt to send for chat completion together with the image or list
          of images
        base64_image :
          The image data or list of image data as a base64 string
        model :
            The model to use. The default is the gpt-4o-mini model.
        image_format :
            The format of the image. The default is "jpeg". Currently supports
            "jpeg", "jpg", "png", "webp", "gif". GIF images cannot be animated.
        schema :
            The schema to use for the response format.
        strict :
            Whether to enforce the schema strictly.

        Returns
        -------
        :
            The response from OpenAI as a string.
        """

        if not isinstance(image_format, list):
            image_format = [image_format]
            base64_image = [base64_image]

        for fmt in image_format:
            if fmt not in ALLOWED_FORMATS:
                raise ValueError(
                    f"Image format {fmt} not supported. "
                    f"Supported formats are {ALLOWED_FORMATS}"
                )
        content = [
                    {"type": "text", "text": message},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{fmt};base64,{img}",
                                "detail": "high"
                            }
                        }
                        for img, fmt in zip(base64_image, image_format)
                    ]
                ]

        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        self._add_response_schema(kwargs, schema, strict)
        response = self.client.chat.completions.create(**kwargs)
        self._track_usage(response)
        return response.choices[0]

    def run_chat_completion_with_pdf(
        self,
        message: str,
        base64_pdf: str,
        schema: Optional[dict] = None,
        strict: Optional[bool] = True,
    ):
        """Run the OpenAI chat completion with a PDF file

        Parameters
        ----------
        message :
            The prompt to send for chat completion together with the PDF
        base64_pdf :
            The PDF data as a base64 string
        schema :
            The schema to use for the response format.
        strict :
            Whether to enforce the schema strictly.

        Returns
        -------
        :
            The response from OpenAI as a string
        """
        content = [
                        {
                        "type": "text",
                        "text": message,
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": "document.pdf",
                            "file_data": f"data:application/pdf;base64,{base64_pdf}",
                        },
                    },
                ]
        
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        self._add_response_schema(kwargs, schema, strict)
        response = self.client.chat.completions.create(**kwargs)
        self._track_usage(response)
        return response.choices[0]

    def run_chat_completion_with_text(
        self,
        message: str,
        text_content: str,
        schema: Optional[dict] = None,
        strict: Optional[bool] = True,
    ):
        """Run the OpenAI chat completion with input text

        Parameters
        ----------
        message :
            The prompt to send for chat completion together with the PDF
        text_content :
            The input text
        schema :
            The schema to use for the response format.
        strict :
            Whether to enforce the schema strictly.

        Returns
        -------
        :
            The response from OpenAI as a string
        """
        content = [
                    {
                        "type": "text",
                        "text": f"{message}\n\n{text_content}" ,
                    },
                ]
        
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        self._add_response_schema(kwargs, schema, strict)
        response = self.client.chat.completions.create(**kwargs)
        self._track_usage(response)
        return response.choices[0].message.content

    def run_chat_completion_with_image_url(
        self,
        message: str,
        image_url: str,
        schema: Optional[dict] = None,
        strict: Optional[bool] = True,
    ):
        """Run the OpenAI chat completion with an image URL

        Parameters
        ----------
        message :
          The prompt to send for chat completion together with the image
        image_url :
          The URL of the image
        schema :
            The schema to use for the response format.
        strict :
            Whether to enforce the schema strictly.

        Returns
        -------
        :
            The response from OpenAI
        """
        content = [
                    {
                        "type": "text",
                        "text": message,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ]
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "max_completion_tokens": self.max_completion_tokens,
        }

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        self._add_response_schema(kwargs, schema, strict)
        response = self.client.chat.completions.create(**kwargs)
        self._track_usage(response)
        return response.choices[0]  

# encode an image file
def encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
