"""
MovieBot Pure-Python PDF Generator Moduli
Ushbu modul hech qanday tashqi kutubxona (reportlab/fpdf) siz
standart PDF 1.4 fayllarini yaratib beradi.
"""

import os
import re
from datetime import datetime


def _latinize(text: str) -> str:
    """Cyrillic va maxsus belgilarni PDF standart Helvetica shriftiga moslashtirish"""
    if not text:
        return ""
    text = str(text)
    cyr_map = {
        'А':'A','а':'a','Б':'B','б':'b','В':'V','в':'v','Г':'G','г':'g',
        'Д':'D','д':'d','Е':'E','е':'e','Ё':'Yo','ё':'yo','Ж':'Zh','ж':'zh',
        'З':'Z','з':'z','И':'I','и':'i','Й':'Y','й':'y','К':'K','к':'k',
        'Л':'L','л':'l','М':'M','м':'m','Н':'N','н':'n','О':'O','о':'o',
        'П':'P','п':'p','Р':'R','р':'r','С':'S','с':'s','Т':'T','т':'t',
        'У':'U','у':'u','Ф':'F','ф':'f','Х':'Kh','х':'kh','Ц':'Ts','ц':'ts',
        'Ч':'Ch','ч':'ch','Ш':'Sh','ш':'sh','Щ':'Shch','щ':'shch','Ъ':'',
        'ъ':'','Ы':'Y','ы':'y','Ь':'','ь':'','Э':'E','э':'e','Ю':'Yu',
        'ю':'yu','Я':'Ya','я':'ya','Ў':'O\'','ў':'o\'','Қ':'Q','қ':'q',
        'Ғ':'G\'','ғ':'g\'','Ҳ':'H','ҳ':'h','‘':'\'','’':'\'','ʻ':'\'','`':'\''
    }
    res = []
    for ch in text:
        res.append(cyr_map.get(ch, ch))
    out = "".join(res)
    # Sanitize PDF string characters
    return out.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


