-- One row per account: assignment, starting usage, email engagement and outcomes
CREATE OR REPLACE VIEW account_outcomes AS
WITH engagement AS (
    SELECT account_id,
           COUNT(*)                                   AS emails_sent,
           AVG(CASE WHEN opened THEN 1 ELSE 0 END)    AS open_rate,
           MAX(CASE WHEN clicked_next_step THEN 1 ELSE 0 END) AS clicked_next_step
    FROM email_sends
    GROUP BY account_id
)
SELECT a.*,
       COALESCE(e.emails_sent, 0)  AS emails_sent,
       e.open_rate,
       COALESCE(e.clicked_next_step, 0) AS clicked_next_step,
       CASE WHEN a.arm = 'holdout' THEN 'No email' ELSE 'Emailed' END AS emailed,
       CASE WHEN e.open_rate >= 0.5 THEN 'Opens most emails'
            WHEN e.open_rate IS NOT NULL THEN 'Opens few or none' END AS open_group,
       CASE WHEN a.renewed THEN 1 ELSE 0 END AS renewed_flag,
       CASE WHEN a.used_reminders_at_renewal THEN 1 ELSE 0 END AS adopted_flag
FROM accounts a
LEFT JOIN engagement e USING (account_id);
