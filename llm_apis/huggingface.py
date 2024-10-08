import requests
from config import CONFIG
import logging

logger = logging.getLogger(__name__)


def get_huggingface_response(question):
    hf_api_key = CONFIG.get('HUGGINGFACE_API_KEY')

    if not hf_api_key:
        logger.error("Hugging Face API key not set!")
        return "Error: Hugging Face API key not set."

    model_id = 'gpt2'  # You can choose any available model
    api_url = f'https://api-inference.huggingface.co/models/{model_id}'

    headers = {
        'Authorization': f'Bearer {hf_api_key}'
    }

    data = {
        'inputs': question,
        'parameters': {
            'max_length': 150,
            'temperature': 0.7,
        },
    }

    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        if isinstance(result, dict) and result.get('error'):
            logger.error(f"Hugging Face API error: {result['error']}")
            return "Sorry, there was an error with the language model."
        text = result[0]['generated_text'].strip()
        return text
    else:
        logger.error(f"Hugging Face API error {response.status_code}: {response.text}")
        return "Sorry, there was an error with the language model."