class PDFBuilder:
    def __init__(self, title="MovieBot Analitik Hisoboti"):
        self.title = title
        self.pages = []  # list of commands lists
        self.current_page = []
        self.y = 800  # top to bottom
        self.page_width = 595.28
        self.page_height = 842.00
        self.margin = 40
        self.page_num = 1
        self._start_new_page()

    def _start_new_page(self):
        if self.current_page:
            self.pages.append(self.current_page)
        self.current_page = []
        self.y = 780

        # Background header bar
        self.current_page.append("0.1 0.12 0.18 rg") # dark navy
        self.current_page.append(f"30 790 535 35 re f")
        
        # Header text
        self.current_page.append("1 1 1 rg") # white
        self.current_page.append("BT /F1 14 Tf 45 802 Td (" + _latinize(self.title) + ") Tj ET")
        
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.current_page.append("0.8 0.85 0.9 rg")
        self.current_page.append("BT /F2 9 Tf 430 804 Td (" + _latinize(now_str) + ") Tj ET")

        # Footer line
        self.current_page.append("0.8 0.8 0.8 RG 0.5 w")
        self.current_page.append("30 40 535 0 M 30 40 535 40 L S")
        
        # Footer text
        self.current_page.append("0.4 0.4 0.4 rg")
        self.current_page.append(f"BT /F2 8 Tf 45 28 Td (MovieBot Rasmiy Analitik Hisoboti | Sahifa {self.page_num}) Tj ET")

        self.y = 760

    def check_space(self, needed_height=20):
        if self.y - needed_height < 50:
            self.page_num += 1
            self._start_new_page()

    def add_section_header(self, text):
        self.check_space(35)
        self.y -= 10
        # Light blue background bar
        self.current_page.append("0.9 0.94 0.98 rg")
        self.current_page.append(f"35 {self.y - 4} 525 20 re f")
        
        # Left accent border
        self.current_page.append("0.1 0.4 0.8 rg")
        self.current_page.append(f"35 {self.y - 4} 4 20 re f")

        self.current_page.append("0.1 0.2 0.4 rg")
        self.current_page.append(f"BT /F1 11 Tf 45 {self.y} Td ({_latinize(text)}) Tj ET")
        self.y -= 25

    def add_metric_cards(self, cards):
        """cards: list of tuples (label, val_str)"""
        self.check_space(55)
        card_w = (525 - (len(cards) - 1) * 10) / len(cards)
        x_start = 35
        
        self.y -= 45
        for i, (label, val) in enumerate(cards):
            x = x_start + i * (card_w + 10)
            # Card background box
            self.current_page.append("0.96 0.97 0.98 rg")
            self.current_page.append(f"{x} {self.y} {card_w} 40 re f")
            self.current_page.append("0.85 0.88 0.92 RG 1 w")
            self.current_page.append(f"{x} {self.y} {card_w} 40 re s")

            # Value text
            self.current_page.append("0.05 0.35 0.75 rg")
            self.current_page.append(f"BT /F1 13 Tf {x + 10} {self.y + 22} Td ({_latinize(val)}) Tj ET")

            # Label text
            self.current_page.append("0.4 0.45 0.5 rg")
            self.current_page.append(f"BT /F2 8 Tf {x + 10} {self.y + 8} Td ({_latinize(label)}) Tj ET")

        self.y -= 15

    def add_table(self, headers, rows, col_widths=None):
        """headers: list of str, rows: list of lists of str"""
        num_cols = len(headers)
        if not col_widths:
            col_widths = [525 / num_cols] * num_cols

        self.check_space(30)

        # Header row
        self.y -= 18
        self.current_page.append("0.2 0.25 0.35 rg")
        self.current_page.append(f"35 {self.y} 525 18 re f")

        x_curr = 35
        self.current_page.append("1 1 1 rg")
        for i, h in enumerate(headers):
            w = col_widths[i]
            self.current_page.append(f"BT /F1 9 Tf {x_curr + 5} {self.y + 5} Td ({_latinize(h)}) Tj ET")
            x_curr += w

        # Data rows
        for r_idx, row in enumerate(rows):
            self.check_space(18)
            self.y -= 16

            # Alternating background
            if r_idx % 2 == 1:
                self.current_page.append("0.97 0.98 0.99 rg")
                self.current_page.append(f"35 {self.y} 525 16 re f")

            # Row bottom border
            self.current_page.append("0.92 0.92 0.92 RG 0.5 w")
            self.current_page.append(f"35 {self.y} 525 0 M 35 {self.y} 560 {self.y} L S")

            x_curr = 35
            self.current_page.append("0.2 0.2 0.2 rg")
            for c_idx, cell in enumerate(row):
                w = col_widths[c_idx]
                cell_text = _latinize(str(cell))
                # Truncate text if too long
                if len(cell_text) > int(w / 5.5):
                    cell_text = cell_text[:int(w / 5.5) - 2] + ".."
                self.current_page.append(f"BT /F2 8 Tf {x_curr + 5} {self.y + 4} Td ({cell_text}) Tj ET")
                x_curr += w

        self.y -= 10

    def add_line_text(self, text, bold=False, size=9, color=(0.2, 0.2, 0.2)):
        self.check_space(size + 6)
        font = "/F1" if bold else "/F2"
        r, g, b = color
        self.y -= (size + 4)
        self.current_page.append(f"{r} {g} {b} rg")
        self.current_page.append(f"BT {font} {size} Tf 35 {self.y} Td ({_latinize(text)}) Tj ET")

    def build(self, output_path: str):
        if self.current_page:
            self.pages.append(self.current_page)

        # PDF indirect objects construction
        objects = []

        # Obj 1: Catalog
        objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")

        # Obj 2: Pages (Kids placeholder)
        page_obj_ids = [3 + i * 2 for i in range(len(self.pages))]
        kids_str = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
        objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(self.pages)} >>\nendobj")

        # Fonts
        font_f1_id = 3 + len(self.pages) * 2
        font_f2_id = font_f1_id + 1

        # Build Page and Content objects
        for idx, page_cmds in enumerate(self.pages):
            page_id = 3 + idx * 2
            content_id = page_id + 1

            page_str = (
                f"{page_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R\n"
                f"   /MediaBox [0 0 595.28 842.00]\n"
                f"   /Contents {content_id} 0 R\n"
                f"   /Resources << /Font << /F1 {font_f1_id} 0 R /F2 {font_f2_id} 0 R >> >>\n"
                f">>\nendobj"
            )
            objects.append(page_str)

            stream_body = "\n".join(page_cmds)
            stream_len = len(stream_body.encode('latin1', errors='ignore'))
            content_str = (
                f"{content_id} 0 obj\n"
                f"<< /Length {stream_len} >>\n"
                f"stream\n"
                f"{stream_body}\n"
                f"endstream\n"
                f"endobj"
            )
            objects.append(content_str)

        # Add Font Objects
        objects.append(f"{font_f1_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj")
        objects.append(f"{font_f2_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj")

        # Binary output generation with xref table
        header = "%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        body_bytes = bytearray(header.encode('latin1'))

        xref_offsets = [0]
        for obj in objects:
            xref_offsets.append(len(body_bytes))
            body_bytes.extend(obj.encode('latin1', errors='ignore'))
            body_bytes.extend(b"\n")

        startxref = len(body_bytes)
        num_objects = len(objects) + 1

        xref_str = f"xref\n0 {num_objects}\n0000000000 65535 f \n"
        for off in xref_offsets[1:]:
            xref_str += f"{off:010d} 00000 n \n"

        trailer_str = (
            f"trailer\n"
            f"<< /Size {num_objects} /Root 1 0 R >>\n"
            f"startxref\n"
            f"{startxref}\n"
            f"%%EOF\n"
        )

        body_bytes.extend(xref_str.encode('latin1'))
        body_bytes.extend(trailer_str.encode('latin1'))

        dirname = os.path.dirname(output_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(body_bytes)

        return output_path
