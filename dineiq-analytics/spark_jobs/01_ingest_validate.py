"""
01_ingest_validate.py - SRS Step 3: data ingestion with Apache Spark.

Demonstrates, and writes evidence to reports/ingestion_report.md:
  1. Explicit schema definition  (spark_common.SCHEMAS)
  2. Schema inference            (inferSchema=True) and how it DIFFERS from the explicit schema
  3. Data-type validation        (PERMISSIVE mode + corrupt-record column)
  4. Large-file / multiple-file ingestion (orders and order_items are folders of part files)
  5. Partition handling          (default partitions, repartition, month-partitioned Parquet + partition pruning)
  6. CSV versus Parquet read speed (why Parquet is the storage format for big data)

Run:  python 01_ingest_validate.py --root ..
"""
import os
import time

from pyspark.sql import functions as F

from spark_common import CHUNKED, SCHEMAS, Timer, get_spark, parse_args, raw_path, read_raw

args = parse_args("DineIQ Spark ingestion")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-01-ingest", args.driver_memory)
J = "01_ingest"
md = ["# Spark ingestion report\n", f"Spark version: `{spark.version}`  |  master: `{spark.sparkContext.master}`\n"]

# ------------------------------------------------------------------ 1-3. explicit vs inferred schema + type validation
md.append("\n## 1. Explicit schema vs inferred schema, and data-type validation\n")
md.append("| Table | Rows | Columns | Columns where inference differs from the explicit schema | Rows that do not fit the schema |\n|---|---|---|---|---|")
row_counts = {}
for t in SCHEMAS:
    with Timer(ROOT, J, f"load+validate {t}"):
        explicit = read_raw(spark, ROOT, t, with_corrupt=True).cache()
        n = explicit.count()
        bad = explicit.filter(F.col("_corrupt_record").isNotNull()).count()
        inferred = (spark.read.option("header", True).option("inferSchema", True).csv(raw_path(ROOT, t)))
        diffs = []
        for f in SCHEMAS[t].fields:
            inf = dict(inferred.dtypes).get(f.name)
            exp = f.dataType.simpleString()
            if inf != exp:
                diffs.append(f"`{f.name}`: inferred {inf} vs explicit {exp}")
        row_counts[t] = n
        md.append(f"| {t} | {n:,} | {len(SCHEMAS[t].fields)} | {'; '.join(diffs) if diffs else 'none'} | {bad:,} |")
        explicit.unpersist()
md.append("\nOn this dataset inference happens to agree with the explicit schema, but it still costs an extra pass over the data "
          "and it only guesses from the values it sees: one dirty value in a hidden evaluation file (a word in a numeric column) or an "
          "all-empty column can silently change an inferred type. An explicit schema is faster, stable between runs and is the "
          "contract the data-quality step checks against.")

# ------------------------------------------------------------------ 4. multiple-file ingestion
md.append("\n## 2. Multiple-file ingestion\n")
md.append("| Table | Part files read | Rows | Spark input partitions |\n|---|---|---|---|")
for t in CHUNKED:
    with Timer(ROOT, J, f"multi-file read {t}"):
        df = read_raw(spark, ROOT, t)
        files = df.select(F.input_file_name().alias("f")).distinct().count()
        md.append(f"| {t} | {files} | {row_counts[t]:,} | {df.rdd.getNumPartitions()} |")

# ------------------------------------------------------------------ 5. partition handling
md.append("\n## 3. Partition handling\n")
lines = read_raw(spark, ROOT, "order_items")
p0 = lines.rdd.getNumPartitions()
p1 = lines.repartition(8).rdd.getNumPartitions()
p2 = lines.coalesce(2).rdd.getNumPartitions()
md.append(f"- `order_items` read as **{p0}** partitions; `repartition(8)` -> **{p1}** (full shuffle, balances data); "
          f"`coalesce(2)` -> **{p2}** (no shuffle, only merges).")
orders_by_month = os.path.join(ROOT, "parquet_data", "orders_by_month")
if os.path.exists(orders_by_month):
    om = spark.read.parquet(orders_by_month)
    months = sorted(r[0] for r in om.select("order_month").distinct().collect())
    pruned = om.filter(F.col("order_month") == "2026-01")
    plan = pruned._jdf.queryExecution().executedPlan().toString()
    import re
    pf = re.findall(r"PartitionFilters: \[[^\]]*\]", plan)
    with Timer(ROOT, J, "partition-pruned read (one month)"):
        n_jan = pruned.count()
    md.append(f"- `parquet_data/orders_by_month` is partitioned by `order_month` ({len(months)} partitions: {', '.join(months)}).")
    md.append(f"- Reading only `order_month = 2026-01` returns {n_jan:,} rows and Spark skips the other folders "
              f"(*partition pruning*). Plan evidence: `{pf[0] if pf else 'n/a'}`")
    md.append("- Rows whose date is invalid sit in `order_month=unknown`: a first, free hint of the data-quality problem.")

# ------------------------------------------------------------------ 6. CSV vs Parquet
pq = os.path.join(ROOT, "parquet_data", "order_items")
if os.path.exists(pq):
    md.append("\n## 4. CSV versus Parquet\n")
    md.append("| Format | Task | Seconds |\n|---|---|---|")
    for label, df in [("CSV (explicit schema)", read_raw(spark, ROOT, "order_items")),
                      ("Parquet (snappy)", spark.read.parquet(pq))]:
        t0 = time.time()
        res = df.groupBy("item_id").agg(F.sum("line_total").alias("rev")).count()
        md.append(f"| {label} | group order lines by item ({res} groups) | {time.time() - t0:.2f} |")
    size = lambda p: sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs) / 1e6
    md.append(f"\nOn disk: CSV `order_items` {size(raw_path(ROOT, 'order_items')):.1f} MB vs Parquet {size(pq):.1f} MB "
              "(columnar, compressed, typed - and Spark only reads the columns a query needs). "
              "Timings come from a small local machine; the first query also pays for JVM warm-up.")

os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
open(os.path.join(ROOT, "reports", "ingestion_report.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
spark.stop()
