import requests
from config import CONFIG
import logging

logger = logging.getLogger(__name__)


def get_cohere_response(question):

    cohere_api_key = CONFIG.get('COHERE_API_KEY')
    if not cohere_api_key:
        logger.error("Cohere API key not set!")
        return "Error: Cohere API key not set."

    api_url = 'https://api.cohere.ai/generate'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {cohere_api_key}'
    }

    data = {
        'prompt': question,
        'max_tokens': 150,
        'temperature': 0.7,
        'k': 0,
        'p': 0.75,
        'stop_sequences': [],
        'return_likelihoods': 'NONE',
    }

    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        text = result['text'].strip()
        return text
    else:
        logger.error(f"Cohere API error {response.status_code}: {response.text}")
        return "Sorry, there was an error with the language model."
