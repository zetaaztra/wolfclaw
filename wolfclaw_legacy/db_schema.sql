-- Wolfclaw Multi-Tenant Schema (PostgreSQL for Supabase)
-- Execute this entirely in your Supabase SQL Editor

-- 1. Create custom types
CREATE TYPE bot_model AS ENUM ('gpt-4o', 'gpt-4o-mini', 'claude-3-5-sonnet-20240620', 'meta/llama-3.1-70b-instruct');

-- 2. Create workspaces table (to group bots and settings)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create bots table (replaces local SOUL.md and MEMORY.md files)
CREATE TABLE bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    model bot_model NOT NULL DEFAULT 'gpt-4o',
    soul_prompt TEXT DEFAULT 'You are a helpful AI assistant.',
    user_context TEXT DEFAULT '',
    memory TEXT DEFAULT '',
    telegram_token TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Create the Vault table (for encrypted API keys and SSH creds)
-- In a true production environment, you should use Supabase Vault (pgsodium)
-- For this prototype SaaS build, we will store them as text and encrypt via Python cryptography before transit.
CREATE TABLE vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    openai_key TEXT,
    anthropic_key TEXT,
    nvidia_key TEXT,
    google_key TEXT,
    ssh_host TEXT,
    ssh_port TEXT DEFAULT '22',
    ssh_user TEXT DEFAULT 'ubuntu',
    ssh_password TEXT,
    ssh_key_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Enable Row Level Security (RLS) policies
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE bots ENABLE ROW LEVEL SECURITY;
ALTER TABLE vault ENABLE ROW LEVEL SECURITY;

-- Workspaces Policy: Users can only see/edit their own workspaces
CREATE POLICY "Users can manage their own workspaces" ON workspaces
    FOR ALL USING (auth.uid() = user_id);

-- Bots Policy: Users can only see/edit bots in their workspaces
CREATE POLICY "Users can manage bots in their workspaces" ON bots
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM workspaces WHERE workspaces.id = bots.workspace_id AND workspaces.user_id = auth.uid()
        )
    );

-- Vault Policy: Users can only see/edit their own vault
CREATE POLICY "Users can manage their own vault" ON vault
    FOR ALL USING (auth.uid() = user_id);
