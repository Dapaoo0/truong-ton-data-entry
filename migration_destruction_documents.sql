-- Private PDF evidence shared by all destruction rows saved in one batch.
CREATE TABLE IF NOT EXISTS public.destruction_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm TEXT NOT NULL,
    team TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    original_file_name TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760),
    mime_type TEXT NOT NULL CHECK (mime_type = 'application/pdf'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_destruction_documents_account_created
    ON public.destruction_documents (farm, team, created_at DESC);

ALTER TABLE public.destruction_documents ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.destruction_documents FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.destruction_documents TO service_role;

ALTER TABLE public.destruction_logs
    ADD COLUMN IF NOT EXISTS document_id UUID
    REFERENCES public.destruction_documents(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_destruction_logs_document_id
    ON public.destruction_logs (document_id)
    WHERE document_id IS NOT NULL;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'destruction-minutes',
    'destruction-minutes',
    FALSE,
    10485760,
    ARRAY['application/pdf']::TEXT[]
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;
