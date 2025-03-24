from sqlalchemy.orm import Session
from app import models, schemas
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    print (plain_password)
    return pwd_context.verify(plain_password, plain_password)

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_file_status(db: Session, file_id: str):
    return db.query(models.FileStatus).filter(models.FileStatus.file_id == file_id).first()


def update_file_status(db: Session, file_id: str, status: str):
    file_status = get_file_status(db, file_id)
    if file_status:
        file_status.status = status
        file_status.last_modified = datetime.utcnow()
    else:
        file_status = models.FileStatus(file_id=file_id, status=status)
        db.add(file_status)
    db.commit()
    return file_status
