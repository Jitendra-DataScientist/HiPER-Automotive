from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()

# This would be replaced with your device authentication system
# For this assignment, I am using a simple dictionary (ideally it should come from the environment)
device_credentials = {
    "device1": "password1",
    "device2": "password2",
}

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint to authenticate devices and provide access tokens.
    """
    # Verify device credentials
    if form_data.username not in device_credentials or device_credentials[form_data.username] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect device ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with device ID as subject
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
