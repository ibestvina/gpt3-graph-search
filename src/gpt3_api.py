from dotenv import load_dotenv

load_dotenv()
import openai


def execute(prompt, **kwargs):
    response = openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        **kwargs
    )
    return response
