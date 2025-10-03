# backend/users/views.py

from rest_framework import generics, status, permissions # <--- IMPORT PERMISSIONS
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, UserSerializer, SendOTPSerializer, VerifyOTPSerializer
from rest_framework.views import APIView
from django.conf import settings


class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny] # <--- ADD THIS LINE

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    permission_classes = [permissions.AllowAny] # <--- ADD THIS LINE

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            })
        else:
            # A more specific error message for failed login
            return Response({"detail": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)


class SendOTPAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SendOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()
        response = {"message": "OTP sent successfully"}
        # In development, return the code for convenience
        if getattr(settings, 'DEBUG', False):
            response["debug_code"] = otp.code
        return Response(response, status=status.HTTP_200_OK)


class VerifyOTPAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key,
        }, status=status.HTTP_200_OK)