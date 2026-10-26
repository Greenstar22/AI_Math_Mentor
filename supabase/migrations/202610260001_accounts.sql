-- Apply in SQL Editor as the database owner. No hosted execution is automatic.
BEGIN;
DO $$
DECLARE t text; actual text[]; expected jsonb := '{
  "profiles":["user_id","display_name","grade_band","school_class","preferred_feedback","accessibility_notes","theme","current_levels","created_at","updated_at"],
  "attempts":["attempt_id","user_id","problem_id","problem_version","topic","concept","difficulty","scoring_version","step_accuracy","coverage","overall_score","submitted_at","saved_at","problem_snapshot","payload"],
  "step_evaluations":["attempt_id","user_id","student_step_index","student_step","expected_step","matched_expected_index","is_correct","error_type","confidence","skill","explanation","skipped_expected_steps","parse_error","feedback_style","feedback_text"],
  "feedback_events":["feedback_event_id","attempt_id","user_id","student_step_index","context_key","feedback_style","reward","created_at"]
}'::jsonb;
BEGIN
  FOREACH t IN ARRAY ARRAY['profiles','attempts','step_evaluations','feedback_events'] LOOP
    IF pg_catalog.to_regclass('public.' || t) IS NOT NULL AND
       pg_catalog.obj_description(pg_catalog.to_regclass('public.' || t), 'pg_class') IS DISTINCT FROM 'mathmentor_accounts_v1' THEN
      RAISE EXCEPTION 'Incompatible existing table public.%. Review its schema before applying accounts migration.', t;
    END IF;
    IF pg_catalog.to_regclass('public.' || t) IS NOT NULL THEN
      SELECT pg_catalog.array_agg(column_name::text ORDER BY column_name) INTO actual
        FROM information_schema.columns WHERE table_schema='public' AND table_name=t;
      IF actual IS DISTINCT FROM ARRAY(SELECT pg_catalog.jsonb_array_elements_text(expected->t) ORDER BY 1) THEN
        RAISE EXCEPTION 'Incompatible existing columns in public.%. No changes applied.', t;
      END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_policies WHERE schemaname='public' AND tablename=t
                 AND policyname NOT IN ('owner_select','owner_insert','owner_update')) THEN
        RAISE EXCEPTION 'Unexpected existing policies in public.%. Review them before rerunning.', t;
      END IF;
    END IF;
  END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS public.profiles (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text NOT NULL DEFAULT 'Student' CHECK (length(btrim(display_name)) > 0 AND length(display_name) <= 80),
  grade_band text NOT NULL DEFAULT 'Grades 9-12' CHECK (length(grade_band) <= 80),
  school_class text NOT NULL DEFAULT '' CHECK (length(school_class) <= 120),
  preferred_feedback text NOT NULL DEFAULT 'socratic' CHECK (preferred_feedback IN ('socratic','concise_hint','worked_example')),
  accessibility_notes text NOT NULL DEFAULT '' CHECK (length(accessibility_notes) <= 1000),
  theme text NOT NULL DEFAULT 'Dark' CHECK (theme IN ('Dark','Light')),
  current_levels jsonb NOT NULL DEFAULT '{"Algebra 1":"beginner","Geometry":"beginner","Algebra 2":"beginner","Precalculus":"beginner","Calculus":"beginner"}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(current_levels) = 'object' AND
    current_levels ?& ARRAY['Algebra 1','Geometry','Algebra 2','Precalculus','Calculus'] AND
    current_levels - ARRAY['Algebra 1','Geometry','Algebra 2','Precalculus','Calculus'] = '{}'::jsonb AND
    current_levels->>'Algebra 1' IN ('beginner','intermediate','advanced') AND
    current_levels->>'Geometry' IN ('beginner','intermediate','advanced') AND
    current_levels->>'Algebra 2' IN ('beginner','intermediate','advanced') AND
    current_levels->>'Precalculus' IN ('beginner','intermediate','advanced') AND
    current_levels->>'Calculus' IN ('beginner','intermediate','advanced') AND
    NOT current_levels @> '{"Algebra 1":null}' AND NOT current_levels @> '{"Geometry":null}' AND
    NOT current_levels @> '{"Algebra 2":null}' AND NOT current_levels @> '{"Precalculus":null}' AND NOT current_levels @> '{"Calculus":null}')
);
COMMENT ON TABLE public.profiles IS 'mathmentor_accounts_v1';
CREATE TABLE IF NOT EXISTS public.attempts (
  attempt_id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
  problem_id text NOT NULL CHECK (length(problem_id) > 0),
  problem_version text NOT NULL CHECK (problem_version ~ '^[0-9a-f]{64}$'),
  topic text NOT NULL CHECK (topic IN ('Algebra 1','Geometry','Algebra 2','Precalculus','Calculus')),
  concept text NOT NULL CHECK (length(concept) > 0), difficulty integer NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  scoring_version text NOT NULL CHECK (scoring_version = 'v1'),
  step_accuracy double precision NOT NULL CHECK (step_accuracy BETWEEN 0 AND 1),
  coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
  overall_score double precision NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  submitted_at timestamptz NOT NULL, saved_at timestamptz NOT NULL DEFAULT now(),
  problem_snapshot jsonb NOT NULL CHECK (jsonb_typeof(problem_snapshot) = 'object'),
  -- Immutable original request allows exact, concurrency-safe retry comparisons.
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  UNIQUE(attempt_id, user_id)
);
COMMENT ON TABLE public.attempts IS 'mathmentor_accounts_v1';
CREATE TABLE IF NOT EXISTS public.step_evaluations (
  attempt_id uuid NOT NULL, user_id uuid NOT NULL,
  student_step_index integer NOT NULL CHECK (student_step_index > 0),
  student_step text NOT NULL, expected_step text, matched_expected_index integer CHECK (matched_expected_index >= 0),
  is_correct boolean NOT NULL, error_type text NOT NULL,
  confidence double precision NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  skill text NOT NULL, explanation text NOT NULL,
  skipped_expected_steps jsonb NOT NULL CHECK (jsonb_typeof(skipped_expected_steps) = 'array'),
  parse_error text, feedback_style text NOT NULL CHECK (feedback_style IN ('socratic','concise_hint','worked_example')),
  feedback_text text NOT NULL,
  PRIMARY KEY(attempt_id, student_step_index),
  FOREIGN KEY(attempt_id, user_id) REFERENCES public.attempts(attempt_id, user_id) ON DELETE CASCADE
);
COMMENT ON TABLE public.step_evaluations IS 'mathmentor_accounts_v1';
CREATE TABLE IF NOT EXISTS public.feedback_events (
  feedback_event_id uuid PRIMARY KEY,
  attempt_id uuid NOT NULL, user_id uuid NOT NULL, student_step_index integer NOT NULL CHECK (student_step_index > 0),
  context_key text NOT NULL, feedback_style text NOT NULL CHECK (feedback_style IN ('socratic','concise_hint','worked_example')),
  reward integer NOT NULL CHECK (reward IN (-1,1)), created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(attempt_id, student_step_index),
  FOREIGN KEY(attempt_id, user_id) REFERENCES public.attempts(attempt_id, user_id) ON DELETE CASCADE,
  FOREIGN KEY(attempt_id, student_step_index) REFERENCES public.step_evaluations(attempt_id, student_step_index) ON DELETE CASCADE
);
COMMENT ON TABLE public.feedback_events IS 'mathmentor_accounts_v1';
CREATE INDEX IF NOT EXISTS attempts_owner_time ON public.attempts(user_id, submitted_at, attempt_id);
CREATE INDEX IF NOT EXISTS steps_owner_attempt ON public.step_evaluations(user_id, attempt_id);
CREATE INDEX IF NOT EXISTS feedback_owner_time ON public.feedback_events(user_id, created_at);

