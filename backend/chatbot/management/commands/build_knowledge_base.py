# backend/chatbot/management/commands/build_knowledge_base.py

import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from langchain.document_loaders import PyPDFLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# --- Import the NEW Google embeddings class ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from chatbot.models import KnowledgeChunk
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class Command(BaseCommand):
    help = 'Builds the knowledge base for the chatbot using Google Gemini.'

    def handle(self, *args, **options):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            self.stdout.write(self.style.ERROR('Google API key not found. Please set it in your .env file.'))
            return
        
        # --- Configure the Google API key for the underlying library ---
        genai.configure(api_key=google_api_key)

        self.stdout.write("Starting to build the knowledge base...")
        KnowledgeChunk.objects.all().delete()
        self.stdout.write("Old knowledge base cleared.")

        # --- The loading and chunking part remains EXACTLY THE SAME ---
        data_path = os.path.join(settings.BASE_DIR, 'data')
        self.stdout.write(f"Scanning for documents in: {data_path}")
        
        all_documents = []
        try:
            files_in_directory = os.listdir(data_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"The 'data' directory was not found."))
            return

        for filename in files_in_directory:
            file_path = os.path.join(data_path, filename)
            if filename.endswith(".pdf"):
                self.stdout.write(f"-> Loading PDF: {filename}")
                loader = PyPDFLoader(file_path)
                all_documents.extend(loader.load())
            elif filename.endswith(".csv"):
                self.stdout.write(f"-> Loading CSV: {filename}")
                loader = CSVLoader(file_path=file_path, encoding='utf-8')
                all_documents.extend(loader.load())

        self.stdout.write(f"Loaded content from {len(all_documents)} document pages/sections.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
        chunks = text_splitter.split_documents(all_documents)
        self.stdout.write(f"Split documents into {len(chunks)} chunks.")

        # --- 4. Create Embeddings using GOOGLE's model ---
        self.stdout.write("Initializing Google Gemini Embeddings model...")
        # We use the "embedding-001" model from Google
        embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        self.stdout.write("Creating embeddings and saving to database... This may take a while.")
        
        # --- The rest of the script is almost the same ---
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.page_content for chunk in batch_chunks]
            
            # This call now goes to Google's API, which has a generous free tier
            batch_embeddings = embeddings_model.embed_documents(batch_texts)

            knowledge_chunks_to_create = []
            for j, chunk in enumerate(batch_chunks):
                embedding = batch_embeddings[j]
                source_name = os.path.basename(chunk.metadata.get('source', 'Unknown'))
                
                knowledge_chunks_to_create.append(
                    KnowledgeChunk(
                        source=source_name,
                        content=chunk.page_content,
                        # The embedding dimension for this Google model is 768
                        embedding_json=json.dumps(embedding)
                    )
                )
            
            KnowledgeChunk.objects.bulk_create(knowledge_chunks_to_create)
            self.stdout.write(f"Processed batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

        self.stdout.write(self.style.SUCCESS('Successfully built the knowledge base using Google Gemini!'))