import argparse
import pandas as pd
excel_df = pd.read_excel("customer_loan_1.xlsx")

parser = argparse.ArgumentParser()
parser.add_argument("--queryFile",required=True,help="Generated SQL Query To Run")
args = parser.parse_args()
queryFile = args.queryFile

with open(queryFile,'r') as file:
    query = file.read()

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
spark = SparkSession.builder.appName("Spark SQL Executor").getOrCreate()
# spark.conf.set("spark.sql.debug.maxToStringFields", "100")
spark_df = spark.createDataFrame(excel_df)
spark_df.createOrReplaceTempView("customer_loan")


# query = """SELECT rim_no,AVG(amount) AS average_amount
# FROM customer_loan
# WHERE amount < (SELECT AVG(amount) AS average_amount FROM customer_loan)
# GROUP BY rim_no;"""

res = spark.sql(query)

res.coalesce(1).write.csv("C:/Users/vridi/Downloads/demo2/demo/outputFromSparkSubmit", header=True, mode="overwrite")
