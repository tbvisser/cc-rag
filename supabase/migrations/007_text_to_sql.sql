-- Text-to-SQL: read-only SQL execution function
-- SECURITY DEFINER bypasses RLS; the generated SQL must filter by user_id.

CREATE OR REPLACE FUNCTION execute_readonly_sql(query_text TEXT, filter_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  normalized TEXT;
  result JSONB;
BEGIN
  -- Normalize whitespace for validation
  normalized := upper(trim(query_text));

  -- Must start with SELECT
  IF NOT normalized LIKE 'SELECT%' THEN
    RAISE EXCEPTION 'Only SELECT queries are allowed';
  END IF;

  -- Block forbidden keywords
  IF normalized ~ '\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b' THEN
    RAISE EXCEPTION 'Query contains forbidden keywords';
  END IF;

  -- Execute with LIMIT 100 safety net
  EXECUTE format('SELECT jsonb_agg(row_to_json(t)) FROM (%s LIMIT 100) t', query_text)
    INTO result;

  -- Return empty array instead of null
  RETURN COALESCE(result, '[]'::jsonb);
END;
$$;
