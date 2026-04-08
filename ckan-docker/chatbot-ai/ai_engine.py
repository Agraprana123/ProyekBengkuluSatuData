from knowledge import knowledge_base

def generate_answer(question, datasets):

    q = question.lower()

    # cek knowledge base dulu
    for key in knowledge_base:

        if key in q:
            return knowledge_base[key]

    # jika tidak ada di knowledge base → cari dataset
    if len(datasets) == 0:
        return "Maaf, saya tidak menemukan informasi atau dataset yang sesuai."

    reply = f"Saya menemukan {len(datasets)} dataset terkait:\n\n"

    for d in datasets:
        reply += f"- {d['title']}\n"

    reply += "\nSilakan buka dataset untuk melihat detail."

    return reply