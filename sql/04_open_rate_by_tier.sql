-- Who opens: usage at the start of the year against open rate and the share who would be cut by a
-- "stop emailing accounts that rarely open" rule
CREATE OR REPLACE VIEW open_rate_by_tier AS
SELECT usage_tier,
       COUNT(*)                                                         AS emailed_accounts,
       ROUND(AVG(open_rate), 3)                                         AS open_rate,
       ROUND(AVG(CASE WHEN open_group = 'Opens few or none' THEN 1 ELSE 0 END), 3) AS share_rarely_opening,
       SUM(arr)                                                         AS arr
FROM account_outcomes
WHERE emailed = 'Emailed'
GROUP BY usage_tier;
