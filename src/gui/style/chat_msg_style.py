import time


def get_client_chat_style(text):
    return f"""
    <div style="
        text-align: right;
        margin: 8px 0 8px 40px;
        animation: fadeIn 0.3s ease;
    ">
        <div style="
            display: inline-block;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6272a4, 
                stop:1 #bd93f9);
            color: #f8f8f2;
            padding: 12px 18px;
            border-radius: 18px 18px 4px 18px;
            max-width: 80%;
            font-size: 14px;
            font-family: 'Segoe UI', Arial, sans-serif;
            box-shadow: 0 2px 12px rgba(98, 114, 164, 0.3);
            border: 1px solid rgba(189, 147, 249, 0.2);
            word-wrap: break-word;
            white-space: pre-wrap;
        ">
            <div style="
                font-size: 12px;
                opacity: 0.7;
                margin-bottom: 4px;
                text-align: right;
            ">
                👤 Вы
            </div>
            <div>{text}</div>
            <div style="
                font-size: 10px;
                opacity: 0.4;
                margin-top: 4px;
                text-align: right;
            ">
                {time.strftime('%H:%M')}
            </div>
        </div>
    </div>
    """

def get_agent_chat_style(response):
    return f"""
    <div style="
        text-align: left;
        margin: 8px 40px 8px 0;
        animation: fadeIn 0.3s ease;
    ">
        <div style="
            display: inline-block;
            background: #282a36;
            color: #f8f8f2;
            padding: 12px 18px;
            border-radius: 18px 18px 18px 4px;
            max-width: 80%;
            font-size: 14px;
            font-family: 'Segoe UI', Arial, sans-serif;
            border: 1px solid #44475a;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
            word-wrap: break-word;
            white-space: pre-wrap;
        ">
            <div style="
                font-size: 12px;
                opacity: 0.7;
                margin-bottom: 4px;
                text-align: left;
            ">
                🤖 Агент
            </div>
            <div>{response}</div>
            <div style="
                font-size: 10px;
                opacity: 0.4;
                margin-top: 4px;
                text-align: left;
            ">
                {time.strftime('%H:%M')}
            </div>
        </div>
    </div>
    """