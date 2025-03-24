import os
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app import models, schemas, crud, auth, utils, background_tasks
from app.database import SessionLocal, engine
from typing import List
from fastapi_utils.tasks import repeat_every
from datetime import timedelta
from dotenv import load_dotenv


dotenv_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path)

ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

models.Base.metadata.create_all(bind=engine)


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication dependency
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return auth.get_current_user(db, token)


@app.post("/upload/", response_model=schemas.FileStatus)
async def upload_file(
    chunk_number: int,
    total_chunks: int,
    file_id: str,
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle file chunk upload.
    """
    chunk_data = await file.read()
    utils.save_chunk(file_id, chunk_number, chunk_data)
    if chunk_number == total_chunks:
        utils.assemble_file(file_id)
        crud.update_file_status(db, file_id, "complete")
    else:
        crud.update_file_status(db, file_id, "incomplete")
    return crud.get_file_status(db, file_id)


@app.get("/download/{file_id}")
async def download_file(
    file_id: str,
    request: Request,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle file download with support for range requests.
    """
    file_path = utils.get_file_path(file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return utils.range_requests_response(request, file_path)


@app.get("/status/{file_id}", response_model=schemas.FileStatus)
def get_file_status(
    file_id: str,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve the current status of a file.
    """
    status = crud.get_file_status(db, file_id)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")
    return status


@app.on_event("startup")
@repeat_every(seconds=3600)  # Run every hour
def cleanup_incomplete_uploads():
    """
    Background task to clean up incomplete uploads.
    """
    background_tasks.cleanup_incomplete_uploads()


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
