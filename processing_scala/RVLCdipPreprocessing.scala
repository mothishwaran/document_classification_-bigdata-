import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

object RVLCdipPreprocessing {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("RVL-CDIP Preprocessing")
      .getOrCreate()

    import spark.implicits._

    val basePath = "/data/raw/rvl-cdip"

    // Step 1: Read image paths
    val df0 = spark.read
      .format("binaryFile")
      .option("recursiveFileLookup", "true")
      .load(basePath)
      .select($"path".as("image_path"))

    // Step 2: Extract split
    val df1 = df0.withColumn(
      "split",
      regexp_extract($"image_path", "/(train|test|validation)/", 1)
    )

    // Step 3: Extract category and label
    val df2 = df1
      .withColumn(
        "class_dir",
        regexp_extract($"image_path", "/(\\w+_class_\\d+)/", 1)
      )
      .withColumn(
        "category",
        regexp_extract($"class_dir", "^(.*)_class_\\d+$", 1)
      )
      .withColumn(
        "label",
        regexp_extract($"class_dir", "_class_(\\d+)$", 1).cast("int")
      )

    // Step 4: Normalize category
    val df3 = df2.withColumn(
      "category",
      lower(regexp_replace($"category", " ", "_"))
    )

    // Step 5: Final ML-ready DataFrame
    val finalDf = df3.select(
      "image_path",
      "split",
      "category",
      "label"
    )

    // Step 6: Write to HDFS as Parquet
    finalDf.write
      .mode("overwrite")
      .partitionBy("split")
      .parquet("/data/tmp/rvl-cdip-processed")

    spark.stop()
  }
}
