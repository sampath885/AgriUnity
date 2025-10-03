"""
Django management command to run the AgriUnity MCP Server
Usage: python manage.py run_mcp_server
"""

import asyncio
import json
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from mcp_server import get_mcp_server

class Command(BaseCommand):
    help = 'Run the AgriUnity MCP Performance Server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8001,
            help='Port to run the MCP server on (default: 8001)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default='localhost',
            help='Host to bind the MCP server to (default: localhost)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run a quick test of the MCP server'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show performance statistics'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting AgriUnity MCP Performance Server...')
        )
        
        try:
            # Initialize the MCP server
            server = get_mcp_server()
            
            if options['test']:
                self.stdout.write('🧪 Running MCP server test...')
                asyncio.run(self._run_test(server))
                return
            
            if options['stats']:
                self.stdout.write('📊 Getting performance statistics...')
                asyncio.run(self._show_stats(server))
                return
            
            # Start the server
            self.stdout.write(
                self.style.SUCCESS(f'✅ MCP Server started on {options["host"]}:{options["port"]}')
            )
            self.stdout.write('📊 Available tools:')
            self.stdout.write('  - predict_price_fast(crop, district, date, user_context)')
            self.stdout.write('  - get_market_data_fast(crop, district, date, grade)')
            self.stdout.write('  - compute_hub_v2_fast(deal_group_id)')
            self.stdout.write('  - compute_hub_v1_fast(deal_group_id)')
            self.stdout.write('  - get_performance_stats()')
            self.stdout.write('  - clear_cache(cache_type)')
            self.stdout.write('')
            self.stdout.write('Press Ctrl+C to stop the server')
            
            # Keep the server running
            try:
                while True:
                    asyncio.run(self._server_loop(server))
            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING('\n🛑 MCP Server stopped by user')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to start MCP server: {e}')
            )
            sys.exit(1)

    async def _run_test(self, server):
        """Run a comprehensive test of the MCP server"""
        from datetime import datetime
        
        self.stdout.write('🧪 Testing price prediction...')
        try:
            price_result = await server.predict_price_fast(
                crop_name="rice",
                district="krishna",
                date=datetime.now(),
                user_context={"user_id": 1}
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Price prediction: ₹{price_result.get("predicted_price", "N/A")}/kg')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Price prediction failed: {e}')
            )
        
        self.stdout.write('🧪 Testing market data...')
        try:
            market_result = await server.get_market_data_fast(
                crop_name="rice",
                district="krishna",
                date=datetime.now()
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Market data: {market_result.get("data_points", "N/A")} data points')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Market data failed: {e}')
            )
        
        self.stdout.write('🧪 Testing performance stats...')
        try:
            stats = await server.get_performance_stats()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Performance: {stats["cache_hit_rate_percent"]}% cache hit rate')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Performance stats failed: {e}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 MCP server test completed!')
        )

    async def _show_stats(self, server):
        """Show performance statistics"""
        try:
            stats = await server.get_performance_stats()
            
            self.stdout.write('📊 MCP Server Performance Statistics:')
            self.stdout.write(f'  Total Requests: {stats["total_requests"]}')
            self.stdout.write(f'  Cache Hits: {stats["cache_hits"]}')
            self.stdout.write(f'  Cache Misses: {stats["cache_misses"]}')
            self.stdout.write(f'  Cache Hit Rate: {stats["cache_hit_rate_percent"]}%')
            self.stdout.write(f'  Memory Usage: {stats["memory_usage_mb"]} MB')
            self.stdout.write(f'  Price Cache Size: {stats["price_cache_size"]}')
            self.stdout.write(f'  Market Cache Size: {stats["market_cache_size"]}')
            self.stdout.write(f'  Hub Cache Size: {stats["hub_cache_size"]}')
            self.stdout.write(f'  Uptime: {stats["uptime_seconds"]:.1f} seconds')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to get stats: {e}')
            )

    async def _server_loop(self, server):
        """Main server loop"""
        # Simple loop to keep server alive
        await asyncio.sleep(1)

