# LangChain compatibility fix - must be imported first
import langchain_compat  # noqa: F401

from typing import TypedDict, List
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from config import settings
from vectorstore import vector_store
import logging

logger = logging.getLogger(__name__)


class RAGState(TypedDict):
    """State for RAG workflow"""
    question: str
    doc_id: str
    context_docs: List[Document]
    answer: str


def retrieve_node(state: RAGState) -> RAGState:
    """
    Retrieve relevant document chunks from FAISS
    
    Args:
        state: Current RAG state with question and doc_id
    
    Returns:
        Updated state with context_docs
    """
    try:
        question = state["question"]
        doc_id = state["doc_id"]
        
        logger.info(f"Retrieving context for doc_id: {doc_id}")
        
        # Load the document's vectorstore
        vectorstore = vector_store.load_vectorstore(doc_id)
        
        if not vectorstore:
            logger.warning(f"No vectorstore found for doc_id: {doc_id}")
            state["context_docs"] = []
            return state
        
        # Perform similarity search (top 4 most relevant chunks)
        docs = vectorstore.similarity_search(question, k=4)
        
        logger.info(f"Retrieved {len(docs)} relevant chunks")
        state["context_docs"] = docs
        
        return state
        
    except Exception as e:
        logger.error(f"Error in retrieve_node: {e}")
        state["context_docs"] = []
        return state


def generate_node(state: RAGState) -> RAGState:
    """
    Generate answer using retrieved context and LLM
    
    Args:
        state: Current RAG state with question and context_docs
    
    Returns:
        Updated state with answer
    """
    try:
        question = state["question"]
        context_docs = state["context_docs"]
        
        # If no context found, provide a fallback response
        if not context_docs:
            state["answer"] = "I couldn't find relevant information in the document to answer your question. Please try rephrasing or ask a different question."
            return state
        
        # Combine context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in context_docs])
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful legal assistant analyzing court documents. 
Your task is to answer questions based ONLY on the provided context from the document.

Important guidelines:
- Only use information from the provided context
- If the context doesn't contain enough information to answer the question, say so clearly
- Be precise and cite specific details from the context when possible
- Maintain a professional and objective tone
- For legal terms, provide brief explanations if helpful

Context from document:
{context}"""),
            ("human", "{question}")
        ])
        
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3
        )
        
        # Create chain and invoke
        chain = prompt | llm
        response = chain.invoke({
            "context": context,
            "question": question
        })
        
        state["answer"] = response.content
        logger.info("Generated answer successfully")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in generate_node: {e}")
        state["answer"] = f"An error occurred while generating the answer: {str(e)}"
        return state


# Build the RAG graph
def create_rag_graph():
    """Create and compile the RAG workflow graph"""
    workflow = StateGraph(RAGState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    
    # Add edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    # Compile the graph
    return workflow.compile()


# Create the compiled RAG application
rag_app = create_rag_graph()