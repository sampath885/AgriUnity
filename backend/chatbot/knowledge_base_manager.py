# backend/chatbot/knowledge_base_manager.py

import os
import json
import time
import re
import asyncio
import pandas as pd
from django.db import connection, OperationalError
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .models import KnowledgeChunk
from .async_utils import run_async
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DATA_PATH = os.path.join(settings.BASE_DIR, 'data')

# --- MODEL INITIALIZATION HELPER ---
def get_embedding_model():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in .env file.")
    
    # Fix for async event loop issues in background threads
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create a new one for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Create embeddings model with proper async handling
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", 
        google_api_key=GOOGLE_API_KEY
    )
    
    return embeddings

# --- PDF VALIDATION HELPER ---
def is_valid_pdf_file(file_path):
    """Check if a PDF file is valid and not corrupted"""
    try:
        # Skip temporary files (common in Windows)
        filename = os.path.basename(file_path)
        if filename.startswith('~$') or filename.startswith('._'):
            print(f"   [SKIP] Temporary file detected: {filename}")
            return False
        
        # Check file size (too small files are likely corrupted)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:  # Less than 1KB
            print(f"   [SKIP] File too small ({file_size} bytes): {filename}")
            return False
        
        # Check if file is actually a PDF by reading header
        with open(file_path, 'rb') as f:
            header = f.read(1024)  # Read first 1KB
            
            # Check for PDF magic number
            if not header.startswith(b'%PDF'):
                print(f"   [SKIP] Invalid PDF header: {filename}")
                return False
            
            # Check for EOF marker
            if b'%%EOF' not in header:
                # For very short PDFs, this might be normal, but let's be cautious
                if file_size < 10000:  # Less than 10KB
                    print(f"   [SKIP] Small file without EOF marker: {filename}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"   [SKIP] Error validating file {os.path.basename(file_path)}: {e}")
        return False

# --- PDF PROCESSOR ---
def process_pdf_into_chunks(file_path):
    filename = os.path.basename(file_path)
    print(f"-> Processing PDF: {filename}")
    
    # Validate PDF file first
    if not is_valid_pdf_file(file_path):
        print(f"   [SKIP] Invalid/corrupted PDF: {filename}")
        return []
    
    # Retry logic for loading the PDF
    max_retries = 3  # Reduced from 5 to 3
    retry_delay_seconds = 1  # Reduced delay
    for attempt in range(max_retries):
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            print(f"-> Successfully loaded {filename}.")
            break
        except Exception as e:
            print(f"   [Attempt {attempt + 1}/{max_retries}] Warning: Could not access {filename}. Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay_seconds)
                retry_delay_seconds *= 2  # Exponential backoff
            else:
                print(f"   [ERROR] Failed to load {filename} after {max_retries} attempts. Skipping.")
                return []
    else:
        print(f"   [ERROR] Failed to load {filename} after {max_retries} attempts. Skipping.")
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    batch_texts = [chunk.page_content for chunk in chunks]
    if not batch_texts:
        return []

    # Fix event loop issues for embeddings in background threads
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create a new one for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Use synchronous embeddings to avoid event-loop issues in background threads
    embeddings_model = get_embedding_model()
    batch_embeddings = embeddings_model.embed_documents(batch_texts)

    knowledge_chunks_to_create = []
    for i, chunk in enumerate(chunks):
        embedding = batch_embeddings[i]
        knowledge_chunks_to_create.append(
            KnowledgeChunk(source=filename, content=chunk.page_content, embedding_json=json.dumps(embedding))
        )
    
    print(f"-> Successfully created {len(knowledge_chunks_to_create)} knowledge chunks for {filename}.")
    return knowledge_chunks_to_create

# --- LARGE CSV PROCESSOR (IMPROVED VERSION) ---
def process_large_csv_in_batches(file_path):
    filename = os.path.basename(file_path)
    print(f"-> Starting memory-efficient processing for large CSV: {filename}")
    
    # Tuneable knobs via env for production-scale ingestion
    pandas_chunk_size = int(os.getenv("CSV_PANDAS_CHUNK_SIZE", "200000"))
    embedding_batch_size = int(os.getenv("CSV_EMBED_BATCH_SIZE", "1024"))
    sample_every_n = int(os.getenv("CSV_SAMPLE_EVERY_N", "1"))  # 1 = use all rows
    date_cutoff_days = int(os.getenv("CSV_DATE_CUTOFF_DAYS", "0"))  # 0 = disabled
    aggregate_monthly = os.getenv("CSV_USE_MONTHLY_AGGREGATION", "0") == "1"
    total_chunks_saved = 0
    
    created_loop = None
    try:
        # Optimize SQLite for concurrent writes if used
        try:
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA journal_mode=WAL;")
                    cursor.execute("PRAGMA synchronous=NORMAL;")
                    cursor.execute("PRAGMA busy_timeout=60000;")
        except Exception:
            pass
        # Ensure a current event loop exists in this watcher thread for libraries that expect it
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            created_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(created_loop)

        # Helper to normalize column names: lowercase and remove non-alphanumeric chars
        def normalize_name(name: str) -> str:
            return re.sub(r"[^a-z0-9]", "", str(name).lower())

        # Define potential normalized names we are looking for
        normalized_options = {
            'state': {'state'},
            'district': {'district', 'districtname'},
            'market': {'market', 'marketname'},
            'commodity': {'commodity'},
            'variety': {'variety'},
            # Many datasets use any of these for arrival date
            'arrival_date': {'arrivaldate', 'date', 'pricedate'},
            # Price can be written in multiple ways; we match the modal/avg price field
            'modal_price': {'modalprice', 'averageprice', 'avgprice', 'modal'}
        }

        # Read the first row to determine actual column names and build a lookup by normalized name
        df_head = pd.read_csv(file_path, nrows=1)
        normalized_to_actual = {normalize_name(col): col for col in df_head.columns}

        # Resolve actual columns for each canonical key using normalized matching
        actual_cols = {}
        for key, options in normalized_options.items():
            resolved_col = None
            for option in options:
                if option in normalized_to_actual:
                    resolved_col = normalized_to_actual[option]
                    break
            # Special-case: handle common exact headers not covered by normalization set
            if resolved_col is None:
                # Try a few more exact header variants seen in the wild
                fallbacks = {
                    'state': {'STATE', 'State'},
                    'district': {'District Name', 'district_name'},
                    'market': {'Market Name', 'market_name'},
                    'arrival_date': {'Arrival Date', 'Price Date', 'Date'},
                    'modal_price': {'Modal Price', 'Modal Price (Rs./Quintal)', 'Modal_Price'}
                }.get(key, set())
                for fb in fallbacks:
                    if fb in df_head.columns:
                        resolved_col = fb
                        break
            actual_cols[key] = resolved_col

        # Check if all required columns were found
        required_keys = ['state', 'district', 'market', 'commodity', 'modal_price', 'arrival_date']
        if not all(actual_cols[key] for key in required_keys):
            missing = [key for key in required_keys if not actual_cols[key]]
            raise ValueError(f"CSV file is missing required columns. Could not find a match for: {missing}")

        print("Detected columns:", {k: actual_cols[k] for k in required_keys})

        use_columns = [actual_cols[key] for key in required_keys] + ([actual_cols['variety']] if actual_cols.get('variety') else [])

        for i, df_chunk in enumerate(
            pd.read_csv(
                file_path,
                chunksize=pandas_chunk_size,
                on_bad_lines='skip',
                low_memory=False,
                usecols=use_columns
            )
        ):
            print(f"  -> Processing pandas chunk #{i+1}...")
            # Optional: filter by recent dates only
            if date_cutoff_days > 0:
                cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=date_cutoff_days)
                # Coerce errors to NaT, then drop rows older than cutoff
                df_chunk[actual_cols['arrival_date']] = pd.to_datetime(
                    df_chunk[actual_cols['arrival_date']], errors='coerce', dayfirst=False, infer_datetime_format=True
                )
                df_chunk = df_chunk[df_chunk[actual_cols['arrival_date']] >= cutoff]

            # Deterministic downsampling for very large datasets
            if sample_every_n > 1 and not df_chunk.empty:
                df_chunk = df_chunk.iloc[::sample_every_n, :]

            # Clean and prepare the chunk
            df_chunk.dropna(subset=[actual_cols[key] for key in required_keys], inplace=True)
            if df_chunk.empty:
                continue

            if aggregate_monthly:
                # Aggregate by month to massively reduce number of chunks
                if not pd.api.types.is_datetime64_any_dtype(df_chunk[actual_cols['arrival_date']]):
                    df_chunk[actual_cols['arrival_date']] = pd.to_datetime(df_chunk[actual_cols['arrival_date']], errors='coerce')
                df_chunk.dropna(subset=[actual_cols['arrival_date']], inplace=True)
                if df_chunk.empty:
                    continue
                df_chunk['_month'] = df_chunk[actual_cols['arrival_date']].dt.to_period('M').astype(str)
                group_cols = [
                    actual_cols['state'], actual_cols['district'], actual_cols['market'], actual_cols['commodity'], '_month'
                ]
                grouped = (
                    df_chunk
                    .groupby(group_cols)[actual_cols['modal_price']]
                    .agg(['count', 'min', 'max', 'mean'])
                    .reset_index()
                )

                docs_to_embed = [
                    (
                        f"In {row[actual_cols['state']]}, district {row[actual_cols['district']]}, market {row[actual_cols['market']]}, "
                        f"for {row[actual_cols['commodity']]} during {row['_month']}, modal price stats over {int(row['count'])} entries: "
                        f"min={row['min']:.2f}, max={row['max']:.2f}, avg={row['mean']:.2f} (Rs./Quintal)."
                    )
                    for _, row in grouped.iterrows()
                ]
            else:
                # Vectorized doc construction for speed
                arrival_vals = df_chunk[actual_cols['arrival_date']].astype('string').to_numpy()
                state_vals = df_chunk[actual_cols['state']].astype('string').to_numpy()
                district_vals = df_chunk[actual_cols['district']].astype('string').to_numpy()
                market_vals = df_chunk[actual_cols['market']].astype('string').to_numpy()
                commodity_vals = df_chunk[actual_cols['commodity']].astype('string').to_numpy()
                price_vals = df_chunk[actual_cols['modal_price']].astype('string').to_numpy()
                if actual_cols.get('variety') and actual_cols['variety'] in df_chunk.columns:
                    variety_vals = df_chunk[actual_cols['variety']].astype('string').to_numpy()
                else:
                    variety_vals = None

                num_rows = len(arrival_vals)
                docs_to_embed = [
                    (
                        f"On {arrival_vals[i]}, in the state of {state_vals[i]}, "
                        f"district {district_vals[i]}, market {market_vals[i]}, "
                        f"the modal price for {commodity_vals[i]} "
                        f"({variety_vals[i] if variety_vals is not None else 'N/A'}) was {price_vals[i]} per quintal."
                    )
                    for i in range(num_rows)
                ]

            # Fix event loop issues for embeddings in background threads
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create a new one for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Initialize embeddings model lazily per chunk to avoid long-lived connections in watcher threads
            embeddings_model = get_embedding_model()

            # Process in embedding batches
            for j in range(0, len(docs_to_embed), embedding_batch_size):
                batch_texts = docs_to_embed[j:j + embedding_batch_size]
                if not batch_texts: continue

                # Use synchronous embeddings to avoid event-loop issues in watcher threads
                # Add simple exponential backoff for transient failures
                backoff_seconds = 1.0
                max_attempts = 5
                last_err = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        batch_embeddings = embeddings_model.embed_documents(batch_texts)
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        time.sleep(backoff_seconds)
                        backoff_seconds = min(backoff_seconds * 2, 30)
                if last_err is not None:
                    raise last_err
                
                knowledge_chunks_to_create = [
                    KnowledgeChunk(
                        source=filename,
                        content=batch_texts[k],
                        embedding_json=json.dumps(batch_embeddings[k])
                    )
                    for k in range(len(batch_texts))
                ]

                # Bulk insert with retry/backoff on database locks
                db_backoff = 1.0
                for _attempt in range(6):
                    try:
                        KnowledgeChunk.objects.bulk_create(knowledge_chunks_to_create, batch_size=20000)
                        break
                    except OperationalError as oe:
                        msg = str(oe).lower()
                        if 'database is locked' in msg or 'database is busy' in msg:
                            time.sleep(db_backoff)
                            db_backoff = min(db_backoff * 2, 30)
                            continue
                        raise
                total_chunks_saved += len(knowledge_chunks_to_create)
                print(f"    -> Saved {len(knowledge_chunks_to_create)} knowledge chunks to DB. Total so far: {total_chunks_saved}")

    except ValueError as ve:
        print(f"[VALIDATION ERROR] {ve}")
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed during large CSV processing: {e}")
        # Print the first few rows of the chunk that failed for debugging
        if 'df_chunk' in locals():
            print("--- Failing Chunk Head ---")
            print(df_chunk.head().to_string())
            print("--------------------------")
    finally:
        # Clean up event loop
        try:
            current_loop = asyncio.get_event_loop()
            if current_loop and current_loop.is_running():
                # Don't close a running loop
                pass
            elif current_loop:
                current_loop.close()
        except RuntimeError:
            # No event loop to clean up
            pass
        finally:
            asyncio.set_event_loop(None)

    return total_chunks_saved

# --- PUBLIC INTERFACE FUNCTIONS (used by the watcher) ---
def sync_file_to_kb(file_path):
    filename = os.path.basename(file_path)
    print(f"SYNC: Synchronizing file '{filename}'...")
    
    # Skip temporary and system files
    if filename.startswith('~$') or filename.startswith('._') or filename.startswith('Thumbs.db'):
        print(f"SYNC: Skipping temporary/system file '{filename}'")
        return
    
    # Remove old chunks for this file
    deleted_count, _ = KnowledgeChunk.objects.filter(source=filename).delete()
    if deleted_count > 0:
        print(f"SYNC: Removed {deleted_count} old chunks for '{filename}'")
    
    if filename.endswith(".pdf"):
        chunks_to_create = process_pdf_into_chunks(file_path)
        if chunks_to_create:
            KnowledgeChunk.objects.bulk_create(chunks_to_create)
            print(f"SYNC: Successfully added {len(chunks_to_create)} chunks for '{filename}'.")
        else:
            print(f"SYNC: No valid chunks created for '{filename}' (file may be corrupted)")
    elif filename.endswith(".csv"):
        chunks_saved_count = process_large_csv_in_batches(file_path)
        print(f"SYNC: Finished processing CSV. Total new chunks added: {chunks_saved_count}.")
    else:
        print(f"SYNC: Skipping unsupported file type '{filename}'.")

def remove_file_from_kb(file_path):
    filename = os.path.basename(file_path)
    print(f"DELETE: File '{filename}' deleted. Removing from knowledge base...")
    deleted_count, _ = KnowledgeChunk.objects.filter(source=filename).delete()
    print(f"DELETE: Successfully deleted {deleted_count} chunks for '{filename}'.")