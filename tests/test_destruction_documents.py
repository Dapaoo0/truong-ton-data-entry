from types import SimpleNamespace

import pytest

from destruction_documents import (
    DESTRUCTION_DOCUMENT_BUCKET,
    MAX_DESTRUCTION_PDF_BYTES,
    build_destruction_storage_path,
    create_destruction_document_signed_url,
    persist_destruction_batch,
    validate_destruction_pdf,
)


class FakeUpload:
    def __init__(self, name="bien-ban.pdf", mime="application/pdf", content=b"%PDF-1.7\nbody"):
        self.name = name
        self.type = mime
        self.size = len(content)
        self._content = content

    def getvalue(self):
        return self._content


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    def __init__(self, service, table_name):
        self.service = service
        self.table_name = table_name
        self.action = None
        self.payload = None
        self.filters = []

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def select(self, columns):
        self.action = "select"
        self.payload = columns
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, value):
        return self

    def execute(self):
        self.service.table_calls.append((self.table_name, self.action, self.payload, self.filters))
        if self.table_name == "destruction_logs" and self.action == "insert" and self.service.fail_log_insert:
            raise RuntimeError("bulk insert failed")
        if self.table_name == "destruction_documents" and self.action == "insert":
            return FakeResponse([{"id": "doc-123", **self.payload}])
        if self.table_name == "destruction_documents" and self.action == "select":
            return FakeResponse([{"storage_path": "Farm-126/2026/06/file.pdf"}])
        return FakeResponse([])


class FakeBucket:
    def __init__(self, service):
        self.service = service

    def upload(self, path, file, file_options=None):
        self.service.uploads.append((path, file, file_options))
        return SimpleNamespace(path=path)

    def remove(self, paths):
        self.service.removals.append(paths)
        return []

    def create_signed_url(self, path, expires_in):
        self.service.signed_calls.append((path, expires_in))
        return SimpleNamespace(signedURL=f"https://signed.example/{path}")


class FakeStorage:
    def __init__(self, service):
        self.service = service

    def from_(self, bucket_name):
        self.service.bucket_names.append(bucket_name)
        return FakeBucket(self.service)


class FakeServiceClient:
    def __init__(self, fail_log_insert=False):
        self.fail_log_insert = fail_log_insert
        self.uploads = []
        self.removals = []
        self.signed_calls = []
        self.bucket_names = []
        self.table_calls = []
        self.storage = FakeStorage(self)

    def table(self, table_name):
        return FakeTableQuery(self, table_name)


def test_validate_destruction_pdf_accepts_a_real_pdf_header():
    pdf = validate_destruction_pdf(FakeUpload())

    assert pdf.file_name == "bien-ban.pdf"
    assert pdf.mime_type == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (None, "(?i)bắt buộc"),
        (FakeUpload(name="bien-ban.png"), "định dạng PDF"),
        (FakeUpload(mime="image/png"), "định dạng PDF"),
        (FakeUpload(content=b"not a pdf"), "không hợp lệ"),
        (FakeUpload(content=b"%PDF-" + b"x" * MAX_DESTRUCTION_PDF_BYTES), "10 MB"),
    ],
)
def test_validate_destruction_pdf_rejects_invalid_files(upload, message):
    with pytest.raises(ValueError, match=message):
        validate_destruction_pdf(upload)


def test_storage_path_uses_farm_year_month_and_uuid():
    path = build_destruction_storage_path("Farm 126", "2026-06-05", document_uuid="abc-123")

    assert path == "Farm-126/2026/06/abc-123.pdf"


def test_persist_batch_uploads_once_and_shares_document_id():
    service = FakeServiceClient()
    pdf = validate_destruction_pdf(FakeUpload())
    rows = [
        {"dim_lo_id": 1, "so_luong": 10},
        {"dim_lo_id": 2, "so_luong": 20},
    ]

    result = persist_destruction_batch(
        service,
        pdf=pdf,
        storage_path="Farm-126/2026/06/abc.pdf",
        document_metadata={"farm": "Farm 126", "team": "NT1"},
        destruction_rows=rows,
    )

    assert result["document_id"] == "doc-123"
    assert len(service.uploads) == 1
    log_insert = next(call for call in service.table_calls if call[0:2] == ("destruction_logs", "insert"))
    assert [row["document_id"] for row in log_insert[2]] == ["doc-123", "doc-123"]
    assert service.uploads[0][2]["content-type"] == "application/pdf"
    assert service.uploads[0][2]["upsert"] == "false"


def test_persist_batch_removes_document_and_file_when_bulk_insert_fails():
    service = FakeServiceClient(fail_log_insert=True)
    pdf = validate_destruction_pdf(FakeUpload())

    with pytest.raises(RuntimeError, match="bulk insert failed"):
        persist_destruction_batch(
            service,
            pdf=pdf,
            storage_path="Farm-126/2026/06/abc.pdf",
            document_metadata={"farm": "Farm 126", "team": "NT1"},
            destruction_rows=[{"dim_lo_id": 1, "so_luong": 10}],
        )

    assert service.removals == [["Farm-126/2026/06/abc.pdf"]]
    assert any(call[0:2] == ("destruction_documents", "delete") for call in service.table_calls)


def test_create_signed_url_uses_private_bucket_for_ten_minutes():
    service = FakeServiceClient()

    url = create_destruction_document_signed_url(service, "doc-123")

    assert url == "https://signed.example/Farm-126/2026/06/file.pdf"
    assert service.signed_calls == [("Farm-126/2026/06/file.pdf", 600)]
    assert service.bucket_names[-1] == DESTRUCTION_DOCUMENT_BUCKET
