from fastapi import FastAPI, File, Request, UploadFile
from fastapi.templating import Jinja2Templates
from services.parser import parse_log

from services.validator import validate_file

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.post("/upload")
async def upload_log(
    request: Request,
    log_file: UploadFile = File(...),
):
    is_valid, error_message = validate_file(log_file.filename or "")

    if not is_valid:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": error_message,
            },
            status_code=400,
        )
    analysis = parse_log(log_file.file)

    return templates.TemplateResponse(
     request=request,
     name="result.html",
     context={
        "filename": log_file.filename,
        "analysis": analysis,
    },
)