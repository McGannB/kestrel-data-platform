# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.2 - PySpark DataFrames
# MAGIC Same questions you answered with pandas in Phase 3-4, now with Spark. Spark is **lazy**:
# MAGIC transformations only build a plan; an **action** (count, show, write) runs it.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

LANDING = "/Volumes/workspace/kvcu/landing"
chats = spark.read.json(f"{LANDING}/chats/")

# explode: one row per turn (like pandas .explode)
turns = (chats
         .select("chat_id", "agent_id", "started_at", F.posexplode("turns").alias("pos", "t"))
         .select("chat_id", "agent_id", "started_at", (F.col("pos") + 1).alias("turn_no"),
                 F.col("t.speaker").alias("speaker"), F.col("t.text").alias("text"), F.col("t.ts").alias("ts")))
print("-> turns:", turns.count())

# COMMAND ----------

# first response time per chat, then median per agent
ts = F.to_timestamp(F.concat_ws(" ", F.substring("started_at", 1, 10), F.col("ts")))
firsts = (turns.withColumn("sent_at", ts)
          .groupBy("chat_id", "agent_id")
          .agg(F.min(F.when(F.col("speaker") == "member", F.col("sent_at"))).alias("first_member"),
               F.min(F.when(F.col("speaker") == "agent", F.col("sent_at"))).alias("first_agent"))
          .withColumn("first_response_s", F.col("first_agent").cast("long") - F.col("first_member").cast("long")))
by_agent = firsts.groupBy("agent_id").agg(F.percentile_approx("first_response_s", 0.5).alias("median_s"))
display(by_agent.orderBy(F.desc("median_s")))
print("-> slowest agent:", by_agent.orderBy(F.desc("median_s")).first()["agent_id"])

# COMMAND ----------

# window function: each member's chats in order
w = Window.partitionBy("member_number").orderBy("started_at")
repeat = (chats.where(F.col("member_number").isNotNull())
          .withColumn("chat_seq", F.row_number().over(w))
          .where("chat_seq > 1"))
print("-> repeat chats (2nd or later from the same member):", repeat.count())

# COMMAND ----------

# how Spark plans to run it - read this like a recipe, bottom up
by_agent.explain()

# COMMAND ----------

turns.write.mode("overwrite").saveAsTable("workspace.kvcu.silver_chat_turns")
