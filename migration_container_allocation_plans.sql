-- Migration: Persist saved container allocation plans for Kinh doanh
CREATE TABLE IF NOT EXISTS public.container_allocation_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_farm TEXT NOT NULL,
    account_team TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    mode TEXT NOT NULL,
    source_mode TEXT,
    source_label TEXT,
    source_bunches INTEGER NOT NULL DEFAULT 0,
    hands_per_bunch INTEGER NOT NULL,
    kg_per_bunch NUMERIC NOT NULL,
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    full_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_container_allocation_plans_account_active
    ON public.container_allocation_plans (account_farm, account_team, is_deleted, created_at DESC);

ALTER TABLE public.container_allocation_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all container allocation plans" ON public.container_allocation_plans;
CREATE POLICY "Allow all container allocation plans"
    ON public.container_allocation_plans
    FOR ALL
    USING (true)
    WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.container_allocation_plans TO anon, authenticated;
