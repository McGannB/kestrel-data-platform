# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.3 - Delta Lake: upserts, history, time travel, schema changes
# MAGIC Upload `grc_issue_changes.parquet` (from `data/bronze/grc/`) to the landing volume first.

# COMMAND ----------

from pyspark.sql import functions as F, Window

changes = spark.read.parquet("/Volumes/workspace/kvcu/landing/grc_issue_changes.parquet")
batches = changes.withColumn("batch_no", F.dense_rank().over(Window.orderBy("_pulled_at")))
display(batches.groupBy("batch_no").count().orderBy("batch_no"))

# COMMAND ----------

# start clean so the version numbers below match the lab (re-running? this resets it)
spark.sql("DROP TABLE IF EXISTS workspace.kvcu.silver_grc_issues")
# version 0: an empty table with the right columns
(batches.drop("_pulled_at", "batch_no").limit(0)
 .write.mode("overwrite").saveAsTable("workspace.kvcu.silver_grc_issues"))

# COMMAND ----------

from delta.tables import DeltaTable

target = DeltaTable.forName(spark, "workspace.kvcu.silver_grc_issues")
for b in (1, 2, 3):
    source = batches.where(F.col("batch_no") == b).drop("_pulled_at", "batch_no")
    (target.alias("t")
     .merge(source.alias("s"), "t.sys_id = s.sys_id")
     .whenMatchedUpdateAll(condition="s.sys_updated_on > t.sys_updated_on")
     .whenNotMatchedInsertAll()
     .execute())                                   # each MERGE = one new table version
    print(f"-> rows after batch {b}:", spark.table("workspace.kvcu.silver_grc_issues").count())

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY workspace.kvcu.silver_grc_issues

# COMMAND ----------

# MAGIC %sql
# MAGIC -- time travel: the table as it was after batch 1 (version 1) and batch 2 (version 2)
# MAGIC SELECT
# MAGIC   (SELECT count(*) FROM workspace.kvcu.silver_grc_issues VERSION AS OF 1) AS rows_v1,
# MAGIC   (SELECT count(*) FROM workspace.kvcu.silver_grc_issues VERSION AS OF 2) AS rows_v2,
# MAGIC   (SELECT count(*) FROM workspace.kvcu.silver_grc_issues) AS rows_now

# COMMAND ----------

# MAGIC %sql
# MAGIC -- schema change: add a column. Old rows get NULL; nothing is rewritten.
# MAGIC ALTER TABLE workspace.kvcu.silver_grc_issues ADD COLUMN reviewer STRING;
# MAGIC -- tidy small files into bigger ones (Delta does more of this automatically on serverless)
# MAGIC OPTIMIZE workspace.kvcu.silver_grc_issues;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- oops: someone deleted every closed issue
# MAGIC DELETE FROM workspace.kvcu.silver_grc_issues WHERE active = 'false';
# MAGIC SELECT count(*) AS rows_after_bad_delete FROM workspace.kvcu.silver_grc_issues;

# COMMAND ----------

# undo it: find the version just before the DELETE in the history, and restore to it
hist = spark.sql("DESCRIBE HISTORY workspace.kvcu.silver_grc_issues")
delete_version = hist.where("operation = 'DELETE'").agg({"version": "max"}).first()[0]
spark.sql(f"RESTORE TABLE workspace.kvcu.silver_grc_issues TO VERSION AS OF {delete_version - 1}")
print("-> rows after restore:", spark.table("workspace.kvcu.silver_grc_issues").count())
