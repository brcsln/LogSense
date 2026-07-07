from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "product": "LogSense",
        "message": "Welcome to LogSense 🚀"
    }