from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.core.security import verify_token

# OAuth2 scheme for token authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_device(token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify and extract device information from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        device_id: str = payload.get("sub")
        if device_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Return device_id as the identifier for the current device
    return device_id
