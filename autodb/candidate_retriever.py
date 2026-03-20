from autodb.sql_executor import SQLExecutor
from autodb.embedder import Embedder
import numpy as np

class CandidateRetriever:

    def __init__(
        self,
        sql_executor: SQLExecutor,
        topk: int = 5,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.sql_executor = sql_executor
        self.topk = topk
        self.embedder = Embedder(embedding_model)

    def __fetch_unique_values(self, table: str, column: str) -> list[str]:
        '''
        Fetches unique values from a column in a table.
        '''

        query = f"""
            SELECT DISTINCT {column}
            FROM {table}
            WHERE {column} IS NOT NULL;
        """

        df = self.sql_executor.execute(query)

        if df.empty:
            return []

        return df[column].astype(str).tolist()

    def retrieve(self, value_ambiguities: list[dict]) -> list[dict]:
        result = []

        for ambiguity in value_ambiguities:
            ambiguous_term = ambiguity["ambiguous_term"]
            candidate_columns = ambiguity["candidate_columns"]
            ambiguous_term_embedding = self.embedder.embed([ambiguous_term])[0]

            candidate_entries = {}
            for col in candidate_columns:
                table, column = col.split(".")
                values = self.__fetch_unique_values(table, column)

                if not values:
                    continue

                value_embeddings = self.embedder.embed(values)           
                                                                         
                similarities = self.embedder.similarity(ambiguous_term_embedding, value_embeddings)
                top_indices = np.argsort(similarities)[-self.topk:][::-1]

                candidate_entries[col] = [values[i] for i in top_indices]

            result.append({
                "ambiguous_term": ambiguous_term,
                "candidate_entries": candidate_entries
            })

        return result