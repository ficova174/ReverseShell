import subprocess

class SpecialInterface:
    def __init__(self):
        self.current_location = None
        self.result = None
    
    def where_am_i(self):
        location = subprocess.run(
            ["PowerShell", "-NoProfile", "-NoLogo", "-WindowStyle", "Hidden", "-Command", "(Get-Location).Path"],
            capture_output=True,
            text=True
        )

        if location.stderr:
            self.current_location = f"where_am_i() error : {location.stderr.strip()}"
        else:
            self.current_location = location.stdout.strip()

    def go(self, what):
        result = subprocess.run(
            ["PowerShell", "-NoProfile", "-NoLogo", "-WindowStyle", "Hidden", "-Command", what],
            capture_output=True,
            text=True,
            cwd=self.current_location
        )

        if result.stderr:
            self.result = f"go() error : {result.stderr.strip()}"
        else:
            self.result = result.stdout.strip()

        self.where_am_i()

if __name__ == "__main__":
    special_interface = SpecialInterface()
    special_interface.go("ls")
    special_interface.result
