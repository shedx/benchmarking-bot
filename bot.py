import logging
import random

from sqlalchemy import func

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

from config import CONFIG
from database.models import Session, Rating
from llm_apis.cohere import get_cohere_response
from llm_apis.huggingface import get_huggingface_response
from llm_apis.openai import get_openai_response
from utils.graphs import send_graphs

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Supported LLMs
LLM_APIS = {
    # 'openai': {
    #     'name': 'OpenAI GPT-3.5',
    #     'api_function': 'get_openai_response'
    # },
    'cohere': {
        'name': 'Cohere',
        'api_function': 'get_cohere_response'
    },
    'huggingface': {
        'name': 'GPT-2 (Hugging Face)',
        'api_function': 'get_huggingface_response'
    },
}

PREDEFINED_QUESTIONS = [
    "What are the main advantages of using large-scale language models?",
    "What limitations exist in current LLMs?",
    "How is safety and ethics ensured in LLM development?",
]

def select_llm(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton(LLM_APIS[model]['name'], callback_data=model)]
        for model in LLM_APIS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text(
            'Please choose a language model:',
            reply_markup=reply_markup
        )
    elif update.callback_query:
        update.callback_query.message.reply_text(
            'Please choose a language model:',
            reply_markup=reply_markup
        )
    else:
        logger.error("Cannot send message: both update.message and update.callback_query are None")


def handle_model_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    model_key = query.data
    context.user_data['model'] = model_key

    keyboard = [
        [
            InlineKeyboardButton("Manual input", callback_data='manual_question'),
            InlineKeyboardButton("From benchmark", callback_data='predefined_question')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=f"You selected model: {LLM_APIS[model_key]['name']}\nPlease choose an option:",
        reply_markup=reply_markup
    )


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Hello! I can answer your questions using various language models."
    )
    select_llm(update, context)


