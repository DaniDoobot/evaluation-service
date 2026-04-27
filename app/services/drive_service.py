import io
import json
import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON no está configurado")

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON válido") from exc

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )

    return build("drive", "v3", credentials=credentials)


def upload_file_to_drive(
    file_content: bytes,
    filename: str,
    mime_type: str,
    folder_id: str,
) -> dict:
    service = get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=mime_type,
        resumable=False,
    )

    uploaded_file = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink",
            supportsAllDrives=True,
        )
        .execute()
    )

    return uploaded_file