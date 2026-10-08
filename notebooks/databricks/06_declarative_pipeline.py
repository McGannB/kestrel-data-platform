# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.6 - A declarative pipeline (Lakeflow / Spark Declarative Pipelines)
# MAGIC You don't write "run this, then that". You declare tables; the engine works out the order,
# MAGIC handles incremental loading, and enforces data quality rules (expectations).
# MAGIC **Don't run this notebook directly.** Create a pipeline (Jobs & Pipelines > Create > ETL pipeline)
# MAGIC and add this file as its source code. Target catalog `workspace`, schema `kvcu`.

# COMMAND ----------

from pyspark import pipelines as dp
from pyspark.sql import functions as F

LANDING = "/Volumes/workspace/kvcu/landing"


@dp.table(comment="Raw chats, loaded incrementally with Auto Loader")
def dp_bronze_chats():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "json")
            .load(f"{LANDING}/chats_stream/"))


@dp.table(comment="Chats we can tie to a member")
@dp.expect_or_drop("has_member_number", "member_number IS NOT NULL")      # bad rows are dropped AND counted
@dp.expect("known_disposition", "disposition IN ('Resolved', 'Escalated - Complaint', 'Transferred', 'Abandoned')")
def dp_silver_chats():
    return (spark.readStream.table("dp_bronze_chats")
            .select("chat_id", F.to_timestamp("started_at").alias("started_at"), "agent_id", "queue",
                    F.col("member_number").cast("int").alias("member_number"), "disposition", "csat",
                    F.size("turns").alias("turn_count")))


@dp.materialized_view(comment="Chats per month and queue, for reporting")
def dp_gold_chats_monthly():
    return (spark.read.table("dp_silver_chats")
            .groupBy(F.date_format("started_at", "yyyy-MM").alias("month"), "queue")
            .agg(F.count("*").alias("chats"),
                 F.sum(F.when(F.col("disposition") == "Escalated - Complaint", 1).otherwise(0)).alias("escalated")))
