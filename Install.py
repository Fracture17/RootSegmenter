import os


#os.system(fR"C:\Users\johno\PycharmProjects\RootSegmenter\.venv\Scripts\python.exe -m PyInstaller Main.spec")
#quit()

DLLs = list(os.listdir("C++/lib"))
binaryText = " ".join([f"--add-binary C++/lib/{name}:C++/lib/{name}" for name in DLLs])
print(binaryText)

os.system(fR"C:\Users\johno\PycharmProjects\RootSegmenter\.venv\Scripts\python.exe -m PyInstaller --onefile Main.py --noupx --hidden-import=numpy.core._multiarray_umath {binaryText}")
