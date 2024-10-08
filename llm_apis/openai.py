import requests
from config import CONFIG
import logging

logger = logging.getLogger(__name__)


def get_openai_response(question):
    openai_api_key = CONFIG.get('OPENAI_API_KEY')
    if not openai_api_key:
        logger.error("OpenAI API key not set!")
        return "Error: OpenAI API key not set."

    api_url = 'https://api.openai.com/v1/chat/completions'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {openai_api_key}'
    }

    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': question}
        ],
        'max_tokens': 150,
        'n': 1,
        'temperature': 0.7,
    }

    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        text = result['choices'][0]['message']['content'].strip()
        return text
    else:
        logger.error(f"OpenAI API error {response.status_code}: {response.text}")
        return "Sorry, there was an error with the language model."
