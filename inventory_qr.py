import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import parse_qs, urlparse

from PIL import Image

try:
    import pythoncom
    import win32print
except ImportError:
    pythoncom = None
    win32print = None

from utils import DATA_FILE, IP_AND_HOST, PRINTED_QR_FILE, gen_qrcode, load_json, save_json


ITEMS_FILE = DATA_FILE
FREE_STATUS = "空闲"
CUSTOM_PAPER_LABEL = "自定义尺寸"


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def normalize_item_id(raw_value):
    text = (raw_value or "").strip()
    if not text:
        return ""

    parsed = urlparse(text)
    if parsed.query:
        item_id = parse_qs(parsed.query).get("item_id", [""])[0]
        if item_id:
            return item_id.strip()

    match = re.search(r"item_id=([^&\s]+)", text)
    if match:
        return match.group(1).strip()

    return text


def qrcode_payload(item_id):
    return f"http://{IP_AND_HOST}/?item_id={item_id}&goto=page7"


def make_qr_pil_image(item_id):
    img = gen_qrcode(item_id)
    if hasattr(img, "get_image"):
        return img.get_image()
    return img


def decode_qr_image(image_file):
    image = Image.open(image_file).convert("RGB")

    try:
        import cv2
        import numpy as np

        rgb = np.array(image)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if data:
            return normalize_item_id(data), None
    except ImportError:
        pass
    except Exception as exc:
        return "", f"OpenCV 解码失败：{exc}"

    try:
        from pyzbar.pyzbar import decode

        decoded = decode(image)
        if decoded:
            raw = decoded[0].data.decode("utf-8", errors="replace")
            return normalize_item_id(raw), None
    except ImportError:
        pass
    except Exception as exc:
        return "", f"pyzbar 解码失败：{exc}"

    return "", "没有可用的二维码解码库，或图片中未识别到二维码。建议安装 opencv-python。"


def get_existing_ids():
    printed_qrs = load_json(PRINTED_QR_FILE)
    items = load_json(ITEMS_FILE)
    ids = {qr.get("item_id") for qr in printed_qrs if qr.get("item_id")}
    ids.update({item.get("item_id") for item in items if item.get("item_id")})
    return ids


def next_number_from_existing(prefix):
    max_number = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for item_id in get_existing_ids():
        match = pattern.match(str(item_id))
        if match:
            max_number = max(max_number, int(match.group(1)))
    return max_number + 1


def build_qr_records(prefix, start_number, count, digits):
    existing_ids = get_existing_ids()
    records = []
    current = int(start_number)
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    while len(records) < count:
        item_id = f"{prefix}{current:0{digits}d}"
        current += 1
        if item_id in existing_ids:
            continue
        records.append(
            {
                "item_id": item_id,
                "qr_payload": qrcode_payload(item_id),
                "created_at": now,
                "printed_times": 0,
                "last_printed_at": None,
            }
        )
        existing_ids.add(item_id)

    return records


def list_printers():
    if win32print is None:
        return [], ""
    try:
        pythoncom.CoInitialize()
        printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        default_printer = win32print.GetDefaultPrinter()
        return printers, default_printer
    except Exception:
        return [], ""


def list_printer_forms(printer_name):
    if win32print is None or not printer_name:
        return []
    try:
        handle = win32print.OpenPrinter(printer_name)
        try:
            forms = win32print.EnumForms(handle)
        finally:
            win32print.ClosePrinter(handle)
    except Exception:
        return []

    names = []
    for form in forms:
        if isinstance(form, dict):
            name = form.get("Name")
        elif isinstance(form, (tuple, list)) and form:
            name = form[0]
        else:
            name = None
        if name:
            names.append(str(name))
    return sorted(set(names))


def generate_temp_qr_pngs(records):
    temp_dir = tempfile.mkdtemp(prefix="inventory_qr_")
    printable = []
    for record in records:
        item_id = record["item_id"]
        img = make_qr_pil_image(item_id)
        png_path = os.path.join(temp_dir, f"{item_id}.png")
        img.save(png_path)
        printable.append({"item_id": item_id, "png_path": png_path})
    return temp_dir, printable


