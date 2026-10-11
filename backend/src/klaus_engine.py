import json
from groq import Groq

from dotenv import load_dotenv
import os

load_dotenv()

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_Klaus_response(user_query, df_columns):
    system_prompt = f"""
    You are 'Klaus', the visualization brain for LOOM.
    Convert user queries into JSON visualization commands.
    
    STRICT COLUMN LIST: {list(df_columns)}
    
    OUTPUT FORMAT:
    {{
      "chart_type": "bar" | "line" | "pie" | "scatter",
      "category": "must_be_from_column_list",
      "value": "must_be_from_column_list",
      "aggregation": "sum" | "avg" | "count"
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        output = json.loads(completion.choices[0].message.content)
        
        # Validation: Ensure the LLM didn't hallucinate a column
        if output['category'] not in df_columns or output['value'] not in df_columns:
            # You could add fuzzy matching here, but for now, just a safety check
            print("Warning: Klaus suggested a non-existent column.")
            
        return output
    except Exception as e:
        print(f"Error in Klaus: {e}")
        return None