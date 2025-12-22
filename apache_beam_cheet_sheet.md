# Apache beam introducing

    * Unified model for batch and streaming data.
    * Separation of pipeline logic from execution engine.
    * Write once, run anywhere (e.g., Google Dataflow, Flink, Spark).
    

# Apache beam vs Spark – Key Concepts

| Concept               | Apache Spark                           | Apache Beam                             |
| --------------------- | -------------------------------------- | --------------------------------------- |
| **Execution Engine**  | Built-in (Spark engine)                | Pluggable (Dataflow, Flink, Spark...)   |
| **Processing Type**   | Mostly batch (w/ structured streaming) | Native batch & streaming (unified)      |
| **Transformations**   | Lazy (`map`, `filter`, etc.)           | Lazy (`MapElements`, `Filter`, etc.)    |
| **Actions**           | Triggers execution (`collect`)         | `pipeline.run()` triggers execution     |
| **In-Memory**         | Caching optimized                      | Depends on runner (Dataflow uses disk)  |
| **Main Data Struct.** | `RDD`, `DataFrame`                     | `PCollection`                           |
| **Windowing**         | Needs structured streaming             | Built-in windowing + watermarks         |
| **Fault Tolerance**   | Lineage + checkpoint                   | Runner-dependent (Dataflow = strong FT) |

# Command Mapping (Spark → Beam)

| Spark (RDD / DF)     | Apache Beam Equivalent                               |
| -------------------- | ---------------------------------------------------- |
| `rdd.map(f)`         | `beam.MapElements(lambda x: f(x))`                   |
| `rdd.filter(f)`      | `beam.Filter(lambda x: f(x))`                        |
| `rdd.flatMap(f)`     | `beam.FlatMap(lambda x: f(x))`                       |
| `rdd.reduceByKey(f)` | `beam.CombinePerKey(f)`                              |
| `rdd.groupByKey()`   | `beam.GroupByKey()`                                  |
| `rdd.collect()`      | `pipeline.run().wait_until_finish()`                 |
| `rdd.join(other)`    | `beam.CoGroupByKey()` + post-processing              |
| `rdd.foreach(f)`     | `beam.ParDo(DoFn)` or `beam.Map(f)` for side effects |
| `read.csv()`         | `beam.io.ReadFromText()` + custom parsing            |
| `write.csv()`        | `beam.io.WriteToText()`                              |

# Apache Beam Example (Python)

```python
import apache_beam as beam

with beam.Pipeline() as p:
    (p
     | beam.io.ReadFromText('data.csv')
     | beam.Map(lambda x: x.split(','))
     | beam.Filter(lambda row: row[1] == 'active')
     | beam.io.WriteToText('filtered_output'))
```

# Apache memory utilization and data shuffle

    * Beam transforms are lazy, and runners like Dataflow optimize for streaming & disk-based execution.
        * You rarely load entire datasets into memory unless you write custom code that forces it.
    *  BUT watch out for: 
        * GroupByKey() or CoGroupByKey() on large unbounded PCollections: can buffer too much data and shuffle too much data
        * CombineGlobally() or similar global aggregations without windowing: **risks OUt Of memory OOM.**
        * beam.ParDo() with large side inputs (e.g: batch sizes: can explode in memory) 


# Apache beam/dataflow executions

  * You can configure worker machine type with not high memory
  * Beam/Dataflow splits work into bundles, which:
    * Are processed in parallel
    * Can spill to disk if needed (less memory pressure)
    * May retry on worker failure
  * Generally, you can get away with modest memory VMs, unless your pipeline:
    * Loads big lookup tables in memory
    * Does massive key reshuffles
    * Avoids windowing in streaming

  * Typical Gotchas That Cause Problems

| Situation                                 | Solution / Prevention                                            |
| ----------------------------------------- | ---------------------------------------------------------------- |
| Global combine without windowing          | Use `CombinePerKey` or add windows                               |
| Large side input (big dictionary)         | Convert to external source or use `beam.View.AsDict()` carefully |
| Unbounded data with no trigger            | Define proper **windowing**, **watermarks**, and **triggers**    |
| Too many small files written to GCS       | Use `FileNaming`, `shard_name_template`, or batch output         |
| Using `print()` or `logging` inside `Map` | Use `beam.Map(print)` with caution, or use `ParDo` with logging  |
