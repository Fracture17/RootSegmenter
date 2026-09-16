import os
import sys


#os.system(f"{sys.executable} -m PyInstaller Main.spec")
#quit()

#PyInstaller separates the source and destination of --add-binary with os.pathsep,
#which is ";" on Windows and ":" everywhere else.
DLLs = list(os.listdir("C++/lib"))
binaryText = " ".join([f"--add-binary C++/lib/{name}{os.pathsep}C++/lib/{name}" for name in DLLs])
print(binaryText)

os.system(f"{sys.executable} -m PyInstaller --onefile Main.py --noupx --hidden-import=numpy.core._multiarray_umath {binaryText}")
