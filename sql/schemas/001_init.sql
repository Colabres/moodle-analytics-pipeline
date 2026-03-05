
CREATE SCHEMA IF NOT EXISTS moodle;

CREATE TABLE IF NOT EXISTS moodle.ingest_file (
  file_id      BIGSERIAL PRIMARY KEY,
  filename     TEXT NOT NULL,
  uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS moodle.event (
  id           BIGSERIAL PRIMARY KEY,
  file_id      BIGINT NOT NULL REFERENCES moodle.ingest_file(file_id),

  ts           TIMESTAMPTZ NOT NULL,     -- Aika
  user_id      BIGINT,                  -- only store confirmed numeric IDs (else NULL)

  context      TEXT,                    -- Tapahtuman konteksti
  component    TEXT,                    -- Komponentti
  event_name   TEXT NOT NULL,           -- Tapahtuman nimi

  description  TEXT,                    -- Kuvaus (raw for now)
  origin       TEXT                     -- Alkuperä
);

CREATE TABLE IF NOT EXISTS moodle.user_dim (
  user_id   BIGINT PRIMARY KEY,
  is_admin  BOOLEAN NOT NULL DEFAULT FALSE,
  is_active BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_event_ts ON moodle.event(ts);
CREATE INDEX IF NOT EXISTS ix_event_file_id ON moodle.event(file_id);
CREATE INDEX IF NOT EXISTS ix_event_user_id ON moodle.event(user_id);
CREATE INDEX IF NOT EXISTS ix_event_event_name ON moodle.event(event_name);
CREATE INDEX IF NOT EXISTS ix_event_component ON moodle.event(component);