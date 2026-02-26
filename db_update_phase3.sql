-- Phase 3 Schema Updates for Streamlit Community Cloud

-- 1. Add ssh_config jsonb column to workspaces table
ALTER TABLE workspaces 
ADD COLUMN IF NOT EXISTS ssh_config jsonb DEFAULT '{}'::jsonb;

-- 2. Add telegram_token column to bots table
ALTER TABLE bots 
ADD COLUMN IF NOT EXISTS telegram_token text;
