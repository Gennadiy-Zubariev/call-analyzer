"""Робота з Google Drive: лістинг, копіювання, завантаження файлів."""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

# Scope-и — рівні доступу, які ми просимо у Google
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Які MIME-типи / розширення вважаємо аудіо
AUDIO_MIME_PREFIXES = ("audio/",)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}


class DriveClient:
    """Інкапсулює всю роботу з Google Drive API."""

    def __init__(self, service_account_file: Path) -> None:
        """Авторизується через service account і будує клієнта."""
        # TODO:
        # 1. створити Credentials з файлу через Credentials.from_service_account_file
        # 2. зберегти у self._creds
        # 3. створити self.service через build("drive", "v3", credentials=creds)
        raise NotImplementedError

    @property
    def credentials(self) -> Credentials:
        """Доступ до credentials для повторного використання у sheets_client."""
        # TODO: повернути self._creds
        raise NotImplementedError

    def list_audio_files(self, folder_id: str) -> list[dict]:
        """Повертає список аудіофайлів у папці."""
        # TODO:
        # 1. сформувати query "'{folder_id}' in parents and trashed = false"
        # 2. викликати self.service.files().list(...) у циклі по pageToken
        # 3. фільтрувати через self._is_audio
        # 4. повернути зібраний список
        raise NotImplementedError

    @staticmethod
    def _is_audio(file_meta: dict) -> bool:
        """Чи це аудіофайл (за MIME або розширенням)?"""
        # TODO: перевірити mimeType і розширення
        raise NotImplementedError

    def download_file(self, file_id: str, destination: Path) -> Path:
        """Завантажує файл з Drive локально."""
        # TODO:
        # 1. створити батьківську теку якщо немає
        # 2. self.service.files().get_media(fileId=file_id) -> request
        # 3. MediaIoBaseDownload + цикл next_chunk()
        # 4. повернути destination
        raise NotImplementedError

    def copy_file(self, file_id: str, target_folder_id: str, new_name: str | None = None) -> dict:
        """Копіює файл на Drive у нову папку (БЕЗ скачування)."""
        # TODO:
        # 1. body = {"parents": [target_folder_id]}, додати name якщо є
        # 2. self.service.files().copy(fileId=..., body=body, fields="id, name, webViewLink")
        # 3. повернути результат .execute()
        raise NotImplementedError

    def upload_text_file(
        self,
        local_path: Path,
        target_folder_id: str,
        target_name: str | None = None,
    ) -> dict:
        """Аплоадить локальний файл у папку Drive."""
        # TODO:
        # 1. визначити mimetype через mimetypes.guess_type
        # 2. MediaFileUpload з потрібним mimetype
        # 3. self.service.files().create(body={...}, media_body=media, fields=...)
        raise NotImplementedError

    def file_in_folder(self, folder_id: str, file_name: str) -> dict | None:
        """Чи є файл з такою назвою у папці? Повертає метадані або None."""
        # TODO:
        # 1. q = "'{folder_id}' in parents and name = '{file_name}' and trashed = false"
        # 2. self.service.files().list(q=..., fields="files(id, name, webViewLink)")
        # 3. повернути перший елемент або None
        raise NotImplementedError
