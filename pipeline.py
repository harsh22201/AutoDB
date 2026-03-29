"""
Pipeline adapter for AutoDB web UI.
Wraps existing AutoDB modules into a web-friendly interface
that returns intermediate outputs instead of printing to console.
"""

import json
import sys
import os
import traceback

# Set up paths — ensure .env is loaded from autodb/ directory
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_AUTODB_DIR = os.path.join(_BASE_DIR, 'autodb')

# Load environment from autodb/.env
from dotenv import load_dotenv
load_dotenv(os.path.join(_AUTODB_DIR, '.env'))

from autodb.sql_executor import SQLExecutor
from autodb.ambiguity_resolver import IntentAmbiguityResolver
from autodb.candidate_retriever import CandidateRetriever
from autodb.analyzer import Analyzer
from autodb.decomposer import Decomposer
from autodb.llm_executor import LLM_Executor


class PipelineSession:
    """
    Manages a single pipeline session for a database connection.
    Designed for web use — no input() calls, returns all intermediate outputs.
    """

    def __init__(self, db_name="grocermind", **db_kwargs):
        self.db_name = db_name
        self.db_kwargs = db_kwargs
        self.sql_executor = None
        self.detector = None
        self.analyzer = None
        self.candidate_retriever = None
        self.decomposer = None
        self.llm_executor = None

        # Per-query state
        self._current_query = None
        self._clarifications = []
        self._iteration = 0
        self._max_iterations = 3
        
        # Pipeline State
        self.analysis = None
        self.candidates = []
        self.decomposition = None
        self.sql_result_df = None

    def connect(self):
        """Connect to the database and initialize all pipeline components."""
        try:
            print(f"[DEBUG] Database '{self.db_name}' Connected.")
            self.sql_executor = SQLExecutor(db_name=self.db_name, **self.db_kwargs)
            
            print("[DEBUG] IntentAmbiguityResolver created.")
            self.detector = IntentAmbiguityResolver(model="openai/gpt-oss-20b")
            
            print("[DEBUG] Analyzer created.")
            self.analyzer = Analyzer(model="openai/gpt-oss-120b")
            
            print("[DEBUG] CandidateRetriever created.")
            self.candidate_retriever = CandidateRetriever(sql_executor=self.sql_executor)
            
            print("[DEBUG] Decomposer created.")
            self.decomposer = Decomposer(model="openai/gpt-oss-120b")
            
            print("[DEBUG] LLM_Executor created.")
            self.llm_executor = LLM_Executor(model="openai/gpt-oss-120b")
            return {"success": True, "message": f"Connected to database '{self.db_name}'."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def disconnect(self):
        """Close the database connection."""
        if self.sql_executor:
            self.sql_executor.close()

    # =========================================================
    # Step 1: Intent Ambiguity Resolution (multi-turn)
    # =========================================================

    def start_ambiguity_detection(self, query):
        """
        Start the ambiguity detection for a new query.
        Returns detected ambiguities (if any) for the frontend to present.
        """
        self._current_query = query
        self._clarifications = []
        self._iteration = 0
        self.analysis = None
        self.candidates = []
        self.decomposition = None
        self.sql_result_df = None
        return self._detect_next_ambiguities()

    def _detect_next_ambiguities(self):
        """Run one iteration of ambiguity detection."""
        if self._iteration >= self._max_iterations:
            return {
                "has_ambiguities": False,
                "clarifications_so_far": self._clarifications,
                "iteration": self._iteration,
                "message": "Max iterations reached."
            }

        self._iteration += 1

        try:
            ambiguities_raw = self.detector._detect_ambiguity(
                self._current_query,
                self._clarifications
            )
        except Exception as e:
            return {
                "has_ambiguities": False,
                "clarifications_so_far": self._clarifications,
                "iteration": self._iteration,
                "error": str(e)
            }

        if not ambiguities_raw:
            return {
                "has_ambiguities": False,
                "clarifications_so_far": self._clarifications,
                "iteration": self._iteration,
                "message": "No ambiguities detected."
            }

        # Process ambiguities — check knowledge store for each
        ambiguities_for_ui = []
        for amb in ambiguities_raw:
            ambiguity_type = amb.get("ambiguity_type", "")
            clarification_question = amb.get("clarification_question", "")
            ambiguity_key = amb.get("ambiguity_key", "")
            context_key = amb.get("context_key", "")
            llm_options = amb.get("options", [])

            # Search knowledge store
            retrieved = self.detector.knowledge_store.search(ambiguity_key, context_key)

            if retrieved:
                # Use stored options with percentages
                stored_options = retrieved["options"]
                options_for_ui = []
                for opt in stored_options:
                    options_for_ui.append({
                        "text": opt["text"],
                        "percentage": opt["percentage"],
                        "display": f"{opt['text']} ({opt['percentage']}%)"
                    })
                ambiguities_for_ui.append({
                    "ambiguity_type": ambiguity_type,
                    "clarification_question": clarification_question,
                    "ambiguity_key": retrieved["ambiguity_key"],
                    "context_key": retrieved["context_key"],
                    "options": options_for_ui,
                    "from_knowledge_store": True,
                    "context_score": round(retrieved.get("context_score", 0), 2),
                    "ambiguity_score": round(retrieved.get("ambiguity_score", 0), 2)
                })
            else:
                options_for_ui = [{"text": opt, "display": opt} for opt in llm_options]
                ambiguities_for_ui.append({
                    "ambiguity_type": ambiguity_type,
                    "clarification_question": clarification_question,
                    "ambiguity_key": ambiguity_key,
                    "context_key": context_key,
                    "options": options_for_ui,
                    "from_knowledge_store": False
                })

        return {
            "has_ambiguities": True,
            "ambiguities": ambiguities_for_ui,
            "iteration": self._iteration,
            "clarifications_so_far": self._clarifications
        }

    def submit_clarifications(self, user_choices):
        """
        Submit user's clarification choices and run next iteration.
        
        user_choices: list of dicts with:
            - clarification_question: str
            - selected_option: str
            - ambiguity_key: str
            - context_key: str
            - from_knowledge_store: bool
            - all_llm_options: list[str] (only if not from knowledge store)
        """
        for choice in user_choices:
            # Update knowledge store
            if choice.get("from_knowledge_store"):
                self.detector.knowledge_store.update(
                    ambiguity_key=choice["ambiguity_key"],
                    context_key=choice["context_key"],
                    selected_option=choice["selected_option"]
                )
            else:
                all_options = choice.get("all_llm_options", [choice["selected_option"]])
                self.detector.knowledge_store.update(
                    ambiguity_key=choice["ambiguity_key"],
                    context_key=choice["context_key"],
                    selected_option=choice["selected_option"],
                    all_options=all_options
                )

            self._clarifications.append({
                "clarification_question": choice["clarification_question"],
                "user_clarification": choice["selected_option"]
            })

        # Run next iteration of detection
        return self._detect_next_ambiguities()

    # =========================================================
    # Steps 2-6: Execute remaining pipeline
    # =========================================================

    def execute_step2(self):
        """Step 2: Query Analysis"""
        try:
            print(f"[DEBUG] Starting analysis for query: {self._current_query}")
            self.analysis = self.analyzer.analyze(query=self._current_query, clarifications=self._clarifications)
            print("[DEBUG] Analysis complete.")
            return {"success": True, "step2_analysis": self.analysis}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def execute_step3(self):
        """Step 3: Value Ambiguity Retrieval"""
        try:
            print("[DEBUG] Starting value ambiguity retrieval...")
            value_ambiguities = self.analysis.get("value_ambiguities", [])
            self.candidates = []
            if value_ambiguities:
                print(f"[DEBUG] Found {len(value_ambiguities)} value ambiguities. Retrieving candidates...")
                self.candidates = self.candidate_retriever.retrieve(value_ambiguities)
                print("[DEBUG] Candidates retrieved.")
            else:
                print("[DEBUG] No value ambiguities found.")
            return {"success": True, "step3_value_ambiguities": {"candidates": self.candidates}}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def execute_step4(self):
        """Step 4: Query Decomposition"""
        try:
            print("[DEBUG] Starting query decomposition...")
            self.decomposition = self.decomposer.decompose(
                query=self._current_query,
                analysis=self.analysis,
                candidates=self.candidates
            )
            print("[DEBUG] Query decomposition complete.")
            return {"success": True, "step4_decomposition": self.decomposition}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def execute_step5(self):
        """Step 5: SQL Execution"""
        try:
            print("[DEBUG] Starting SQL execution...")
            structured_query = self.decomposition.get("structured_query", "")
            self.sql_result_df = None
            sql_result_data = None

            if structured_query:
                self.sql_result_df = self.sql_executor.execute(structured_query)
                sql_result_data = {
                    "query": structured_query,
                    "columns": list(self.sql_result_df.columns) if not self.sql_result_df.empty else [],
                    "rows": self.sql_result_df.values.tolist() if not self.sql_result_df.empty else [],
                    "row_count": len(self.sql_result_df)
                }
            else:
                print("[DEBUG] No structured query to execute.")
                sql_result_data = {
                    "query": None,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "message": "No structured query to execute."
                }
            print("[DEBUG] SQL execution complete.")
            return {"success": True, "step5_sql": sql_result_data}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def execute_step6(self):
        """Step 6: Final Answer Generation"""
        try:
            print("[DEBUG] Starting Final Answer Generation...")
            unstructured_query = self.decomposition.get("unstructured_query", "")
            
            if self.sql_result_df is None or isinstance(self.sql_result_df, str):
                df_to_pass = "No structured query executed."
            else:
                df_to_pass = self.sql_result_df.head(25)

            final_answer = self.llm_executor.execute(
                sql_result=df_to_pass,
                unstructured_query=unstructured_query,
                original_query=self._current_query
            )
            print("[DEBUG] Final answer generated.")
            return {"success": True, "step6_final_answer": final_answer}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
