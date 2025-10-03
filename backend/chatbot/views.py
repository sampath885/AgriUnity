# backend/chatbot/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .qa_logic import get_answer # Import our powerful QA function
from .models import ChatbotMessage
from .serializers import ChatMessageSerializer

class ChatbotAPI(APIView):
    """
    An API endpoint for the AgriGenie chatbot.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated] # Ensures only logged-in users can access this

    def post(self, request, *args, **kwargs):
        # 1. Get data from the incoming request
        user_message = request.data.get('message')
        
        if not user_message:
            return Response(
                {"error": "Message field is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Get the user's role from their profile
        # The 'request.user' object is available because of 'IsAuthenticated'
        user_role = request.user.role

        try:
            # 3. Persist user message
            ChatbotMessage.objects.create(user=request.user, sender=ChatbotMessage.SenderType.USER, content=user_message)

            # 4. Call our core logic function to get the AI's answer
            ai_response = get_answer(query=user_message, user_role=user_role, user_id=request.user.id)

            # 5. Persist AI response
            ChatbotMessage.objects.create(user=request.user, sender=ChatbotMessage.SenderType.AGENT, content=ai_response)

            # 6. Return the successful response
            return Response({"answer": ai_response}, status=status.HTTP_200_OK)
        except Exception as e:
            # Basic error handling in case the AI logic fails
            print(f"Error in QA Logic: {e}")
            return Response(
                {"error": "An error occurred while processing your request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, *args, **kwargs):
        """Returns last N chat messages for the current user."""
        try:
            limit = int(request.query_params.get('limit', 50))
        except Exception:
            limit = 50
        qs = ChatbotMessage.objects.filter(user=request.user).order_by('-created_at')[:limit]
        messages = list(reversed(list(qs)))
        data = ChatMessageSerializer(messages, many=True).data
        return Response(data, status=status.HTTP_200_OK)