def print_qr_labels(records, printer_name, paper_name, label_width, label_height, copies):
    temp_dir, printable = generate_temp_qr_pngs(records)
    items_json_path = os.path.join(temp_dir, "print_items.json")
    script_path = os.path.join(temp_dir, "print_qr_labels.ps1")

    with open(items_json_path, "w", encoding="utf-8") as fp:
        json.dump(printable, fp, ensure_ascii=False, indent=2)

    use_saved_paper = bool(paper_name and paper_name != CUSTOM_PAPER_LABEL)
    ps_script = f"""
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$items = Get-Content -Raw -Encoding UTF8 -Path {ps_quote(items_json_path)} | ConvertFrom-Json
$printerName = {ps_quote(printer_name)}
$paperName = {ps_quote(paper_name)}
$useSavedPaper = ${str(use_saved_paper).lower()}
$labelWidth = [int]([double]{label_width} * 3.937)
$labelHeight = [int]([double]{label_height} * 3.937)
$copies = [int]{copies}
$success = 0
$failed = 0

foreach ($item in $items) {{
    for ($i = 0; $i -lt $copies; $i++) {{
        $img = $null
        $doc = $null
        try {{
            $img = [System.Drawing.Image]::FromFile($item.png_path)
            $doc = New-Object System.Drawing.Printing.PrintDocument
            $doc.PrinterSettings.PrinterName = $printerName
            if (-not $doc.PrinterSettings.IsValid) {{
                throw "Printer is not valid: $printerName"
            }}

            if ($useSavedPaper) {{
                $matched = $null
                foreach ($paper in $doc.PrinterSettings.PaperSizes) {{
                    if ($paper.PaperName -eq $paperName) {{
                        $matched = $paper
                        break
                    }}
                }}
                if ($matched -ne $null) {{
                    $doc.DefaultPageSettings.PaperSize = $matched
                }} else {{
                    Write-Host "Paper not found, use custom size: $paperName"
                    $custom = New-Object System.Drawing.Printing.PaperSize("InventoryLabel", $labelWidth, $labelHeight)
                    $doc.DefaultPageSettings.PaperSize = $custom
                }}
            }} else {{
                $custom = New-Object System.Drawing.Printing.PaperSize("InventoryLabel", $labelWidth, $labelHeight)
                $doc.DefaultPageSettings.PaperSize = $custom
            }}

            $doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
            $handler = {{
                param($sender, $event)
                $bounds = $event.PageBounds
                $font = New-Object System.Drawing.Font("Arial", 7)
                $text = [string]$item.item_id
                $textSize = $event.Graphics.MeasureString($text, $font)
                $usableWidth = [Math]::Max(1, $bounds.Width - 4)
                $usableHeight = [Math]::Max(1, $bounds.Height - $textSize.Height - 8)
                $qrSide = [Math]::Min($usableWidth, $usableHeight)
                $x = ($bounds.Width - $qrSide) / 2
                $y = [Math]::Max(0, ($bounds.Height - $qrSide - $textSize.Height - 4) / 2)
                $event.Graphics.DrawImage($img, $x, $y, $qrSide, $qrSide)
                $textX = ($bounds.Width - $textSize.Width) / 2
                $textY = $y + $qrSide + 2
                $event.Graphics.DrawString($text, $font, [System.Drawing.Brushes]::Black, $textX, $textY)
                $event.HasMorePages = $false
            }}.GetNewClosure()

            $doc.add_PrintPage($handler)
            $doc.Print()
            $doc.remove_PrintPage($handler)
            $success++
            Write-Host "PRINT_OK $($item.item_id)"
        }} catch {{
            $failed++
            Write-Host "PRINT_FAIL $($item.item_id) - $($_.Exception.Message)"
        }} finally {{
            if ($doc -ne $null) {{ $doc.Dispose() }}
            if ($img -ne $null) {{ $img.Dispose() }}
        }}
    }}
}}

Write-Host "PRINT_DONE success=$success failed=$failed"
if ($failed -gt 0) {{ exit 1 }}
"""

    with open(script_path, "w", encoding="utf-8-sig") as fp:
        fp.write(ps_script)

    try:
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def mark_printed(records, copies):
    printed_qrs = load_json(PRINTED_QR_FILE)
    record_map = {record["item_id"]: record for record in printed_qrs}
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for record in records:
        target = record_map.get(record["item_id"])
        if target:
            target["printed_times"] = int(target.get("printed_times") or 0) + copies
            target["last_printed_at"] = now
    save_json(PRINTED_QR_FILE, printed_qrs)


def register_item(item_id, item_name, remark):
    items = load_json(ITEMS_FILE)
    items.append(
        {
            "item_id": item_id,
            "item_name": item_name,
            "remark": remark,
            "status": FREE_STATUS,
            "username": None,
            "name": None,
            "user": None,
            "user_class": None,
            "user_phone": None,
            "usage": None,
            "take_time": None,
            "due_date": None,
        }
    )
    save_json(ITEMS_FILE, items)


def build_batch_item_name(prefix, index, digits):
    return f"{prefix}_{index:0{digits}d}"


def register_printed_records(records, name_prefix, start_number=0, digits=2, remark=""):
    items = load_json(ITEMS_FILE)
    registered_ids = {item.get("item_id") for item in items}
    created = []
    skipped = []

    for offset, record in enumerate(records):
        item_id = record.get("item_id")
        if not item_id or item_id in registered_ids:
            skipped.append(item_id)
            continue

        item_name = build_batch_item_name(name_prefix, int(start_number) + offset, int(digits))
        items.append(
            {
                "item_id": item_id,
                "item_name": item_name,
                "remark": remark,
                "status": FREE_STATUS,
                "username": None,
                "name": None,
                "user": None,
                "user_class": None,
                "user_phone": None,
                "usage": None,
                "take_time": None,
                "due_date": None,
            }
        )
        registered_ids.add(item_id)
        created.append({"item_id": item_id, "item_name": item_name})

    if created:
        save_json(ITEMS_FILE, items)
    return created, skipped
