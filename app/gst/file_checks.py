"""Bound parsing work before accepting uploaded evidence."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, BadZipFile


def validate_file(content, filename):
    extension = Path(filename).suffix.lower()
    if extension == '.pdf':
        if not content.lstrip().startswith(b'%PDF-'):
            raise ValueError('This file is not a readable PDF.')
    elif extension in {'.png', '.jpg', '.jpeg'}:
        from PIL import Image
        with Image.open(BytesIO(content)) as image:
            if image.format not in {'PNG', 'JPEG'} or image.width * image.height > 25000000:
                raise ValueError('Choose a PNG or JPEG photo smaller than 25 megapixels.')
            image.verify()
    elif extension == '.xlsx':
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 1500 or sum(e.file_size for e in entries) > 50 * 1024 * 1024:
                    raise ValueError('This workbook is too large to read. Split it into smaller files.')
                if '[Content_Types].xml' not in archive.namelist() or 'xl/workbook.xml' not in archive.namelist():
                    raise ValueError('Use an Excel workbook saved as .xlsx.')
                if any('vbaProject' in e.filename or 'externalLinks/' in e.filename for e in entries):
                    raise ValueError('Remove macros and external workbook links before uploading.')
        except BadZipFile:
            raise ValueError('This file is not a readable Excel workbook.') from None
    elif extension == '.csv':
        try:
            text = content.decode('utf-8-sig')
            if '\x00' in text:
                raise ValueError('Save your CSV as UTF-8 text.')
        except UnicodeDecodeError:
            raise ValueError('Save your CSV as UTF-8 text.') from None
    else:
        raise ValueError('Choose PDF, JPG, PNG, Excel or CSV files.')
