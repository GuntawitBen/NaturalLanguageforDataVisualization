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
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        if not self.api_key:
            print("[WARNING] OPENAI_API_KEY not found in environment")
        
        self.client = openai.OpenAI(api_key=self.api_key)

    def recommend_charts(
        self,
        user_question: str,
        sql_query: str,
        columns_info: List[Dict[str, str]],
        sample_data: List[Dict[str, Any]],
        preferred_chart_type: Optional[str] = None
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

            if preferred_chart_type:
                user_prompt += f"""

CHART TYPE PREFERENCE:
The user has specifically requested a '{preferred_chart_type}' chart. You MUST use '{preferred_chart_type}' as the chart_type.
Configure x_axis, y_axis, and color_by optimally for this chart type with this data."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHART_REC_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )

            content = response.choices[0].message.content
            if not content:
                print("[WARNING] GPT returned empty content for chart recommendation")
                return VisualizationResponse(recommendations=[], summary="Empty response from AI")

            # Handle potential markdown code blocks
            import re
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            data = json.loads(content)
            
            return VisualizationResponse(**data)

        except Exception as e:
            print(f"[ERROR] Chart recommendation failed: {e}")
            return VisualizationResponse(
                recommendations=[],
                summary=f"Failed to generate recommendations: {str(e)}"
            )
