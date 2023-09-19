import requests
import base64
from django.conf import settings


#### default smtp send function
def smtp_send(
    subject,
    emails,
    sender="No Reply <no-reply@newtech.co.nz>",
    html_body="",
    body="",
    attachments=None,
):

    data = {
        "to": emails,
        "sender": sender,
        "subject": subject,
        "text_body": body,
        "html_body": html_body,
        "api_key": settings.SMTP_API_KEY,
    }
    if attachments:
        attachments_data = []
        for attachment in attachments:
            file_name, file_data, content_type = attachment
            file_encoded = base64.b64encode(file_data).decode('utf-8')
            attachments_data.append({"filename": file_name, "fileblob": file_encoded, "content_type": content_type})
        data["attachments"] = attachments_data

    res = requests.post(
        settings.SMTP_API_URL,
        json=data,
        headers={"Content-type": "application/json"},
    )

    if res.status_code != 200:
        print(res.__dict__)
        raise
    return res
