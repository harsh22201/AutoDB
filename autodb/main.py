import json
from autodb.sql_executor import SQLExecutor
from autodb.ambiguity_resolver import IntentAmbiguityResolver
from autodb.candidate_retriever import CandidateRetriever
from autodb.analyzer import Analyzer
from autodb.decomposer import Decomposer


def main():
    # Initialize components
    sql_executor = SQLExecutor()
    detector = IntentAmbiguityResolver()
    analyzer = Analyzer(model="openai/gpt-oss-120b")
    candidate_retriever = CandidateRetriever(sql_executor=sql_executor)
    decomposer = Decomposer(model="openai/gpt-oss-120b")
    
    print("\n===========================================")
    print("Welcome to AutoDB Query Pipeline")
    print("===========================================")
    
    while True:
        query = input("\n[USER] Enter your natural language query (or 'exit' to quit): ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            print("[INFO] Exiting AutoDB. Goodbye!")
            break
            
        if not query:
            continue
            
        print("\n[SYSTEM] --- Step 1: Intent Ambiguity Resolution ---")
        try:
            clarifications = detector.resolve(query)
            if clarifications:
                print(f"[INFO] Collected {len(clarifications)} clarifications.")
            else:
                print("[INFO] No intent clarifications needed or resolved automatically.")
                
            print("\n[SYSTEM] --- Step 2: Query Analysis ---")
            analysis = analyzer.analyze(query=query, clarifications=clarifications)
            print(f"[INFO] Analysis result:")
            print(json.dumps(analysis, indent=2))
            
            # Pop value_ambiguities out — candidates go to decomposer separately
            value_ambiguities = analysis.pop("value_ambiguities", [])
            candidates = []
            
            if value_ambiguities:
                print("\n[SYSTEM] --- Step 3: Value Ambiguity Retrieval ---")
                print(f"[INFO] Found {len(value_ambiguities)} potential value ambiguities. Retrieving candidates...")
                candidates = candidate_retriever.retrieve(value_ambiguities)
                print(f"[INFO] Retrieved Candidates:")
                print(json.dumps(candidates, indent=2))
            else:
                print("\n[SYSTEM] --- Step 3: Value Ambiguity Retrieval ---")
                print("[INFO] No value ambiguities detected.")

            print("\n[SYSTEM] --- Step 4: Query Decomposition ---")
            decomposition = decomposer.decompose(
                query=query,
                analysis=analysis,
                candidates=candidates
            )
            print("[INFO] Decomposition result:")
            print(json.dumps(decomposition, indent=2))

            print("\n[SYSTEM] --- Step 5: SQL Execution ---")
            structured_query = decomposition.get("structured_query", "")
            if structured_query:
                df = sql_executor.execute(structured_query)
                print(f"[INFO] SQL Result ({len(df)} rows):")
                print(df.head(20).to_string(index=False))
            else:
                print("[INFO] No structured query to execute.")
                
            print("\n[SYSTEM] Pipeline finished for query.")
        except Exception as e:
            print(f"\n[ERROR] Pipeline failed: {e}")
    
    sql_executor.close()


if __name__ == "__main__":
    main()

