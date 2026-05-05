from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

AUDIO_MIME_PREFIXES = ("audio/",)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}


class DriveClient:
    def __init__(self, service_account_file: Path) -> None:
        creds = Credentials.from_service_account_file(
            str(service_account_file), scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=creds)
        self._creds = creds

    @property
    def credentials(self) -> Credentials:
        """Для повторного використання у sheets_client."""
        return self._creds

    def list_audio_files(self, folder_id: str) -> list[dict]:
        """Повертає список аудіофайлів з папки."""
        query = f"'{folder_id}' in parents and trashed = false"
        files: list[dict] = []
        page_token: str | None = None

        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, webViewLink)",
                    pageSize=100,
                    pageToken=page_token,
                )
                .execute()
            )
            for f in response.get("files", []):
                if self._is_audio(f):
                    files.append(f)
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info("Знайдено %d аудіофайлів у папці %s", len(files), folder_id)
        return files

    @staticmethod
    def _is_audio(file_meta: dict) -> bool:
        mime = file_meta.get("mimeType", "")
        if any(mime.startswith(prefix) for prefix in AUDIO_MIME_PREFIXES):
            return True
        # запасний варіант — за розширенням
        name = file_meta.get("name", "").lower()
        return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)

    def download_file(self, file_id: str, destination: Path) -> Path:
        """Завантажує файл з Drive локально."""
        request = self.service.files().get_media(fileId=file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug("  завантажено %d%%", int(status.progress() * 100))
        logger.info("Завантажено %s", destination.name)
        return destination

    # def copy_file(self, file_id: str, target_folder_id: str, new_name: str | None = None) -> dict:
    #     """Копіює файл у вказану папку (без скачування)."""
    #     body = {"parents": [target_folder_id]}
    #     if new_name:
    #         body["name"] = new_name
    #     copy = self.service.files().copy(fileId=file_id, body=body, fields="id, name, webViewLink").execute()
    #     logger.info("Скопійовано → %s (id=%s)", copy["name"], copy["id"])
    #     return copy

    # def upload_text_file(
    #     self,
    #     local_path: Path,
    #     target_folder_id: str,
    #     target_name: str | None = None,
    # ) -> dict:
    #     """Завантажує текстовий файл (наприклад, транскрипт) у папку Drive."""
    #     name = target_name or local_path.name
    #     mime, _ = mimetypes.guess_type(str(local_path))
    #     media = MediaFileUpload(str(local_path), mimetype=mime or "text/plain", resumable=False)
    #     file = (
    #         self.service.files()
    #         .create(
    #             body={"name": name, "parents": [target_folder_id]},
    #             media_body=media,
    #             fields="id, name, webViewLink",
    #         )
    #         .execute()
    #     )
    #     logger.info("Завантажено в Drive: %s", file["name"])
    #     return file

    def file_in_folder(self, folder_id: str, file_name: str) -> dict | None:
        """Перевіряє, чи є файл з таким іменем у папці (для ідемпотентності)."""
        q = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
        resp = self.service.files().list(q=q, fields="files(id, name, webViewLink)").execute()
        files = resp.get("files", [])
        return files[0] if files else None
