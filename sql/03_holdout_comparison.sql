-- What the emails caused: every assigned account counts, opened or not, compared with the random holdout
CREATE OR REPLACE VIEW holdout_comparison AS
SELECT usage_tier, arm,
       COUNT(*)                     AS accounts,
       ROUND(AVG(renewed_flag), 4)  AS renewal_rate,
       ROUND(AVG(adopted_flag), 4)  AS reminders_adoption_rate,
       ROUND(AVG(open_rate), 3)     AS open_rate,
       SUM(arr)                     AS arr
FROM account_outcomes
GROUP BY GROUPING SETS ((usage_tier, arm), (arm))
ORDER BY usage_tier NULLS FIRST, arm;
