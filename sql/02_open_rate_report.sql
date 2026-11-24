-- What a typical email report would say: accounts that open renew more
CREATE OR REPLACE VIEW open_rate_report AS
SELECT open_group,
       COUNT(*)                         AS accounts,
       ROUND(AVG(renewed_flag), 4)      AS renewal_rate,
       ROUND(AVG(active_share_start), 3) AS avg_active_share_at_start
FROM account_outcomes
WHERE emailed = 'Emailed'
GROUP BY open_group
ORDER BY open_group DESC;
