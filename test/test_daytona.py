import os
from daytona import Daytona, DaytonaConfig

daytona = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
print("Creating sandbox...")
sandbox = daytona.create()
print("Sandbox created:", sandbox)

try:
    print("\nsandbox attrs:", [a for a in dir(sandbox) if not a.startswith("_")])
    print("\nsandbox.process attrs:", [a for a in dir(sandbox.process) if not a.startswith("_")])

    result = sandbox.process.code_run("print('hello from sandbox')")
    print("\nRESULT:", result)
    print("exit_code:", result.exit_code)
    print("output:", result.result)
finally:
    sandbox.delete()
    print("\nsandbox deleted")