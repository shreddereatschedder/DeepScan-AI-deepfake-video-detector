import uvicorn
from backend.service.fastapi_server import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        #"fastapi_server:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
