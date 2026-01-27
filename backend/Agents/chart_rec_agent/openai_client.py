"""
OpenAI client for the Chart Recommendation agent.
"""

import os
import json
import openai
from typing import List, Dict, Any, Optional
from .models import VisualizationResponse, ChartRecommendation
from .prompts import CHART_REC_SYSTEM_PROMPT, CHART_REC_USER_PROMPT_TEMPLATE

class ChartRecOpenAIClient:
    """Client for interacting with OpenAI for chart recommendations"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        if not self.api_key:
            print("[WARNING] OPENAI_API_KEY not found in environment")
        
        self.client = openai.OpenAI(api_key=self.api_key)

    def recommend_charts(
        self,
        user_question: str,
        sql_query: str,
        columns_info: List[Dict[str, str]],
        sample_data: List[Dict[str, Any]]
    ) -> VisualizationResponse:
        """
        Get chart recommendations from GPT
        """
        try:
            # Format columns info
            cols_str = "\\n".join([f"- {c['name']} ({c['type']})" for c in columns_info])
            
            # Format sample data
            sample_str = json.dumps(sample_data[:5], indent=2)

            user_prompt = CHART_REC_USER_PROMPT_TEMPLATE.format(
                sql_query=sql_query,
                columns_info=cols_str,
                sample_data=sample_str,
                user_question=user_question
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHART_REC_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            
            return VisualizationResponse(**data)

        except Exception as e:
            print(f"[ERROR] Chart recommendation failed: {e}")
            return VisualizationResponse(
                recommendations=[],
                summary=f"Failed to generate recommendations: {str(e)}"
            )
