import subprocess
import os


def build_pdf(latex_string, filename="test"):

    tex_file = f"{filename}.tex"

    with open(tex_file, "w") as f:
        f.write(latex_string)

    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", tex_file],
        stdout=subprocess.DEVNULL
    )

    # Remove aux files
    for ext in ["aux", "log"]:
        file = f"{filename}.{ext}"
        if os.path.exists(file):
            os.remove(file)

    print(f"PDF generated: {filename}.pdf")