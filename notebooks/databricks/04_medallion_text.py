# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.4 - Bronze, silver, gold in the lakehouse (with text processing in Spark)
# MAGIC Upload the 21 `page_*.json` files from your newest `data/bronze/forms/<run>/` folder into `landing/forms/`,
# MAGIC plus `stop_words.txt` and `category_map.csv` from `data/reference/`.

# COMMAND ----------

from pyspark.sql import functions as F

LANDING = "/Volumes/workspace/kvcu/landing"

# BRONZE: the pages exactly as the API sent them, plus where/when they came from
pages = spark.read.option("multiLine", True).json(f"{LANDING}/forms/")
bronze = (pages.select(F.explode("value").alias("e"), F.col("_metadata.file_path").alias("_source_file"))
          .withColumn("_ingested_at", F.current_timestamp()))
bronze.write.mode("overwrite").saveAsTable("workspace.kvcu.bronze_form_entries")
print("-> bronze entries:", bronze.count())

# COMMAND ----------

# SILVER: same rules as Lab 3.2
cat_map = spark.read.option("header", True).csv(f"{LANDING}/category_map.csv")
e = spark.table("workspace.kvcu.bronze_form_entries").select("e.*")
silver = (e.where(F.col("Entry.Status") == "Submitted")
          .where(~F.coalesce(F.col("WhatHappened"), F.lit("")).rlike("(?i)\\btest|please ignore|form qa"))
          .where(~(F.lower(F.col("Name.First")) == "test") & ~(F.lower(F.col("Name.Last")) == "test"))
          .select(F.col("Id").alias("complaint_id"),
                  F.to_timestamp("Entry.DateSubmitted").alias("submitted_at_utc"),
                  F.expr("try_cast(nullif(regexp_replace(MemberNumber, '[^0-9]', ''), '') as int)").alias("member_number"),
                  F.col("ComplaintCategory").alias("form_category"),
                  F.trim(F.regexp_replace(F.regexp_replace("WhatHappened", "â€™|’", "'"), "\\s+", " ")).alias("narrative"))
          .withColumn("submitted_date", F.to_date(F.from_utc_timestamp("submitted_at_utc", "America/New_York")))
          .join(cat_map.select(F.col("form_label").alias("form_category"), "category_code"), "form_category", "left"))
# double submissions: same member + same text within 10 minutes
from pyspark.sql.window import Window
w = Window.partitionBy("member_number", "narrative").orderBy("submitted_at_utc")
silver = (silver.withColumn("prev", F.lag("submitted_at_utc").over(w))
          .where(F.col("prev").isNull() | (F.col("submitted_at_utc").cast("long") - F.col("prev").cast("long") > 600))
          .drop("prev"))
silver.write.mode("overwrite").saveAsTable("workspace.kvcu.silver_complaints")
print("-> silver complaints:", spark.table("workspace.kvcu.silver_complaints").count())

# COMMAND ----------

# Text in Spark: mask emails and long numbers, then split into words
stop = [r.value for r in spark.read.text(f"{LANDING}/stop_words.txt").collect()]
masked = (spark.table("workspace.kvcu.silver_complaints")
          .withColumn("narrative_masked", F.regexp_replace("narrative", "[\\w.+-]+@[\\w-]+(\\.[\\w-]+)+", "[EMAIL]"))
          .withColumn("narrative_masked", F.regexp_replace("narrative_masked", "\\b\\d[\\d -]{8,}\\d\\b", "[NUMBER]")))
words = (masked
         .select("complaint_id", "category_code",
                 F.explode(F.regexp_extract_all(F.lower("narrative_masked"), F.lit("[a-z]+(?:'[a-z]+)?"), 0)).alias("w"))
         .withColumn("word", F.regexp_replace("w", "'", ""))
         .where(~F.col("word").isin(stop) & (F.length("word") >= 3) & ~F.col("word").isin("email", "number")))
masked.select("complaint_id", "category_code", "submitted_date", "narrative_masked") \
    .write.mode("overwrite").saveAsTable("workspace.kvcu.silver_complaints_masked")
display(words.groupBy("word").count().orderBy(F.desc("count")).limit(15))
print("-> top word:", words.groupBy("word").count().orderBy(F.desc("count")).first()["word"])

# COMMAND ----------

# MAGIC %sql
# MAGIC -- GOLD: a small, ready-to-report table
# MAGIC CREATE OR REPLACE TABLE workspace.kvcu.gold_complaints_monthly AS
# MAGIC SELECT date_format(submitted_date, 'yyyy-MM') AS month, category_code, count(*) AS complaints
# MAGIC FROM workspace.kvcu.silver_complaints
# MAGIC GROUP BY ALL;
# MAGIC SELECT * FROM workspace.kvcu.gold_complaints_monthly WHERE month = '2026-03' ORDER BY complaints DESC;
