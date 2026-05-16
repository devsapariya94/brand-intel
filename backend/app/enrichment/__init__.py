"""AI Enrichment Layer for Brand Intel Alert Management

This module provides intelligent alert filtering using LLM-based evaluation
to reduce false positives while maintaining high recall for genuine threats.

Key Components:
- LLM Provider Abstraction: OpenAI-compatible interface for multiple providers
- Alert Evaluator: Analyzes raw_hits to determine threat level
- Decision Engine: Makes final alert decisions based on thresholds
- Enrichment Orchestrator: Coordinates the enrichment pipeline
"""

__version__ = "1.0.0"

# Made with Bob