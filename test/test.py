import os
from daytona import Daytona, DaytonaConfig

daytona = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
sandbox = daytona.create()
try:
    result = sandbox.process.code_run("print('hello from sandbox')")
    print(result.result)
finally:
    sandbox.delete()