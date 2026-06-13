import os
from daytona import Daytona, DaytonaConfig

daytona = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
sandbox = daytona.create()

try:
    print("fs attrs:", [a for a in dir(sandbox.fs) if not a.startswith("_")])

    # try uploading a small text file
    sandbox.fs.upload_file(b"hello sandbox file", "/tmp/test.txt")
    print("upload ok")

    result = sandbox.process.code_run("print(open('/tmp/test.txt').read())")
    print("read back:", result.result)

    # check if pdfplumber is available
    check = sandbox.process.code_run("import pdfplumber; print('pdfplumber available')")
    print("pdfplumber check:", check.result if check.exit_code == 0 else f"NOT AVAILABLE (exit {check.exit_code}): {check.result}")

finally:
    sandbox.delete()