CREATE OR REPLACE FUNCTION public.create_account_profile() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  INSERT INTO public.profiles(user_id) VALUES (NEW.id) ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.create_account_profile() FROM PUBLIC, anon, authenticated;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_trigger WHERE tgname='mathmentor_create_profile' AND tgrelid='auth.users'::regclass AND tgfoid <> 'public.create_account_profile()'::regprocedure) THEN
    RAISE EXCEPTION 'Incompatible existing mathmentor_create_profile trigger';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_trigger WHERE tgname='mathmentor_create_profile' AND tgrelid='auth.users'::regclass) THEN
    CREATE TRIGGER mathmentor_create_profile AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.create_account_profile();
  END IF;
END $$;
INSERT INTO public.profiles(user_id) SELECT id FROM auth.users ON CONFLICT (user_id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.touch_account_profile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'Profile ownership and creation time are immutable';
  END IF;
  NEW.updated_at = pg_catalog.now();
  RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.touch_account_profile() FROM PUBLIC, anon, authenticated;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_trigger WHERE tgname='mathmentor_profile_updated' AND tgrelid='public.profiles'::regclass AND tgfoid <> 'public.touch_account_profile()'::regprocedure) THEN
    RAISE EXCEPTION 'Incompatible existing mathmentor_profile_updated trigger';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_trigger WHERE tgname='mathmentor_profile_updated' AND tgrelid='public.profiles'::regclass) THEN
    CREATE TRIGGER mathmentor_profile_updated BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.touch_account_profile();
  END IF;
