from pydantic import BaseModel
from datetime import datetime

class FileStatus(BaseModel):
    file_id: str
    status: str
    last_modified: datetime

    class Config:
        orm_mode = True

class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
