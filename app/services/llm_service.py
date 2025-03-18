import os
import json
import groq
from typing import List, Dict, Any, Optional

DEFAULT_MODEL = os.getenv("DEFAULT_GROQ_MODEL", "llama3-70b-8192")

async def generate_summary(transcript: str, api_key: str, instructions: Optional[str] = None) -> str:
    """
    Generate summary from transcript using Groq LLM
    
    Args:
        transcript: The YouTube video transcript
        api_key: Groq API key
        instructions: Optional specific instructions for summarization
        
    Returns:
        Generated summary text
    """
    # Set up Groq client
    client = groq.Groq(api_key=api_key)
    
    # Default instructions if none provided
    if not instructions:
        instructions = """Create a concise, informative summary of the video transcript. 
        Focus on key points, main ideas, and important takeaways. 
        Keep the summary well-structured with headers for main sections."""
    
    # Create prompt for the model
    prompt = f"""You are an expert in creating concise, informative summaries of video content.
    
    INSTRUCTIONS:
    {instructions}
    
    VIDEO TRANSCRIPT:
    {transcript}
    
    Provide only the summary without any introductory text like "Here's a summary:" or "Summary:".
    """
    
    # Generate summary using Groq
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an educational assistant that specializes in creating concise, informative summaries."},
            {"role": "user", "content": prompt}
        ],
        model=DEFAULT_MODEL,
        temperature=0.3,
        max_tokens=1500,
    )
    
    return response.choices[0].message.content.strip()

async def generate_mcqs(transcript: str, api_key: str, num_questions: int = 5) -> List[Dict[str, Any]]:
    """
    Generate multiple-choice questions based on the transcript
    
    Args:
        transcript: The YouTube video transcript
        api_key: Groq API key
        num_questions: Number of questions to generate
        
    Returns:
        List of MCQ objects
    """
    # Set up Groq client
    client = groq.Groq(api_key=api_key)
    
    # Prompt for MCQ generation
    prompt = f"""You are an expert in creating educational assessments.
    
    INSTRUCTIONS:
    Create {num_questions} multiple-choice questions based on the provided transcript. 
    Each question should:
    1. Test understanding of key concepts from the content
    2. Have 4 options (labeled A, B, C, D)
    3. Have exactly one correct answer
    4. Include a brief explanation for why the correct answer is right
    
    FORMAT YOUR RESPONSE AS A JSON ARRAY with the following structure for each question:
    {{
        "question": "The question text",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correctAnswer": "The correct option text",
        "explanation": "Brief explanation of the correct answer"
    }}
    
    TRANSCRIPT:
    {transcript}
    
    Provide ONLY the JSON array without any additional text. Ensure the JSON is valid.
    """
    
    # Generate MCQs using Groq
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an educational assistant that creates high-quality assessment questions."},
            {"role": "user", "content": prompt}
        ],
        model=DEFAULT_MODEL,
        temperature=0.5,
        max_tokens=2500,
    )
    
    # Extract and parse JSON response
    response_text = response.choices[0].message.content.strip()
    
    # Clean up response text to ensure it's valid JSON
    # Remove markdown code blocks if present
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        questions = json.loads(response_text)
        return questions
    except json.JSONDecodeError:
        # Fallback parsing for more complex responses
        try:
            # Add square brackets if they're missing
            if not response_text.startswith("["):
                response_text = "[" + response_text + "]"
            questions = json.loads(response_text)
            return questions
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}") 