END $$;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.step_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.profiles, public.attempts, public.step_evaluations, public.feedback_events FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.profiles, public.attempts, public.step_evaluations, public.feedback_events TO authenticated;
GRANT UPDATE(display_name,grade_band,school_class,preferred_feedback,accessibility_notes,theme,current_levels) ON public.profiles TO authenticated;
GRANT INSERT(attempt_id,user_id,problem_id,problem_version,topic,concept,difficulty,scoring_version,step_accuracy,coverage,overall_score,submitted_at,problem_snapshot,payload) ON public.attempts TO authenticated;
GRANT INSERT ON public.step_evaluations TO authenticated;
-- created_at is the original rating time, including imported guest ratings.
GRANT INSERT(feedback_event_id,attempt_id,user_id,student_step_index,context_key,feedback_style,reward,created_at) ON public.feedback_events TO authenticated;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['profiles','attempts','step_evaluations','feedback_events'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policies WHERE schemaname='public' AND tablename=t AND policyname='owner_select') THEN
      EXECUTE pg_catalog.format('CREATE POLICY owner_select ON public.%I FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()))',t);
    END IF;
    IF t <> 'profiles' AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policies WHERE schemaname='public' AND tablename=t AND policyname='owner_insert') THEN
      EXECUTE pg_catalog.format('CREATE POLICY owner_insert ON public.%I FOR INSERT TO authenticated WITH CHECK (user_id = (SELECT auth.uid()))',t);
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policies WHERE schemaname='public' AND tablename='profiles' AND policyname='owner_update') THEN
    CREATE POLICY owner_update ON public.profiles FOR UPDATE TO authenticated
      USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.record_feedback(p_attempt_id uuid, p_rating jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE owner uuid := auth.uid(); inserted integer;
BEGIN
  IF owner IS NULL THEN RAISE EXCEPTION 'Authentication required'; END IF;
  IF pg_catalog.jsonb_typeof(p_rating) IS DISTINCT FROM 'object' OR
     NOT p_rating ?& ARRAY['feedback_event_id','student_step_index','context_key','feedback_style','reward','created_at'] OR
     p_rating - ARRAY['feedback_event_id','student_step_index','context_key','feedback_style','reward','created_at'] <> '{}'::jsonb THEN
    RAISE EXCEPTION 'Invalid rating fields';
  END IF;
  IF pg_catalog.jsonb_typeof(p_rating->'reward') IS DISTINCT FROM 'number' OR
     pg_catalog.jsonb_typeof(p_rating->'student_step_index') IS DISTINCT FROM 'number' OR
     p_rating->>'context_key' IS NULL OR p_rating->>'created_at' IS NULL OR
     NOT EXISTS (SELECT 1 FROM public.step_evaluations WHERE attempt_id=p_attempt_id AND user_id=owner AND student_step_index=(p_rating->>'student_step_index')::integer) THEN
    RAISE EXCEPTION 'Invalid or unavailable evaluated step';
  END IF;
  INSERT INTO public.feedback_events(feedback_event_id,attempt_id,user_id,student_step_index,context_key,feedback_style,reward,created_at)
  VALUES ((p_rating->>'feedback_event_id')::uuid,p_attempt_id,owner,(p_rating->>'student_step_index')::integer,
          p_rating->>'context_key',p_rating->>'feedback_style',(p_rating->>'reward')::integer,(p_rating->>'created_at')::timestamptz)
  ON CONFLICT(attempt_id,student_step_index) DO NOTHING;
  GET DIAGNOSTICS inserted = ROW_COUNT;
  RETURN inserted = 1;
EXCEPTION WHEN unique_violation THEN
  RAISE EXCEPTION 'Rating could not be saved' USING ERRCODE='P0001';
END $$;
REVOKE ALL ON FUNCTION public.record_feedback(uuid,jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.record_feedback(uuid,jsonb) TO authenticated;

CREATE OR REPLACE FUNCTION public.save_attempts(p_attempts jsonb) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE owner uuid := auth.uid(); a jsonb; e jsonb; r jsonb; aid uuid; prior jsonb; indices integer[];
DECLARE fields text[] := ARRAY['attempt_id','problem_id','problem_version','topic','concept','difficulty','scoring_version','step_accuracy','coverage','overall_score','submitted_at','problem_snapshot','evaluations','ratings'];
DECLARE step_fields text[] := ARRAY['student_step_index','student_step','expected_step','matched_expected_index','is_correct','error_type','confidence','skill','explanation','skipped_expected_steps','parse_error','feedback_style','feedback_text'];
BEGIN
  IF owner IS NULL THEN RAISE EXCEPTION 'Authentication required'; END IF;
  IF pg_catalog.jsonb_typeof(p_attempts) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Attempts must be an array'; END IF;
  -- Consistent lock ordering prevents batch retry deadlocks. RLS still governs every query.
  FOR aid IN SELECT DISTINCT (value->>'attempt_id')::uuid FROM pg_catalog.jsonb_array_elements(p_attempts) ORDER BY 1 LOOP
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(aid::text,0));
  END LOOP;
  FOR a IN SELECT value FROM pg_catalog.jsonb_array_elements(p_attempts) LOOP
    IF pg_catalog.jsonb_typeof(a) IS DISTINCT FROM 'object' OR NOT a ?& fields OR a - fields <> '{}'::jsonb THEN RAISE EXCEPTION 'Invalid attempt fields'; END IF;
    aid := (a->>'attempt_id')::uuid;
    IF aid IS NULL OR pg_catalog.jsonb_typeof(a->'evaluations') IS DISTINCT FROM 'array' OR
       pg_catalog.jsonb_array_length(a->'evaluations')=0 OR pg_catalog.jsonb_typeof(a->'ratings') IS DISTINCT FROM 'array' OR
       pg_catalog.jsonb_typeof(a->'problem_snapshot') IS DISTINCT FROM 'object' OR
       NOT (a->'problem_snapshot') ?& ARRAY['problem_id','topic','concept','grade_band','difficulty','prompt','expected_steps','final_answer','hints'] OR
       (a->'problem_snapshot') - ARRAY['problem_id','topic','concept','grade_band','difficulty','prompt','expected_steps','final_answer','hints'] <> '{}'::jsonb OR
       a->>'submitted_at' IS NULL OR
       pg_catalog.jsonb_typeof(a->'step_accuracy') IS DISTINCT FROM 'number' OR
       pg_catalog.jsonb_typeof(a->'coverage') IS DISTINCT FROM 'number' OR
       pg_catalog.jsonb_typeof(a->'overall_score') IS DISTINCT FROM 'number' OR
       pg_catalog.jsonb_typeof(a->'difficulty') IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'Invalid attempt structure'; END IF;
    IF (a->'problem_snapshot')->>'problem_id' IS DISTINCT FROM a->>'problem_id' OR
       (a->'problem_snapshot')->>'topic' IS DISTINCT FROM a->>'topic' OR
       (a->'problem_snapshot')->>'concept' IS DISTINCT FROM a->>'concept' OR
       (a->'problem_snapshot')->>'difficulty' IS DISTINCT FROM a->>'difficulty' THEN RAISE EXCEPTION 'Snapshot metadata mismatch'; END IF;
    IF pg_catalog.jsonb_typeof(a->'problem_snapshot'->'prompt') IS DISTINCT FROM 'string' OR
       pg_catalog.jsonb_typeof(a->'problem_snapshot'->'grade_band') IS DISTINCT FROM 'string' OR
       pg_catalog.jsonb_typeof(a->'problem_snapshot'->'final_answer') IS DISTINCT FROM 'string' OR
       pg_catalog.jsonb_typeof(a->'problem_snapshot'->'expected_steps') IS DISTINCT FROM 'array' OR
       pg_catalog.jsonb_typeof(a->'problem_snapshot'->'hints') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Invalid snapshot fields'; END IF;
    IF pg_catalog.jsonb_array_length(a->'problem_snapshot'->'expected_steps')=0 OR
       EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(a->'problem_snapshot'->'hints') h WHERE pg_catalog.jsonb_typeof(h.value) IS DISTINCT FROM 'string') OR
       EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(a->'problem_snapshot'->'expected_steps') s
         WHERE pg_catalog.jsonb_typeof(s.value) IS DISTINCT FROM 'object' OR
               NOT s.value ?& ARRAY['math','skill','explanation'] OR
               s.value - ARRAY['math','skill','explanation'] <> '{}'::jsonb OR
               pg_catalog.jsonb_typeof(s.value->'math') IS DISTINCT FROM 'string' OR
               pg_catalog.jsonb_typeof(s.value->'skill') IS DISTINCT FROM 'string' OR
               pg_catalog.jsonb_typeof(s.value->'explanation') IS DISTINCT FROM 'string') THEN
      RAISE EXCEPTION 'Invalid reference steps or hints';
    END IF;
    SELECT payload INTO prior FROM public.attempts WHERE attempt_id=aid AND user_id=owner;
    IF FOUND THEN
      IF prior IS DISTINCT FROM a THEN RAISE EXCEPTION 'Conflicting attempt payload'; END IF;
      CONTINUE;
    END IF;
    INSERT INTO public.attempts(attempt_id,user_id,problem_id,problem_version,topic,concept,difficulty,scoring_version,step_accuracy,coverage,overall_score,submitted_at,problem_snapshot,payload)
    VALUES (aid,owner,a->>'problem_id',a->>'problem_version',a->>'topic',a->>'concept',(a->>'difficulty')::integer,a->>'scoring_version',
            (a->>'step_accuracy')::double precision,(a->>'coverage')::double precision,(a->>'overall_score')::double precision,
            (a->>'submitted_at')::timestamptz,a->'problem_snapshot',a);
    indices := ARRAY[]::integer[];
    FOR e IN SELECT value FROM pg_catalog.jsonb_array_elements(a->'evaluations') LOOP
      IF pg_catalog.jsonb_typeof(e) IS DISTINCT FROM 'object' OR NOT e ?& step_fields OR e - step_fields <> '{}'::jsonb OR
         pg_catalog.jsonb_typeof(e->'student_step_index') IS DISTINCT FROM 'number' OR
         pg_catalog.jsonb_typeof(e->'is_correct') IS DISTINCT FROM 'boolean' OR
         pg_catalog.jsonb_typeof(e->'confidence') IS DISTINCT FROM 'number' OR
         pg_catalog.jsonb_typeof(e->'skipped_expected_steps') IS DISTINCT FROM 'array' OR
         pg_catalog.jsonb_typeof(e->'student_step') IS DISTINCT FROM 'string' OR
         pg_catalog.jsonb_typeof(e->'error_type') IS DISTINCT FROM 'string' OR
         pg_catalog.jsonb_typeof(e->'skill') IS DISTINCT FROM 'string' OR
         pg_catalog.jsonb_typeof(e->'explanation') IS DISTINCT FROM 'string' OR
         pg_catalog.jsonb_typeof(e->'feedback_text') IS DISTINCT FROM 'string' OR
         pg_catalog.jsonb_typeof(e->'expected_step') NOT IN ('string','null') OR
         pg_catalog.jsonb_typeof(e->'parse_error') NOT IN ('string','null') OR
         pg_catalog.jsonb_typeof(e->'matched_expected_index') NOT IN ('number','null') OR
         (e->>'student_step_index')::integer = ANY(indices) THEN RAISE EXCEPTION 'Invalid evaluation'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(e->'skipped_expected_steps') s WHERE pg_catalog.jsonb_typeof(s.value) IS DISTINCT FROM 'string') THEN
        RAISE EXCEPTION 'Invalid skipped expected steps';
      END IF;
      indices := pg_catalog.array_append(indices,(e->>'student_step_index')::integer);
      INSERT INTO public.step_evaluations(attempt_id,user_id,student_step_index,student_step,expected_step,matched_expected_index,is_correct,error_type,confidence,skill,explanation,skipped_expected_steps,parse_error,feedback_style,feedback_text)
      VALUES (aid,owner,(e->>'student_step_index')::integer,e->>'student_step',e->>'expected_step',(e->>'matched_expected_index')::integer,
              (e->>'is_correct')::boolean,e->>'error_type',(e->>'confidence')::double precision,e->>'skill',e->>'explanation',e->'skipped_expected_steps',e->>'parse_error',e->>'feedback_style',e->>'feedback_text');
    END LOOP;
    indices := ARRAY[]::integer[];
    FOR r IN SELECT value FROM pg_catalog.jsonb_array_elements(a->'ratings') LOOP
      IF (r->>'student_step_index')::integer = ANY(indices) THEN RAISE EXCEPTION 'Duplicate imported rating'; END IF;
      indices := pg_catalog.array_append(indices,(r->>'student_step_index')::integer);
      PERFORM public.record_feedback(aid,r);
    END LOOP;
  END LOOP;
EXCEPTION WHEN unique_violation THEN
  -- Does not reveal whether a conflicting UUID belongs to another account.
  RAISE EXCEPTION 'Attempt could not be saved: unavailable or conflicting identifier' USING ERRCODE='P0001';
END $$;
REVOKE ALL ON FUNCTION public.save_attempts(jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.save_attempts(jsonb) TO authenticated;
COMMIT;
