-- Run this in Supabase Dashboard → SQL Editor
-- Allows the app (using anon key) to INSERT and SELECT on the transactions table.
-- For a single-user app with the key in .env this is fine. Tighten if you add Auth.

-- Allow anyone using the anon key to insert rows (your app uses this)
CREATE POLICY "Allow anon insert on transactions"
ON public.transactions
FOR INSERT
TO anon
WITH CHECK (true);

-- Allow anyone using the anon key to read rows (needed for list/summary)
CREATE POLICY "Allow anon select on transactions"
ON public.transactions
FOR SELECT
TO anon
USING (true);

-- Allow anyone using the anon key to update rows (for edit in Search tab)
CREATE POLICY "Allow anon update on transactions"
ON public.transactions
FOR UPDATE
TO anon
USING (true)
WITH CHECK (true);

-- Allow anyone using the anon key to delete rows (for delete in Search tab)
CREATE POLICY "Allow anon delete on transactions"
ON public.transactions
FOR DELETE
TO anon
USING (true);
