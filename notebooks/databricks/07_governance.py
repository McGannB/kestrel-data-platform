# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.7 - Unity Catalog governance: who sees what
# MAGIC Grants, a row filter, a column mask, tags and lineage. This is the part of Databricks that
# MAGIC a compliance department cares about most.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- a member table that holds PII (built in Lab 10.1)
# MAGIC CREATE OR REPLACE TABLE workspace.kvcu.members_secure AS
# MAGIC SELECT member_number, first_name, last_name, email, birth_year, branch_code, status
# MAGIC FROM workspace.kvcu.bronze_members;
# MAGIC
# MAGIC -- TAGS: label sensitive columns so people (and scanners) can find them
# MAGIC ALTER TABLE workspace.kvcu.members_secure ALTER COLUMN email SET TAGS ('pii' = 'email');
# MAGIC ALTER TABLE workspace.kvcu.members_secure ALTER COLUMN last_name SET TAGS ('pii' = 'name');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- COLUMN MASK: everyone outside the 'compliance-analysts' group sees ***@domain instead of the email
# MAGIC CREATE OR REPLACE FUNCTION workspace.kvcu.mask_email(email STRING)
# MAGIC RETURN CASE WHEN is_account_group_member('compliance-analysts') THEN email
# MAGIC             ELSE regexp_replace(email, '^[^@]+', '***') END;
# MAGIC
# MAGIC ALTER TABLE workspace.kvcu.members_secure ALTER COLUMN email SET MASK workspace.kvcu.mask_email;
# MAGIC
# MAGIC SELECT email FROM workspace.kvcu.members_secure LIMIT 5;   -- you are not in that group, so: masked

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ROW FILTER: a Cedar Falls branch manager should only see Cedar Falls members (branch 06)
# MAGIC CREATE OR REPLACE FUNCTION workspace.kvcu.branch_06_only(branch_code INT)
# MAGIC RETURN is_account_group_member('compliance-analysts') OR branch_code = 6;
# MAGIC
# MAGIC ALTER TABLE workspace.kvcu.members_secure SET ROW FILTER workspace.kvcu.branch_06_only ON (branch_code);
# MAGIC
# MAGIC SELECT count(*) AS rows_i_can_see FROM workspace.kvcu.members_secure;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- GRANTS: give read access on the gold table only. Nobody needs bronze to read a report.
# MAGIC GRANT USE CATALOG ON CATALOG workspace TO `account users`;
# MAGIC GRANT USE SCHEMA ON SCHEMA workspace.kvcu TO `account users`;
# MAGIC GRANT SELECT ON TABLE workspace.kvcu.gold_complaints_monthly TO `account users`;
# MAGIC SHOW GRANTS ON TABLE workspace.kvcu.gold_complaints_monthly;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- clean up the filter and mask when you are done experimenting
# MAGIC ALTER TABLE workspace.kvcu.members_secure DROP ROW FILTER;
# MAGIC ALTER TABLE workspace.kvcu.members_secure ALTER COLUMN email DROP MASK;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: AI functions on text
# MAGIC If your workspace has AI Functions turned on, try these on 20 rows first (they cost compute).
# MAGIC Never send unmasked PII to a model. Use the masked narrative.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT complaint_id, ai_analyze_sentiment(narrative_masked) AS sentiment
# MAGIC FROM workspace.kvcu.silver_complaints_masked
# MAGIC LIMIT 20;
