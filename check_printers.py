import win32print
import win32api

printer_name = win32print.GetDefaultPrinter()
file_path = r"c:\Users\pullo\Downloads\robo print.pdf"  # Update this path if needed

print(f"Printing to: {printer_name}")

try:
    win32api.ShellExecute(0, "print", file_path, None, ".", 0)
    print("Print command sent successfully!")
except Exception as e:
    print("Error:", e)