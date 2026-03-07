from autodb.ambiguity_resolver import IntentAmbiguityResolver


b = a + 10 
if __name__ == "__main__":
    
    # Example usage of IntentAmbiguityResolver
    detector = IntentAmbiguityResolver()

    queries = [
        "Show me the sales trend for the last quarter.",
        "Which products sold the most recently?"
    ]

    for query in queries:
        clarifications = detector.detect(query)