# backend/chatbot/management/commands/cleanup_knowledge_base.py

import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from chatbot.models import KnowledgeChunk
from chatbot.knowledge_base_manager import sync_file_to_kb

class Command(BaseCommand):
    help = 'Clean up corrupted files and rebuild the knowledge base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean-files',
            action='store_true',
            help='Remove corrupted and temporary files from data directory',
        )
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild the knowledge base after cleanup',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation',
        )

    def handle(self, *args, **options):
        data_path = os.path.join(settings.BASE_DIR, 'data')
        
        if not os.path.exists(data_path):
            self.stdout.write(self.style.ERROR(f"Data directory not found: {data_path}"))
            return

        self.stdout.write(f"Scanning data directory: {data_path}")
        
        # Find all files
        all_files = []
        corrupted_files = []
        temporary_files = []
        
        for filename in os.listdir(data_path):
            file_path = os.path.join(data_path, filename)
            if os.path.isfile(file_path):
                all_files.append(file_path)
                
                # Check for temporary files
                if filename.startswith('~$') or filename.startswith('._') or filename.startswith('Thumbs.db'):
                    temporary_files.append(file_path)
                    self.stdout.write(f"  [TEMP] {filename}")
                
                # Check for potentially corrupted PDFs
                elif filename.endswith('.pdf'):
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(1024)
                            if not header.startswith(b'%PDF'):
                                corrupted_files.append(file_path)
                                self.stdout.write(f"  [CORRUPT] {filename} - Invalid PDF header")
                            elif b'%%EOF' not in header and os.path.getsize(file_path) < 10000:
                                corrupted_files.append(file_path)
                                self.stdout.write(f"  [CORRUPT] {filename} - Missing EOF marker")
                    except Exception as e:
                        corrupted_files.append(file_path)
                        self.stdout.write(f"  [CORRUPT] {filename} - Error reading file: {e}")
        
        self.stdout.write(f"\nFound {len(all_files)} total files")
        self.stdout.write(f"Found {len(temporary_files)} temporary files")
        self.stdout.write(f"Found {len(corrupted_files)} corrupted files")
        
        if not options['clean_files'] and not options['rebuild']:
            self.stdout.write("\nUse --clean-files to remove corrupted/temporary files")
            self.stdout.write("Use --rebuild to rebuild the knowledge base")
            return
        
        # Clean up files if requested
        if options['clean_files']:
            if not options['force']:
                confirm = input(f"\nAre you sure you want to remove {len(temporary_files) + len(corrupted_files)} files? (yes/no): ")
                if confirm.lower() != 'yes':
                    self.stdout.write("Cleanup cancelled.")
                    return
            
            # Remove temporary files
            for file_path in temporary_files:
                try:
                    os.remove(file_path)
                    self.stdout.write(f"  [REMOVED] {os.path.basename(file_path)}")
                except Exception as e:
                    self.stdout.write(f"  [ERROR] Failed to remove {os.path.basename(file_path)}: {e}")
            
            # Remove corrupted files
            for file_path in corrupted_files:
                try:
                    os.remove(file_path)
                    self.stdout.write(f"  [REMOVED] {os.path.basename(file_path)}")
                except Exception as e:
                    self.stdout.write(f"  [ERROR] Failed to remove {os.path.basename(file_path)}: {e}")
            
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully removed {len(temporary_files) + len(corrupted_files)} files"))
        
        # Rebuild knowledge base if requested
        if options['rebuild']:
            if not options['force']:
                confirm = input(f"\nAre you sure you want to rebuild the knowledge base? This will clear all existing chunks. (yes/no): ")
                if confirm.lower() != 'yes':
                    self.stdout.write("Rebuild cancelled.")
                    return
            
            self.stdout.write("\nClearing existing knowledge base...")
            deleted_count, _ = KnowledgeChunk.objects.all().delete()
            self.stdout.write(f"Removed {deleted_count} existing knowledge chunks")
            
            self.stdout.write("\nRebuilding knowledge base...")
            remaining_files = [f for f in all_files if f not in temporary_files and f not in corrupted_files]
            
            for file_path in remaining_files:
                filename = os.path.basename(file_path)
                if filename.endswith(('.pdf', '.csv')):
                    self.stdout.write(f"Processing: {filename}")
                    try:
                        sync_file_to_kb(file_path)
                    except Exception as e:
                        self.stdout.write(f"  [ERROR] Failed to process {filename}: {e}")
            
            # Count total chunks
            total_chunks = KnowledgeChunk.objects.count()
            self.stdout.write(self.style.SUCCESS(f"\nKnowledge base rebuilt successfully! Total chunks: {total_chunks}"))
        
        self.stdout.write("\nCleanup and rebuild completed!")
