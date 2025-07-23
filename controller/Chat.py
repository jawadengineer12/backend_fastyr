from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from dotenv import load_dotenv
from starlette.responses import JSONResponse
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, CSVLoader, TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
import os
import tempfile

load_dotenv()
api_key = os.getenv("API_KEY")

router = APIRouter(prefix="/chat", tags=["Chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatModel(BaseModel):
    prompt: str
    userId: int

class CreateChatResponse(BaseModel):
    responses: list[str]

# Memory & vector stores for each user
user_memories = {}
user_vectorstores = {}

def get_user_memory(email: str):
    if email not in user_memories:
        user_memories[email] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return user_memories[email]

def get_user_vectorstore(email: str):
    return user_vectorstores.get(email)

@router.post("/upload/{email}")
async def upload_file(email: str, file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            file_path = tmp.name

        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file.filename.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
            print("Docx file loaded successfully")
        elif file.filename.endswith(".csv"):
            loader = CSVLoader(file_path)
        elif file.filename.endswith(".txt"):  # <-- Add this
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        texts = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        if email in user_vectorstores:
            user_vectorstores[email].add_documents(texts)
        else:
            user_vectorstores[email] = FAISS.from_documents(texts, embeddings)

        return {"message": f"{file.filename} uploaded and processed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/create")
def create_chat(email: str, prompt: str, db: Session = Depends(get_db)):
    try:
        memory = get_user_memory(email)
        vectorstore = get_user_vectorstore(email)

        llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=api_key, temperature=0.3)
        casual_responses = ["thanks", "thank you", "ok", "bye"]

        # Keyword-based retrieval trigger
        retrieval_keywords = ["docs", "pdf", "csv", "file", "document"]

        if vectorstore and any(word in prompt.lower() for word in retrieval_keywords):
            retriever = vectorstore.as_retriever()
            conversation = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory
            )
            response_text = conversation.run(prompt)
        elif len(prompt.split()) < 3 or prompt.lower() in casual_responses:
            response_text = llm.predict(prompt)
        else:
            response_text = llm.predict(prompt)

        formatted_response = response_text.split("\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return CreateChatResponse(responses=formatted_response)

@router.get("/clearHistory/{email}")
def clear_chat_history(email: str):
    if email in user_memories:
        user_memories[email].clear()
    if email in user_vectorstores:
        del user_vectorstores[email]
    return "History and documents cleared."
