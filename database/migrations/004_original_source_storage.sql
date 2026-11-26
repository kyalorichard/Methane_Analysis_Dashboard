-- Retain the immutable original upload separately from the canonical Parquet derivative.
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_storage_key TEXT;
