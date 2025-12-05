# LangChain compatibility fix - must be imported first
import langchain_compat  # noqa: F401

from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from config import settings
from vectorstore import vector_store
import logging

logger = logging.getLogger(__name__)

SummaryType = Literal["brief", "detailed", "key_points"]


def get_summary_prompt(summary_type: SummaryType) -> tuple[str, str]:
    """
    Get map and combine prompts based on summary type
    
    Returns:
        Tuple of (map_prompt, combine_prompt)
    """
    
    if summary_type == "brief":
        map_prompt = """Write a concise summary of the following text:

{text}

CONCISE SUMMARY:"""
        
        combine_prompt = """You are summarizing a legal document. Provide a brief, high-level summary (3-5 sentences) that captures the main purpose and key points of the document.

Text to summarize:
{text}

BRIEF SUMMARY:"""
    
    elif summary_type == "detailed":
        map_prompt = """Provide a detailed summary of the following section, including all important points, facts, and details:

{text}

DETAILED SUMMARY:"""
        
        combine_prompt = """You are analyzing a legal document. Provide a comprehensive, detailed summary that covers:
- Main subject matter and purpose
- Key arguments or claims
- Important facts and evidence
- Relevant parties involved
- Significant outcomes or decisions
- Any notable legal precedents or citations

Be thorough but organized. Use clear paragraphs to separate different aspects.

Text to summarize:
{text}

DETAILED SUMMARY:"""
    
    else:  # key_points
        map_prompt = """Extract the key points and important facts from the following text:

{text}

KEY POINTS:"""
        
        combine_prompt = """You are analyzing a legal document. Extract and list the key points in a structured format:

1. Main subject/topic
2. Key parties involved
3. Critical facts and dates
4. Main arguments or claims
5. Important outcomes or decisions
6. Relevant legal principles
7. Any actionable items or next steps

Present each point clearly and concisely.

Text to analyze:
{text}

KEY POINTS:"""
    
    return map_prompt, combine_prompt


def summarize_document(doc_id: str, summary_type: SummaryType) -> str:
    """
    Generate a summary of a document
    
    Args:
        doc_id: Document identifier
        summary_type: Type of summary to generate (brief, detailed, key_points)
    
    Returns:
        Generated summary text
    
    Raises:
        ValueError: If document not found or no content available
        Exception: For other errors during summarization
    """
    try:
        logger.info(f"Generating {summary_type} summary for doc_id: {doc_id}")
        
        # Load the document's vectorstore
        vectorstore = vector_store.load_vectorstore(doc_id)
        
        if not vectorstore:
            raise ValueError(f"No vectorstore found for document: {doc_id}")
        
        # Get all documents from the vectorstore
        all_docs = vectorstore.similarity_search("document content", k=30)
        
        if not all_docs:
            raise ValueError(f"No content found for document: {doc_id}")
        
        # Combine all document content
        combined_text = "\n\n".join([doc.page_content for doc in all_docs])
        
        # Get prompt based on summary type
        _, combine_prompt_text = get_summary_prompt(summary_type)
        
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3
        )
        
        # Create prompt template
        prompt = PromptTemplate(template=combine_prompt_text, input_variables=["text"])
        
        # Generate summary directly
        chain = prompt | llm
        result = chain.invoke({"text": combined_text})
        
        # Extract content from result
        summary = result.content if hasattr(result, 'content') else str(result)
        
        logger.info(f"Successfully generated {summary_type} summary for doc_id: {doc_id}")
        return summary
        
    except ValueError as e:
        logger.error(f"Validation error in summarize_document: {e}")
        raise
    except Exception as e:
        logger.error(f"Error generating summary for doc_id {doc_id}: {e}")
        raise Exception(f"Failed to generate summary: {str(e)}")