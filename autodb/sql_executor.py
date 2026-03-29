import psycopg2
import pandas as pd
from psycopg2 import OperationalError, Error
import time
from dotenv import load_dotenv
import os

load_dotenv()

class SQLExecutor:
    """
    Read-only PostgreSQL SQL executor (DQL only).
    Returns query results as Pandas DataFrames.
    """

    def __init__(
        self,
        db_name: str = "grocermind",
        user: str = "postgres",
        password: str = os.getenv("DB_PASSWORD"),
        host: str = "localhost",
        port: str = "5432"
    ):
        try:
            self.__connection = psycopg2.connect(
                dbname=db_name,
                user=user,
                password=password,
                host=host,
                port=port
            )
            print(f"[INFO] Connected to PostgreSQL database '{db_name}'.")
        except OperationalError as e:
            raise ConnectionError(f"[ERROR] Could not connect to database: {e}")

    def __validate_read_only(self, query: str):
        """
        Ensure query is read-only (SELECT / WITH only).
        """
        cleaned_query = query.strip().lower()

        # Block multiple statements
        if ";" in cleaned_query[:-1]:
            raise ValueError("Multiple SQL statements are not allowed.")

        # Allow SELECT or WITH (CTE)
        if not (cleaned_query.startswith("select") or cleaned_query.startswith("with")):
            raise ValueError("Only read-only queries (SELECT/CTE) are allowed.")

    def execute(self, sql_query: str) -> pd.DataFrame:

        if self.__connection is None or self.__connection.closed:
            raise ConnectionError("Database connection is closed.")

        try:
            # Validate query safety
            self.__validate_read_only(sql_query)

            start_time = time.time()  # start timer

            with self.__connection.cursor() as cursor:
                cursor.execute(sql_query)

                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()

                    df = pd.DataFrame(rows, columns=columns)

                    end_time = time.time()  # end timer
                    execution_time = end_time - start_time

                    print(f"[INFO] Query executed successfully. Returned {len(df)} rows. Time: {execution_time:.4f} sec")

                    return df

                return pd.DataFrame()

        except Error as e:
            print(f"[ERROR] Failed to execute query: {e}")
            return pd.DataFrame()

    def close(self):
        """Close database connection safely."""

        if self.__connection and not self.__connection.closed:
            self.__connection.close()
            print("[INFO] PostgreSQL connection closed.")


if __name__ == "__main__":
    executor = SQLExecutor()
    df = executor.execute("select * d FROM grocermind_products select distinct product_name")
    print(df)
    executor.close()


