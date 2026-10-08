# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 10.1 - Set up your lakehouse and take a first look
# MAGIC Run each cell with **Shift+Enter**. Before you start, upload the kit files (see the lab steps).

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Unity Catalog names everything catalog.schema.object. Free Edition gives you a catalog called "workspace".
# MAGIC CREATE SCHEMA IF NOT EXISTS workspace.kvcu;
# MAGIC CREATE VOLUME IF NOT EXISTS workspace.kvcu.landing;   -- a folder for files, governed like a table

# COMMAND ----------

LANDING = "/Volumes/workspace/kvcu/landing"
display(dbutils.fs.ls(LANDING))          # you should see the files you uploaded

# COMMAND ----------

chats = spark.read.json(f"{LANDING}/chats/")   # reads every JSON-lines file in the folder
print("-> chats:", chats.count())
chats.printSchema()

# COMMAND ----------

display(chats.groupBy("disposition").count().orderBy("count", ascending=False))

# COMMAND ----------

members = (spark.read
           .option("header", True)
           .option("sep", "|")
           .option("inferSchema", True)
           .csv(f"{LANDING}/members_extract_20260930.txt"))
print("-> members:", members.count())
members.write.mode("overwrite").saveAsTable("workspace.kvcu.bronze_members")   # your first Delta table
