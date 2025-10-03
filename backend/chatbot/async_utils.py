# backend/chatbot/async_utils.py

import asyncio
import threading

def run_async(coro):
    """
    Runs an async coroutine in the current thread by creating and managing
    a new asyncio event loop. This is a crucial bridge for running async
    code from synchronous contexts like Django views or background threads.
    """
    # Check if we are in a thread that already has a running loop
    try:
        if asyncio.get_running_loop().is_running():
            # If so, just run the coroutine in the existing loop
            return asyncio.run_coroutine_threadsafe(coro, asyncio.get_running_loop()).result()
    except RuntimeError:
        # 'no running loop in thread'
        pass

    # If no loop is running, create a new one
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        # Run the coroutine until it completes
        result = loop.run_until_complete(coro)
    finally:
        # Ensure the loop is closed
        loop.close()
        # It's good practice to set the loop to None for the thread
        asyncio.set_event_loop(None)
        
    return result