def handle_question(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get('expecting_question', False):
        return

    question = update.message.text
    user_id = update.message.from_user.id
    model_key = context.user_data.get('model', 'cohere')

    llm_response = get_llm_response(question, model_key)

    context.user_data['question'] = question
    context.user_data['answer'] = llm_response

    context.user_data['expecting_question'] = False

    update.message.reply_text(llm_response)

    keyboard = [
        [
            InlineKeyboardButton("0", callback_data='0'),
            InlineKeyboardButton("1", callback_data='1'),
            InlineKeyboardButton("2", callback_data='2')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'Please rate the answer (0-2):',
        reply_markup=reply_markup
    )


def handle_rating(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    rating = int(query.data)
    user_id = query.from_user.id
    question = context.user_data.get('question', '')
    answer = context.user_data.get('answer', '')
    model_key = context.user_data.get('model', 'cohere')

    session = Session()
    new_rating = Rating(
        user_id=user_id,
        question=question,
        answer=answer,
        rating=rating,
        model=model_key
    )
    session.add(new_rating)
    session.commit()
    session.close()

    query.edit_message_text(text=f"Thank you! You rated: {rating}")

    keyboard = [
        [InlineKeyboardButton("View statistics", callback_data='view_stats')],
        [InlineKeyboardButton("Ask another question", callback_data='ask_again')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        'What would you like to do next?',
        reply_markup=reply_markup
    )


def handle_post_rating_option(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'view_stats':
        stats(update, context)
    elif query.data == 'ask_again':
        select_llm(update, context)
    else:
        query.message.reply_text("Please choose a valid option.")


def stats(update: Update, context: CallbackContext) -> None:
    session = Session()
    user_id = update.effective_user.id

    total_ratings = session.query(Rating).count()
    avg_rating = session.query(func.avg(Rating.rating)).scalar() or 0
    avg_rating = round(avg_rating, 2)

    user_ratings = session.query(Rating).filter(Rating.user_id == user_id).count()
    user_avg_rating = session.query(func.avg(Rating.rating)).filter(Rating.user_id == user_id).scalar() or 0
    user_avg_rating = round(user_avg_rating, 2)

    message = (
        f"Total ratings: {total_ratings}\n"
        f"Average rating: {avg_rating}\n\n"
        f"Your ratings: {user_ratings}\n"
        f"Your average rating: {user_avg_rating}"
    )

    update.effective_message.reply_text(message)

    send_graphs(update, context, session)

    keyboard = [
        [InlineKeyboardButton("View statistics", callback_data='view_stats')],
        [InlineKeyboardButton("Ask another question", callback_data='ask_again')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    if query:
        query.message.reply_text(
            'What would you like to do next?',
            reply_markup=reply_markup
        )
    else:
        update.effective_message.reply_text(
            'What would you like to do next?',
            reply_markup=reply_markup
        )
    session.close()


def handle_question_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    choice = query.data

    if choice == 'manual_question':
        context.user_data['expecting_question'] = True
        query.edit_message_text(text="Please enter your question.")
    elif choice == 'predefined_question':
        keyboard = [
            [
                InlineKeyboardButton("Random question", callback_data='random_question'),
                InlineKeyboardButton("Select manually", callback_data='choose_manual')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text="Please choose an option:",reply_markup=reply_markup
        )


def handle_predefined_question_option(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    option = query.data

    if option == 'random_question':
        question = random.choice(PREDEFINED_QUESTIONS)
        context.user_data['question'] = question

        model_key = context.user_data.get('model', 'cohere')
        llm_response = get_llm_response(question, model_key)
        context.user_data['answer'] = llm_response

        query.edit_message_text(text=f"Question: {question}\n\nAnswer:\n{llm_response}")

        keyboard = [
            [
                InlineKeyboardButton("0", callback_data='0'),
                InlineKeyboardButton("1", callback_data='1'),
                InlineKeyboardButton("2", callback_data='2')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=query.message.chat_id,
            text='Please rate the answer (0-2):',
            reply_markup=reply_markup
        )
    elif option == 'choose_manual':
        keyboard = [
            [InlineKeyboardButton(f"{question}", callback_data=f"predefined_{index}")]
            for index, question in enumerate(PREDEFINED_QUESTIONS)
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="Please select a question:", reply_markup=reply_markup)
    else:
        query.edit_message_text(text="Please choose a valid option.")


def handle_predefined_question_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    data = query.data
    index = int(data.split('_')[1])
    question = PREDEFINED_QUESTIONS[index]

    user_id = query.from_user.id
    model_key = context.user_data.get('model', 'cohere')

    context.user_data['question'] = question

    llm_response = get_llm_response(question, model_key)

    context.user_data['answer'] = llm_response

    query.edit_message_text(text=f"Question: {question}\n\nAnswer:\n{llm_response}")

    keyboard = [
        [
            InlineKeyboardButton("0", callback_data='0'),
            InlineKeyboardButton("1", callback_data='1'),
            InlineKeyboardButton("2", callback_data='2')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text='Please rate the answer (0-2):',
        reply_markup=reply_markup
    )


def get_llm_response(question, model_key):
    if model_key == 'cohere':
        return get_cohere_response(question)
    elif model_key == 'huggingface':
        return get_huggingface_response(question)
    elif model_key == 'openai':
        return get_openai_response(question)
    else:
        return "Invalid language model selected."


def main():
    telegram_token = CONFIG.get('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.error("Telegram bot token is not set!")
        return

    updater = Updater(telegram_token, use_context=True)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stats", stats))

    # Callback handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_model_selection, pattern='^(' + '|'.join(LLM_APIS.keys()) + ')$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_question_choice, pattern='^(manual_question|predefined_question)$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_predefined_question_option, pattern='^(random_question|choose_manual)$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_predefined_question_selection, pattern='^predefined_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_rating, pattern='^[0-2]$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_post_rating_option, pattern='^(view_stats|ask_again)$'))

    # Message handler for questions
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_question))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
