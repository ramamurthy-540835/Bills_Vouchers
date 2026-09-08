import asyncio
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from io import BytesIO
from app.services.documents import validate_upload

def test_rejects_content_with_fake_image_mime():
    upload=UploadFile(filename="fake.jpg",file=BytesIO(b"not a jpeg"),headers={"content-type":"image/jpeg"})
    with pytest.raises(HTTPException) as error: asyncio.run(validate_upload(upload))
    assert error.value.status_code==400
