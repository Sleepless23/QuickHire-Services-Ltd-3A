import csv
from pathlib import Path

class CSVView:
    @staticmethod
    def export(rows: list[dict], path: str | Path):
        path = Path(path)
        if not rows:
            # Create a minimal CSV with a message for clarity
            with path.open('w', newline='', encoding='utf-8-sig') as f:
                f.write('message\nNo data\n')
            return
        headers = list(rows[0].keys())
        with path.open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

class PDFView:
    @staticmethod
    def export(rows: list[dict], path: str | Path, title: str = "Report"):
        # Minimal PDF generator (single-page text) to avoid external deps.
        # Renders each line separately with proper line breaks.
        path = Path(path)
        if not rows:
            lines = [title, "", "No data"]
        else:
            headers = list(rows[0].keys())
            col_widths = {h: max(len(h), max((len(str(r[h])) for r in rows), default=0)) for h in headers}
            header_line = "  ".join(h.ljust(col_widths[h]) for h in headers)
            sep_line = "  ".join("-" * col_widths[h] for h in headers)
            data_lines = ["  ".join(str(r[h]).ljust(col_widths[h]) for h in headers) for r in rows]
            lines = [title, "", header_line, sep_line, *data_lines]
        def pdf_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        # Build content stream: set font, move to start, set leading, print each line with Tj and T*
        leading = 14
        y_start = 780
        content_lines = ["BT", "/F1 10 Tf", f"1 0 0 1 50 {y_start} Tm", f"{leading} TL"]
        first = True
        for line in lines:
            txt = f"({pdf_escape(line)}) Tj"
            if first:
                content_lines.append(txt)
                first = False
            else:
                content_lines.append("T* " + txt)
        content_lines.append("ET")
        stream_text = "\n".join(content_lines)
        objects = []
        xref = []
        def add_object(obj_str: str):
            offset = sum(len(o) for o in objects)
            xref.append(offset)
            objects.append(obj_str)
            return len(objects)
        # 1. Font object
        add_object("1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        # 2. Contents
        stream = f"2 0 obj\n<< /Length {len(stream_text)} >>\nstream\n{stream_text}\nendstream\nendobj\n"
        add_object(stream)
        # 3. Page object
        page_obj = "3 0 obj\n<< /Type /Page /Parent 4 0 R /Resources << /Font << /F1 1 0 R >> >> /MediaBox [0 0 612 792] /Contents 2 0 R >>\nendobj\n"
        add_object(page_obj)
        # 4. Pages object
        pages_obj = "4 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        add_object(pages_obj)
        # 5. Catalog
        catalog_obj = "5 0 obj\n<< /Type /Catalog /Pages 4 0 R >>\nendobj\n"
        add_object(catalog_obj)
        header = "%PDF-1.4\n"
        body = "".join(objects)
        xref_start = len(header) + len(body)
        xref_table = ["xref\n0 6\n0000000000 65535 f \n"]
        for off in [0] + xref:
            xref_table.append(f"{off:010d} 00000 n \n")
        trailer = f"trailer\n<< /Size 6 /Root 5 0 R >>\nstartxref\n{xref_start}\n%%EOF"
        pdf_bytes = (header + body + ''.join(xref_table) + trailer).encode('latin1', errors='ignore')
        path.write_bytes(pdf_bytes)
