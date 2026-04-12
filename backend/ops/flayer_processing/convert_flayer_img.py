from backend.app.db.data_preprocessing.pdf_to_img import pdf_converter_img
from pathlib import Path
from termcolor import cprint

def convert_flayer_img_automation():
    current_dir = Path(__file__).parent.parent.parent.parent

    flayers_dir = current_dir / "backend" / "data" / "data_test" / "flayers"
    
    pdf_paths = [pdf for pdf in flayers_dir.rglob("*.pdf")]
    cprint("loading the following pdf files:", "green")
    [cprint(pdf, "blue") for pdf in pdf_paths]
    for pdf_path in pdf_paths:
        output_dir = pdf_path.parent / "img"
        cprint(f"converting {pdf_path} to images in {output_dir}", "yellow")
        pdf_converter_img(str(pdf_path), str(output_dir))
        cprint(f"finished converting {pdf_path}", "green")
