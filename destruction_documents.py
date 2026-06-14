"""Private PDF evidence for destruction batches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
import uuid


DESTRUCTION_DOCUMENT_BUCKET = "destruction-minutes"
MAX_DESTRUCTION_PDF_BYTES = 10 * 1024 * 1024
SIGNED_URL_TTL_SECONDS = 10 * 60


@dataclass(frozen=True)
class ValidatedPDF:
    file_name: str
    mime_type: str
    content: bytes

    @property
    def size_bytes(self) -> int:
        return len(self.content)


def validate_destruction_pdf(uploaded_file) -> ValidatedPDF:
    if uploaded_file is None:
        raise ValueError("Bắt buộc tải lên biên bản PDF.")

    file_name = str(getattr(uploaded_file, "name", "") or "").strip()
    mime_type = str(getattr(uploaded_file, "type", "") or "").lower().strip()
    if not file_name.lower().endswith(".pdf") or mime_type != "application/pdf":
        raise ValueError("Biên bản phải đúng định dạng PDF.")

    content = uploaded_file.getvalue()
    if len(content) > MAX_DESTRUCTION_PDF_BYTES:
        raise ValueError("Biên bản PDF không được vượt quá 10 MB.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("Nội dung file PDF không hợp lệ.")

    return ValidatedPDF(file_name=file_name, mime_type=mime_type, content=content)


def build_destruction_storage_path(farm: str, document_date, document_uuid: str | None = None) -> str:
    parsed_date = document_date
    if not isinstance(parsed_date, (date, datetime)):
        parsed_date = datetime.fromisoformat(str(document_date)).date()
    if isinstance(parsed_date, datetime):
        parsed_date = parsed_date.date()

    farm_segment = re.sub(r"[^A-Za-z0-9_-]+", "-", str(farm).strip()).strip("-") or "Unknown-Farm"
    file_id = document_uuid or str(uuid.uuid4())
    return f"{farm_segment}/{parsed_date.year:04d}/{parsed_date.month:02d}/{file_id}.pdf"


def _response_rows(response) -> list:
    if isinstance(response, dict):
        data = response.get("data", response)
    else:
        data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def persist_destruction_batch(
    service_client,
    *,
    pdf: ValidatedPDF,
    storage_path: str,
    document_metadata: dict,
    destruction_rows: list[dict],
) -> dict:
    if not destruction_rows:
        raise ValueError("Danh sách xuất hủy đang trống.")

    bucket = service_client.storage.from_(DESTRUCTION_DOCUMENT_BUCKET)
    uploaded = False
    document_id = None
    try:
        bucket.upload(
            storage_path,
            pdf.content,
            {"content-type": "application/pdf", "upsert": "false"},
        )
        uploaded = True

        metadata = {
            **document_metadata,
            "storage_path": storage_path,
            "original_file_name": pdf.file_name,
            "file_size_bytes": pdf.size_bytes,
            "mime_type": pdf.mime_type,
        }
        document_response = service_client.table("destruction_documents").insert(metadata).execute()
        document_rows = _response_rows(document_response)
        if not document_rows or not document_rows[0].get("id"):
            raise RuntimeError("Không tạo được metadata biên bản xuất hủy.")
        document_id = document_rows[0]["id"]

        rows_with_document = [{**row, "document_id": document_id} for row in destruction_rows]
        service_client.table("destruction_logs").insert(rows_with_document).execute()
        return {
            "document_id": document_id,
            "storage_path": storage_path,
            "inserted_rows": len(rows_with_document),
        }
    except Exception:
        if document_id:
            try:
                service_client.table("destruction_documents").delete().eq("id", document_id).execute()
            except Exception:
                pass
        if uploaded:
            try:
                bucket.remove([storage_path])
            except Exception:
                pass
        raise


def create_destruction_document_signed_url(service_client, document_id: str) -> str:
    response = (
        service_client.table("destruction_documents")
        .select("storage_path")
        .eq("id", document_id)
        .limit(1)
        .execute()
    )
    rows = _response_rows(response)
    if not rows or not rows[0].get("storage_path"):
        raise ValueError("Không tìm thấy biên bản PDF.")

    signed_response = service_client.storage.from_(DESTRUCTION_DOCUMENT_BUCKET).create_signed_url(
        rows[0]["storage_path"], SIGNED_URL_TTL_SECONDS
    )
    if isinstance(signed_response, dict):
        signed_url = signed_response.get("signedURL") or signed_response.get("signedUrl")
    else:
        signed_url = getattr(signed_response, "signedURL", None) or getattr(signed_response, "signedUrl", None)
    if not signed_url:
        raise RuntimeError("Không tạo được đường dẫn xem biên bản PDF.")
    return signed_url
