import fitz
import os
def pdf_converter_img(pdf_path:str, output_dir:str):
    """
    Convert a PDF file to a series of images.
    """
    os.makedirs(output_dir, exist_ok=True)
    mat = fitz.Matrix(1.0, 1.0)
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc.load_page(i)
    
        pix = page.get_pixmap(matrix=mat)
        pix.save(f"{output_dir}/page_{i:02d}.png")
    doc.close()
if __name__ == "__main__":
    pdf_path = "/home/lite/Desktop/Projects/FitnessAI/fit_ai/backend/data/data_test/flayers/provigo/PDF.js viewer.pdf"
    output_dir = "/home/lite/Desktop/Projects/FitnessAI/fit_ai/backend/data/data_test/flayers/provigo/img"
    pdf_converter_img(pdf_path, output_dir)