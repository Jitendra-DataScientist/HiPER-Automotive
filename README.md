# Secure File Transfer API

A secure and reliable FastAPI application for handling file transfers between remote devices and a server. This API supports chunked uploads, resumable transfers, partial downloads, and background cleanup processes.

## Features

- **Chunked File Uploads**: Upload files in small pieces with custom binary headers that include checksums for data integrity.
- **Resumable Transfers**: Uploads can be interrupted and resumed from where they left off.
- **Partial Downloads**: Support for the HTTP Range header to download specific parts of files.
- **Real-Time Status Monitoring**: Endpoints to check the status of file transfers.
- **Background Cleanup**: Automated processing of stale uploads and cleanup of unused resources.
- **JWT Authentication**: Secure token-based authentication for device authorization.

## Project Structure

```
.
├── README.md
├── main.py
├── requirements.txt
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dependencies.py
│   │   ├── routers
│   │   │   ├── __init__.py
│   │   │   └── files.py
│   │   └── schemas.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db
│   │   ├── __init__.py
│   │   └── models.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── file_service.py
│   │   └── cleanup_service.py
│   └── utils
│       ├── __init__.py
│       └── file_utils.py
└── tests
    ├── __init__.py
    ├── conftest.py
    └── test_files.py
```

## Setup Instructions

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create an `.env` file in the root directory with the following variables:
   ```
   SECRET_KEY=your_secret_key  # Use a strong secret key for JWT token generation
   ACCESS_TOKEN_EXPIRE_MINUTES=30  # the token generated from auth/token endpoint would expire in 30 minutes
   ```
4. Run the application:
   ```
   python main.py
   ```
   Alternatively, you can use Uvicorn directly:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8005 --reload
   ```
   One could specify some other port for the port flag. The flags reload, port and host aren't mandatory.

## API Endpoints

### Authentication

- **POST /auth/token**: Authenticate a device and receive a JWT token

### File Operations

- **POST /api/files/upload**: Upload a file chunk with a custom binary header
- **GET /api/files/download/{filename}**: Download a complete file or a specific range
- **GET /api/files/status/{filename}**: Get the status of a file upload
- **GET /api/files**: List all files for the authenticated device
- **DELETE /api/files/{filename}**: Delete a file or cancel an ongoing upload

## File Chunk Format

File chunks must include a custom binary header with the following format:
- start_byte: 8 bytes (big-endian)
- end_byte: 8 bytes (big-endian)
- checksum: 1 byte (sum of chunk bytes modulo 256)

## Design Decisions

1. **Asynchronous Operations**: FastAPI's asynchronous capabilities are leveraged for efficient I/O operations, especially during file uploads and downloads.

2. **Chunked Storage**: File chunks are initially stored separately to support resumable uploads, and then assembled once all chunks are received.

3. **Background Cleanup**: A periodic task runs to process stale uploads and clean up temporary resources.

4. **JWT Authentication**: Token-based authentication ensures that only authorized devices can access the API endpoints.

5. **File Status Tracking**: Detailed status information allows devices to monitor upload progress and determine where to resume interrupted transfers.

6. **Range Requests**: Support for HTTP Range header enables efficient partial downloads of large files.

## Future Enhancements

1. **Cloud Storage Integration**: The design allows for future integration with cloud storage solutions by extending the FileService class.

2. **Database Storage**: Replace file-based metadata with a database for improved scalability.

3. **Multiple Storage Backends**: Add support for different storage backends such as S3, Azure Blob Storage, etc.

4. **Rate Limiting**: Implement rate limiting to prevent abuse of the API.

5. **Multi-tenancy**: Extend the authentication system to support multiple tenants or organizations.

## Security Considerations

- All endpoints require JWT authentication
- File chunk checksums ensure data integrity
- Background processes prevent resource exhaustion
- Proper error handling prevents information leakage
