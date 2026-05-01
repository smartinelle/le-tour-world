-- Le-Tour Multi-User Database Schema
-- Run this in Supabase SQL Editor after creating your project

-- ============================================================================
-- User Profiles (extends Supabase auth.users)
-- ============================================================================
CREATE TABLE profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    name TEXT,
    email TEXT,
    avatar_url TEXT,
    
    -- Cycling metrics
    ftp_w INTEGER DEFAULT 250,
    mass_kg FLOAT DEFAULT 75.0,
    max_hr_bpm INTEGER,
    
    -- Physics parameters (for SIM mode calculations)
    cda_m2 FLOAT DEFAULT 0.33,
    crr FLOAT DEFAULT 0.0045,
    
    -- Preferences
    units TEXT DEFAULT 'metric' CHECK (units IN ('metric', 'imperial')),
    default_erg_power_w INTEGER DEFAULT 150,
    default_sim_grade_pct FLOAT DEFAULT 0.0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Training Sessions
-- ============================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users NOT NULL,
    
    -- Session info
    mode TEXT NOT NULL CHECK (mode IN ('free', 'erg', 'sim')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_s FLOAT,
    
    -- Device info
    trainer_name TEXT,
    hr_device_name TEXT,
    
    -- Statistics
    total_distance_m FLOAT,
    avg_power_w FLOAT,
    max_power_w INTEGER,
    avg_cadence_rpm FLOAT,
    avg_speed_mps FLOAT,
    avg_hr_bpm FLOAT,
    max_hr_bpm INTEGER,
    
    -- Training metrics
    normalized_power_w FLOAT,
    intensity_factor FLOAT,
    training_stress_score FLOAT,
    
    -- Settings at session time
    user_ftp_w INTEGER,
    user_mass_kg FLOAT,
    erg_target_power_w INTEGER,
    sim_grade_pct FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Training Samples (time-series data)
-- ============================================================================
CREATE TABLE samples (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions ON DELETE CASCADE NOT NULL,
    
    timestamp TIMESTAMPTZ NOT NULL,
    elapsed_s FLOAT NOT NULL,
    
    -- Core metrics
    power_w INTEGER,
    cadence_rpm INTEGER,
    speed_mps FLOAT,
    distance_m FLOAT,
    hr_bpm INTEGER,
    
    -- Mode-specific
    erg_target_power_w INTEGER,
    sim_grade_pct FLOAT
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_start_time ON sessions(start_time DESC);
CREATE INDEX idx_samples_session_id ON samples(session_id);
CREATE INDEX idx_samples_timestamp ON samples(timestamp);

-- ============================================================================
-- Row-Level Security (RLS) Policies
-- Users can only access their own data
-- ============================================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE samples ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Sessions policies
CREATE POLICY "Users can view own sessions"
    ON sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
    ON sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
    ON sessions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
    ON sessions FOR DELETE
    USING (auth.uid() = user_id);

-- Samples policies (access through session ownership)
CREATE POLICY "Users can access own samples"
    ON samples FOR ALL
    USING (
        session_id IN (
            SELECT id FROM sessions WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- Auto-create profile on user signup
-- ============================================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================================
-- Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
