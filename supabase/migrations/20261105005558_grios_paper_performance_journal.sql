CREATE TABLE IF NOT EXISTS public.grios_paper_ideas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint text NOT NULL UNIQUE
        CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    asset_key text NOT NULL,
    symbol text NOT NULL,
    asset_class text NOT NULL,
    provider text NOT NULL,
    data_as_of date NOT NULL,
    recorded_at timestamptz NOT NULL,
    entry_price numeric NOT NULL CHECK (entry_price > 0),
    technical_score numeric CHECK (technical_score >= 0 AND technical_score <= 100),
    factor_coverage_pct integer NOT NULL
        CHECK (factor_coverage_pct >= 0 AND factor_coverage_pct <= 100),
    decision text NOT NULL CHECK (decision IN ('WATCH_ONLY', 'NO_RANK')),
    thesis text NOT NULL,
    invalidation text NOT NULL,
    benchmark_symbol text,
    benchmark_asset_key text,
    benchmark_entry_price numeric CHECK (benchmark_entry_price IS NULL OR benchmark_entry_price > 0),
    assumed_round_trip_cost_bps numeric
        CHECK (assumed_round_trip_cost_bps IS NULL OR assumed_round_trip_cost_bps >= 0),
    model_version text NOT NULL DEFAULT 'grios-v15-scanner-v1',
    source_revision text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (asset_key, data_as_of)
);

CREATE TABLE IF NOT EXISTS public.grios_paper_evaluations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id uuid NOT NULL
        REFERENCES public.grios_paper_ideas(id) ON DELETE CASCADE,
    checkpoint_days smallint NOT NULL
        CHECK (checkpoint_days IN (1, 7, 30, 90, 365)),
    evaluated_at timestamptz NOT NULL,
    observed_at date NOT NULL,
    price numeric NOT NULL CHECK (price > 0),
    return_pct numeric NOT NULL,
    benchmark_price numeric CHECK (benchmark_price IS NULL OR benchmark_price > 0),
    benchmark_return_pct numeric,
    excess_return_pct numeric,
    assumed_round_trip_cost_bps numeric
        CHECK (assumed_round_trip_cost_bps IS NULL OR assumed_round_trip_cost_bps >= 0),
    estimated_cost_pct numeric,
    net_return_pct numeric,
    source_revision text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (idea_id, checkpoint_days)
);

CREATE INDEX IF NOT EXISTS grios_paper_ideas_recorded_at_idx
    ON public.grios_paper_ideas (recorded_at DESC);
CREATE INDEX IF NOT EXISTS grios_paper_ideas_asset_date_idx
    ON public.grios_paper_ideas (asset_key, data_as_of DESC);
CREATE INDEX IF NOT EXISTS grios_paper_evaluations_checkpoint_idx
    ON public.grios_paper_evaluations (checkpoint_days, observed_at DESC);

ALTER TABLE public.grios_paper_ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grios_paper_evaluations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.grios_paper_ideas FROM anon, authenticated;
REVOKE ALL ON TABLE public.grios_paper_evaluations FROM anon, authenticated;
GRANT ALL ON TABLE public.grios_paper_ideas TO service_role;
GRANT ALL ON TABLE public.grios_paper_evaluations TO service_role;
