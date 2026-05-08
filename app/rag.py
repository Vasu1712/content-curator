from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Import the response model for the output parser
from app.models import BundleResponse

class ContentCuratorEngine:
    def __init__(self, model_name="llama3", embed_model="nomic-embed-text"):
        # Temperature is set low (0.1) to enforce deterministic, grounded outputs
        self.llm = OllamaLLM(model=model_name, temperature=0.1)
        self.embeddings = OllamaEmbeddings(model=embed_model)
        self.parser = JsonOutputParser(pydantic_object=BundleResponse)

    def generate_case_study(self, objective: str, content: str) -> dict:
        """Processes the content, retrieves context, and queries the LLM."""
        
        # 1. Chunking the input text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_text(content)
        
        # 2. Embedding & Retrieval (Using an ephemeral, in-memory Chroma instance)
        vectorstore = Chroma.from_texts(texts=chunks, embedding=self.embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        
        relevant_docs = retriever.invoke(objective)
        
        # Failure Mode Trigger: No relevant context found
        if not relevant_docs:
            vectorstore.delete_collection()
            raise ValueError("NO_RELEVANT_CONTEXT")
            
        context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # 3. Constructing the Prompt
        prompt = PromptTemplate(
            template="""You are an expert instructional designer. Based strictly on the provided context, build a learning challenge.
            
            Learning Objective: {objective}
            Source Context: {context}
            
            Rules:
            1. Rely ONLY on the provided context. Do not invent outside facts.
            2. Make the challenge highly actionable.
            
            {format_instructions}""",
            input_variables=["objective", "context"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        chain = prompt | self.llm | self.parser
        
        # 4. Execution and Cleanup
        try:
            result = chain.invoke({"objective": objective, "context": context_text})
            return result
        except Exception as e:
            # Failure Mode Trigger: LLM failed to output correct JSON schema
            raise ValueError(f"PARSE_ERROR: {str(e)}")
        finally:
            # Always clean up the local vector collection to prevent memory leaks
            vectorstore.delete_collection()