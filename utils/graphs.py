import io

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import textwrap

from telegram import Update
from telegram.ext import CallbackContext

from database.models import Rating


def send_graphs(update: Update, context: CallbackContext, session):
    # Generate distribution graph
    df = pd.read_sql(session.query(Rating).statement, session.bind)

    if df.empty:
        update.effective_message.reply_text("No data available for graphs.")
        return

    model_names = {
        # 'openai': 'OpenAI GPT-3.5',
        'cohere': 'Cohere',
        'huggingface': 'GPT-2(Hugging Face)'
    }

    df['Model'] = df['model'].map(model_names)

    # Models performance distribution
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x='rating', hue='Model', bins=10, palette='Set1', element="step", discrete=True)

    plt.title('Rating distribution')
    plt.xlabel('Rating')
    plt.ylabel('Frequency')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    update.effective_message.reply_photo(photo=buf)

    # Model performance
    model_avg = df.groupby('model')['rating'].mean()
    model_avg.plot(kind='bar', figsize=(10,6))
    plt.title('Average Rating by Model')
    plt.xlabel('Model')
    plt.ylabel('Average Rating')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    update.effective_message.reply_photo(photo=buf)

    # top-5 and bottom-5
    for model_key, model_name in model_names.items():
        model_df = df[df['model'] == model_key]

        if model_df.empty:
            continue
        top5 = model_df.nlargest(5, 'rating')[['question', 'answer', 'rating']]

        bottom5 = model_df.nsmallest(5, 'rating')[['question', 'answer', 'rating']]
        if not top5.empty:
            top_title = f"Top-5 {model_name} answers"
            top_buf = create_table_image(top5, top_title)
            update.effective_message.reply_document(document=top_buf, filename='top_answers.png')
        else:
            update.effective_message.reply_text(f"No top answers available for {model_name}.")

        if not bottom5.empty:
            bottom_title = f"Bottom-5 {model_name} answers"
            bottom_buf = create_table_image(bottom5, bottom_title)
            update.effective_message.reply_document(document=bottom_buf, filename='bottom_answers.png')
        else:
            update.effective_message.reply_text(f"No bottom answers available for {model_name}.")


def create_table_image(df_table, title):
    max_colwidth = 40

    for col in ['question', 'answer']:
        df_table[col] = df_table[col].apply(lambda x: '\n'.join(textwrap.wrap(x, width=max_colwidth)))

    num_rows = max(len(df_table), 5)
    fig_height = num_rows * 0.6 + 1
    fig_width = 30

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')

    table = ax.table(cellText=df_table.values, colLabels=df_table.columns, loc='center')

    # Set font size and cell size
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    cell_dict = table.get_celld()
    for i in range(len(df_table.columns)):
        for j in range(len(df_table) + 1):  # +1 for headers
            cell = cell_dict[(j, i)]
            cell.set_height(0.5)
            cell.set_width(0.2)
            cell.set_text_props(ha='left', va='top')

    plt.title(title, fontsize=20, pad=0, loc="left")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()
    return buf
