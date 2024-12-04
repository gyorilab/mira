import base64
import os
import unittest

import requests

from mira.openai import OpenAIClient


@unittest.skipIf(os.environ.get('GITHUB_ACTIONS') is not None,
                 reason="Meant to be run locally")
@unittest.skipIf(os.environ.get('OPENAI_API_KEY') is None,
                 reason="Need OPENAI_API_KEY environment variable to run")
def test_explain_image():
    bananas_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Cavendish_Banana_DS.jpg/640px-Cavendish_Banana_DS.jpg"
    res = requests.get(bananas_url)
    base64_image = base64.b64encode(res.content).decode('utf-8')

    client = OpenAIClient()
    response = client.run_chat_completion_with_image(
        message="What is in this image?",
        base64_image=base64_image,
        image_format="jpeg",
    )
    assert "banana" in response.message.content, response.message.content
