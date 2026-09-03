def get_client_chat_style(text):
    return f"<div align='right' style='background: #1e3a5f; padding: 8px 12px; border-radius: 12px; margin: 4px 0; color: #4fc3f7;'><b>Вы:</b> {text}</div>"

def get_agent_chat_style(response):
    return f"<div align='left' style='background: #2d2d2d; padding: 8px 12px; border-radius: 12px; margin: 4px 0; color: #e0e0e0;'><b>Агент:</b> {response}</div>"