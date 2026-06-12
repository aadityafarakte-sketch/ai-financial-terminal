import os
from google import genai
from google.genai import types

def generate_financial_analysis(ticker, user_query, financial_context):
    try:
        # Initialize the official GenAI Client (picks up GEMINI_API_KEY automatically)
        client = genai.Client()
        
        system_instruction = """
        You are an expert, ultra-precise Institutional Equity Research Analyst and Risk Manager.
        Your task is to provide objective, perfectly consistent, non-speculative financial analyses.
        
        CRITICAL OPERATING RULES:
        1. Rely STRICTLY on the real numeric data provided in the financial context. Never hallucinate metrics.
        2. If values are missing, evaluate the baseline numbers logically without inventing speculative performance spikes.
        3. Maintain an absolute professional, high-conviction Wall Street tier analytical tone.
        
        You MUST format your output exactly into these clear markdown sections:
        - 📰 Real-Time News Impact Matrix (Render a markdown table mapping Headline, Impact Score, Time Horizon, and Core Reason)
        - Financial Data Synthesis (Directly address the user's text query using exact numbers from the context data grid)
        - 🐂 Bull Case vs 🐻 Bear Case (3 robust bullet points per pillar backed by raw metrics)
        - 🤖 AI Verdict (Provide: Verdict Status, Confidence Score out of 100, and Core Conviction Reason)
        """
        
        # Assemble the clean data payload block
        prompt = f"""
        Target Asset Ticker: {ticker}
        User Inquiry: {user_query}
        
        Extracted Financial Context:
        {financial_context}
        """
        
        # Execute the model inference with strict deterministic constraints
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,  # CRITICAL FIX: Drops creativity to zero for absolute stability
                top_p=0.1,        # Restricts choice patterns to the highest mathematical probability
            )
        )
        return response.text
    except Exception as e:
        return f"Analysis engine exception: {str(e)}"
