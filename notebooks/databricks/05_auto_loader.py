# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.5 - Auto Loader: pick up only NEW files, every time
# MAGIC Upload `chats_2025_h1.jsonl` into `landing/chats_stream/` and run all cells.
# MAGIC Then upload `chats_2025_h2.jsonl` and run again. Then `chats_2026.jsonl` and run again.

# COMMAND ----------

from pyspark.sql import functions as F

LANDING = "/Volumes/workspace/kvcu/landing"
CHECKPOINT = f"{LANDING}/_checkpoints/bronze_chats"   # Auto Loader remembers which files it already read here

(spark.readStream
 .format("cloudFiles")
 .option("cloudFiles.format", "json")
 .option("cloudFiles.schemaLocation", CHECKPOINT)       # where it stores the inferred schema
 .load(f"{LANDING}/chats_stream/")
 .withColumn("_source_file", F.col("_metadata.file_path"))
 .writeStream
 .option("checkpointLocation", CHECKPOINT)
 .trigger(availableNow=True)                            # process what's there, then stop (batch-style streaming)
 .toTable("workspace.kvcu.bronze_chats_stream")
 .awaitTermination())

print("-> chats in the stream table:", spark.table("workspace.kvcu.bronze_chats_stream").count())

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT _source_file, count(*) AS chats FROM workspace.kvcu.bronze_chats_stream GROUP BY ALL ORDER BY 1

# COMMAND ----------

# MAGIC %md
# MAGIC **Start over?** Drop the table AND delete the checkpoint folder. If you keep the checkpoint,
# MAGIC Auto Loader still thinks it has read those files and skips them.
# MAGIC ```
# MAGIC DROP TABLE workspace.kvcu.bronze_chats_stream;
# MAGIC dbutils.fs.rm(CHECKPOINT, recurse=True)
# MAGIC ```
