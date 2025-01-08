from flask import Flask, request, jsonify
import requests
import os
app = Flask(__name__)

# Tokens y configuraciones
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Ruta del webhook
@app.route('/webhook', methods=['POST'])
def gitlab_webhook():
    # Recibe los datos del webhook
    data = request.json
    if "object_kind" in data and data["object_kind"] == "issue":
        issue = data["object_attributes"]
        # Extraer propiedades del ticket
        issue_id = str(issue["id"])
        title = issue["title"]
        description = issue.get("description", "")
        url = issue["url"]
        assignee = issue.get("assignee", {}).get("name", "Sin asignar")
        created_at = issue["created_at"]
        milestone = issue.get("milestone", {}).get("title", "Sin hito")
        time_estimate = issue.get("time_estimate", 0)
        time_spent = issue.get("total_time_spent", 0)
        epic_title = data.get("epic", {}).get("title", "Sin épica")

        # Manejar los labels para separar Estado, Prioridad, Módulo y Tipo
        labels = issue["labels"]
        estado = get_label_value(labels, "Estado")
        prioridad = get_label_value(labels, "Prioridad")
        modulo = get_label_value(labels, "Modulo")
        tipo = get_label_value(labels, "Tipo")

        # Verifica si ya existe en Notion
        notion_page = buscar_pagina_notion(issue_id)
        if notion_page:
            # Actualiza la tarea existente
            actualizar_pagina_notion(
                notion_page["id"], title, description, url, assignee,
                created_at, milestone, time_estimate, time_spent, epic_title,
                estado, prioridad, modulo, tipo
            )
        else:
            # Crea una nueva tarea
            crear_pagina_notion(
                issue_id, title, description, url, assignee,
                created_at, milestone, time_estimate, time_spent, epic_title,
                estado, prioridad, modulo, tipo
            )
    return jsonify({"status": "success"}), 200

# Extraer el valor de un label basado en su prefijo (e.g., "Estado :: En proceso")
def get_label_value(labels, prefix):
    for label in labels:
        if label.startswith(f"{prefix} :: "):
            return label.split(" :: ")[1]
    return "Sin especificar"

# Buscar página en Notion por Issue ID
def buscar_pagina_notion(issue_id):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    query = {
        "filter": {
            "property": "Issue ID",  # Debe coincidir con el nombre de la propiedad en Notion
            "text": {
                "equals": issue_id
            }
        }
    }
    response = requests.post(url, headers=NOTION_HEADERS, json=query)
    results = response.json().get("results", [])
    return results[0] if results else None


def crear_pagina_notion(issue_id, title, description, url, assignee, created_at,
                        milestone, time_estimate, time_spent, epic_title,
                        estado, prioridad, modulo, tipo):
    notion_url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Título": {"title": [{"text": {"content": title}}]},
            "Descripción": {"rich_text": [{"text": {"content": description}}]},
            "Issue ID": {"rich_text": [{"text": {"content": issue_id}}]},
            "URL": {"url": url},
            "Assignee": {"rich_text": [{"text": {"content": assignee}}]},
            "Created At (UTC)": {"date": {"start": created_at}},
            "Milestone": {"rich_text": [{"text": {"content": milestone}}]},
            "Time Estimate": {"number": time_estimate},
            "Time Spent": {"number": time_spent},
            "Epic Title": {"rich_text": [{"text": {"content": epic_title}}]},
            "Estado": {"select": {"name": estado}},
            "Prioridad": {"select": {"name": prioridad}},
            "Modulo": {"select": {"name": modulo}},
            "Tipo": {"select": {"name": tipo}}
        }
    }
    response = requests.post(notion_url, headers=NOTION_HEADERS, json=data)
    return response.status_code == 200

# Actualizar tarea existente en Notion
def actualizar_pagina_notion(page_id, title, description, url, assignee, created_at,
                             milestone, time_estimate, time_spent, epic_title,
                             estado, prioridad, modulo, tipo):
    notion_url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Título": {"title": [{"text": {"content": title}}]},
            "Descripción": {"rich_text": [{"text": {"content": description}}]},
            "URL": {"url": url},
            "Assignee": {"rich_text": [{"text": {"content": assignee}}]},
            "Created At (UTC)": {"date": {"start": created_at}},
            "Milestone": {"rich_text": [{"text": {"content": milestone}}]},
            "Time Estimate": {"number": time_estimate},
            "Time Spent": {"number": time_spent},
            "Epic Title": {"rich_text": [{"text": {"content": epic_title}}]},
            "Estado": {"select": {"name": estado}},
            "Prioridad": {"select": {"name": prioridad}},
            "Modulo": {"select": {"name": modulo}},
            "Tipo": {"select": {"name": tipo}}
        }
    }
    response = requests.patch(notion_url, headers=NOTION_HEADERS, json=data)
    return response.status_code == 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
