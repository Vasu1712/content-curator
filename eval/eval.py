from langchain_community.llms import Ollama

def evaluate_faithfulness(original_content: str, generated_challenge: str) -> dict:
    """LLM-as-a-judge evaluation to ensure the challenge is grounded in the source text."""
    
    llm = Ollama(model="llama3", temperature=0)
    
    prompt = f"""
    You are an evaluator for an educational platform. Your job is to check if an AI-generated learning challenge is "faithful" to the original source text.
    
    Original Source Text:
    {original_content}
    
    Generated Challenge:
    {generated_challenge}
    
    Rule: The challenge must ONLY rely on facts and concepts present in the Original Source Text. 
    Respond with ONLY a valid JSON object in this exact format:
    {{"is_faithful": true/false, "reason": "brief explanation"}}
    """
    
    response = llm.invoke(prompt)
    return response

# Example Usage:
# result = evaluate_faithfulness(user_input_text, api_response["dynamic_challenge"])
# print(result)