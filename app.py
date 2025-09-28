

import pandas as pd
# ...existing code...

import zipfile, tempfile, os
import threading
import time
from flask import Flask, request, render_template, send_file, jsonify, flash, redirect, url_for, session
import csv, io
from collections import OrderedDict


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB
import tempfile
import os
app.secret_key = "replace-with-a-random-secret-for-production"

# --- Recurring job to clean up temp CSV files ---
def cleanup_temp_csvs():
    temp_dir = '.'  # or use a dedicated temp folder if needed
    while True:
        now = time.time()
        for fname in os.listdir(temp_dir):
            if fname.endswith('.csv') and fname.startswith('tmp'):
                fpath = os.path.join(temp_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if now - mtime > 3600:  # 1 hour
                        os.remove(fpath)
                except Exception:
                    pass
        time.sleep(1800)  # Run every 30 minutes

# Start cleanup job in background
cleanup_thread = threading.Thread(target=cleanup_temp_csvs, daemon=True)
cleanup_thread.start()

# Jinja2 filter for Excel-style column letters
def excel_col(idx):
    letters = ''
    while idx >= 0:
        letters = chr(idx % 26 + ord('A')) + letters
        idx = idx // 26 - 1

    return letters
app.jinja_env.filters['excel_col'] = excel_col


# --- Modify CSV feature ---
@app.route("/modify_csv", methods=["GET", "POST"])
def modify_csv():
    columns = None
    modfile_path = None
    if request.method == "POST":
        file = request.files.get("modfile")
        if file:
            temp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', dir='.')
            temp.write(file.read())
            temp.close()
            modfile_path = temp.name
            df = pd.read_csv(modfile_path)
            columns = []
            def python_to_human_fmt(fmt):
                if not fmt:
                    return None
                # Map python strftime to user-friendly format
                return (fmt.replace('%Y', 'yyyy')
                           .replace('%m', 'MM')
                           .replace('%d', 'dd')
                           .replace('%H', 'HH')
                           .replace('%M', 'mm')
                           .replace('%S', 'ss'))

            for col in df.columns:
                dtype = df[col].dtype
                col_format = None
                # Simple type detection
                if pd.api.types.is_integer_dtype(dtype):
                    coltype = "Integer"
                elif pd.api.types.is_float_dtype(dtype):
                    coltype = "Float"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    coltype = "DateTime"
                    sample = df[col].dropna().astype(str).iloc[0] if not df[col].dropna().empty else None
                    if sample:
                        import re
                        if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", sample):
                            col_format = "%Y-%m-%d %H:%M:%S"
                        elif re.match(r"\d{4}-\d{2}-\d{2}", sample):
                            col_format = "%Y-%m-%d"
                        elif re.match(r"\d{2}/\d{2}/\d{4}", sample):
                            col_format = "%m/%d/%Y"
                        else:
                            col_format = None
                    # Use format in pd.to_datetime if available
                    try:
                        if col_format:
                            pd.to_datetime(df[col], format=col_format, errors='raise')
                        else:
                            pd.to_datetime(df[col], errors='raise')
                    except:
                        pass
                elif pd.api.types.is_bool_dtype(dtype):
                    coltype = "Boolean"
                else:
                    try:
                        # Try to parse as date
                        sample = df[col].dropna().astype(str).iloc[0] if not df[col].dropna().empty else None
                        if sample:
                            import re
                            if re.match(r"\d{4}-\d{2}-\d{2}", sample):
                                col_format = "%Y-%m-%d"
                            elif re.match(r"\d{2}/\d{2}/\d{4}", sample):
                                col_format = "%m/%d/%Y"
                            else:
                                col_format = None
                        if col_format:
                            pd.to_datetime(df[col], format=col_format, errors='raise')
                        else:
                            pd.to_datetime(df[col], errors='raise')
                        coltype = "Date"
                    except:
                        coltype = "Text"
                columns.append({"name": col, "type": coltype, "format": python_to_human_fmt(col_format) if col_format else "(unknown)"})
            return render_template("modify_csv.html", columns=columns, modfile_path=modfile_path)
        # Second POST: apply modifications (not implemented yet)
        modfile_path = request.form.get("modfile_path")
        if modfile_path and os.path.exists(modfile_path):
            df = pd.read_csv(modfile_path)
            # Apply modifications and type changes
            for col in df.columns:
                action = request.form.get(f"action_{col}")
                new_type = request.form.get(f"new_type_{col}")
                if action == "delete":
                    df = df.drop(columns=[col])
                    continue
                if action == "modify":
                    mod_type = request.form.get(f"mod_type_{col}")
                    new_value = request.form.get(f"new_value_{col}")
                    concat_cols = request.form.get(f"concat_cols_{col}")
                    datefmt_modify = request.form.get(f"datefmt_modify_{col}")
                    if mod_type == "replace" and new_value:
                        df[col] = new_value
                    elif mod_type == "add_value" and new_value:
                        # Add a new value as-is to the output CSV for this column
                        df[col] = [new_value] * len(df)
                    elif mod_type == "concat" and concat_cols:
                        # Enhanced: allow custom separators between columns using quoted strings
                        import re
                        # Robust parser for quoted separators and column names
                        # Example: A":"B, " "A, A"-NA"
                        tokens = []
                        pattern = r'"([^"]*)"|([A-Za-z0-9_]+)'
                        for match in re.finditer(pattern, concat_cols):
                            sep, colname = match.groups()
                            if sep is not None:
                                tokens.append((sep, ''))
                            elif colname is not None:
                                tokens.append(('', colname))
                        concat_expr = []
                        columns_found = [colname for sep, colname in tokens if colname and colname in df.columns]
                        # Only concatenate if at least one column is present in the pattern
                        # Support column references by index (A, B, C, ...) as well as by name
                        col_letters = {chr(ord('A') + idx): name for idx, name in enumerate(df.columns)}
                        def resolve_col(colname):
                            if colname in df.columns:
                                return colname
                            elif colname in col_letters:
                                return col_letters[colname]
                            else:
                                return None

                        columns_present = any(colname and resolve_col(colname) for sep, colname in tokens)
                        separators_present = any(sep for sep, colname in tokens)
                        if columns_present:
                            nrows = len(df)
                            output = []
                            for i in range(nrows):
                                row_parts = []
                                for sep, colname in tokens:
                                    if sep:
                                        row_parts.append(sep)
                                    elif colname:
                                        resolved = resolve_col(colname)
                                        if resolved:
                                            val = df[resolved].iloc[i]
                                            if pd.isnull(val) or str(val).lower() in ["nan", "nat"]:
                                                row_parts.append("")
                                            else:
                                                row_parts.append(str(val))
                                output.append(''.join(row_parts))
                            df[col] = output
                        elif separators_present:
                            # Only separator, output blank
                            df[col] = [''] * len(df)
                        else:
                            # No columns or separators, output blank
                            df[col] = [''] * len(df)
                    elif mod_type == "datefmt":
                        try:
                            if datefmt_modify:
                                import re
                                from dateutil import parser
                                formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"]
                                def to_strftime(fmt):
                                    return fmt.replace('dd', '%d').replace('MM', '%m').replace('yyyy', '%Y').replace('yy', '%y').replace('HH', '%H').replace('mm', '%M').replace('ss', '%S')
                                strftime_format = to_strftime(datefmt_modify)
                                def detect_format(val):
                                    val = str(val).strip()
                                    for fmt in formats:
                                        try:
                                            pd.to_datetime(val, format=fmt, errors='raise')
                                            return fmt
                                        except Exception:
                                            continue
                                    return None
                                def robust_parse(val):
                                    val_orig = str(val)
                                    val = val_orig.strip()
                                    # Remove debug logging for production
                                    if not val or val.lower() in ["nan", "nat"]:
                                        return ''
                                    if val == 'NaT':
                                        return ''
                                    fmt = detect_format(val)
                                    try:
                                        if fmt:
                                            parsed = pd.to_datetime(val, format=fmt, errors='raise')
                                        else:
                                            parsed = parser.parse(val)
                                        if pd.isnull(parsed) or str(parsed) == 'NaT' or str(parsed) == 'nan':
                                            return ''
                                        try:
                                            result = parsed.strftime(strftime_format)
                                        except Exception:
                                            return ''
                                        return str(result)
                                    except Exception:
                                        return ''
                                df[col] = df[col].apply(robust_parse)
                                # ...existing code...
                            else:
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                        except Exception:
                            pass
                # Skip type conversion if 'datefmt' modification was applied
                if action == "modify" and mod_type == "datefmt":
                    pass  # Already handled above, do not overwrite
                elif new_type and new_type != str(df[col].dtype):
                    try:
                        datefmt = request.form.get(f"datefmt_{col}")
                        if new_type == "Integer":
                            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                        elif new_type == "Float":
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                        elif new_type == "Text":
                            df[col] = df[col].astype(str)
                        elif new_type == "Date":
                            df[col] = pd.to_datetime(df[col], errors="coerce")
                            if datefmt:
                                df[col] = df[col].dt.strftime(datefmt)
                            else:
                                df[col] = df[col].dt.date.astype(str)
                        elif new_type == "DateTime":
                            df[col] = pd.to_datetime(df[col], errors="coerce")
                            if datefmt:
                                df[col] = df[col].dt.strftime(datefmt)
                        elif new_type == "Boolean":
                            df[col] = df[col].astype(bool)
                    except Exception:
                        pass
            # Replace all NaN, NaT, and 'nan'/'NaT' strings with blanks before saving
            df = df.replace({pd.NA: '', pd.NaT: '', 'NaN': '', 'NaT': '', 'nan': '', 'nat': ''})
            bio = io.StringIO(newline='')
            df.to_csv(bio, index=False, quoting=1, lineterminator='\n')
            bio.seek(0)
            return send_file(
                io.BytesIO(bio.getvalue().encode("utf-8")),
                as_attachment=True,
                download_name="modified.csv",
                mimetype="text/csv"
            )
    return render_template("modify_csv.html")

# --- Check Duplicates feature routes (must be after app = Flask(__name__)) ---
@app.route("/check_duplicates", methods=["GET", "POST"])
def check_duplicates():
    if request.method == "GET":
        return render_template("check_duplicates.html")

    file = request.files.get("dupfile")
    column = request.form.get("dup_column", "").strip()
    # If column is not provided but temp file is present, try to get it from hidden input
    if not column:
        column = request.form.get("last_column", "").strip()

    import base64
    # Store uploaded file in a temp folder and use its path for subsequent actions
    temp_file_path = request.form.get('dupfile_path')
    loaded_filename = None
    if file:
        # Save to temp file
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', dir='.')
        temp.write(file.read())
        temp.close()
        temp_file_path = temp.name
        with open(temp_file_path, 'rb') as f:
            file_bytes = f.read()
        loaded_filename = file.filename
    elif temp_file_path and os.path.exists(temp_file_path):
        with open(temp_file_path, 'rb') as f:
            file_bytes = f.read()
        loaded_filename = os.path.basename(temp_file_path)
    elif temp_file_path and os.path.exists(temp_file_path):
        with open(temp_file_path, 'rb') as f:
            file_bytes = f.read()
    else:
        flash("Please upload a CSV file and select a column.", "error")
        return render_template("check_duplicates.html")

    # Read CSV
    h, rows = read_csv_stream(io.BytesIO(file_bytes))
    if column not in h:
        flash(f"Column '{column}' not found in file.", "error")
        return render_template("check_duplicates.html")

    # Find duplicates: group by column, keep only rows where value appears more than once
    from collections import Counter
    value_counts = Counter(r.get(column, "") for r in rows)
    dups = [r for r in rows if value_counts[r.get(column, "")] > 1]
    unique_dup_values = [val for val, count in value_counts.items() if count > 1 and val != ""]

    # If user clicked 'Retain 1 of Each Duplicate & Download CSV'
    if request.form.get("retain_one") == "1":
        # Use temp file if it exists, else ask to upload
        if not (temp_file_path and os.path.exists(temp_file_path)):
            flash("No file found for deduplication. Please upload a CSV file first.", "error")
            return render_template("check_duplicates.html")
        seen = set()
        output_rows = []
        for r in rows:
            val = r.get(column, "")
            if value_counts[val] > 1:
                if val not in seen:
                    output_rows.append(r)
                    seen.add(val)
            else:
                output_rows.append(r)
        # Generate CSV and send as download
        bio = rows_to_csv_bytes(h, output_rows)
        bio.seek(0)
        return send_file(
            bio,
            as_attachment=True,
            download_name=f"deduplicated_{column}.csv",
            mimetype="text/csv"
        )

    # For pagination, just render all and let frontend paginate (like result.html)
    return render_template(
        "check_duplicates.html",
        headers=h,
        duplicates=dups,
        unique_dup_count=len(unique_dup_values),
        file_location_message=None,
        dupfile_path=temp_file_path,
        last_column=column,
        loaded_filename=loaded_filename
    )

# AJAX endpoint to get headers for Check Duplicates
@app.route("/dup_headers", methods=["POST"])
def dup_headers():
    file = request.files.get("dupfile")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    h, _ = read_csv_stream(file.stream)
    return jsonify({"headers": h})

# Route for Split CSV page (must be after app = Flask(__name__))
@app.route("/split_csv", methods=["GET", "POST"])
def split_csv():
    if request.method == "GET":
        return render_template("split_csv.html")

    file = request.files.get("csvfile")
    split_count = request.form.get("split_count", type=int)
    if not file or not split_count or split_count < 1:
        flash("Please upload a CSV file and enter a valid split count.", "error")
        return render_template("split_csv.html")

    # Read CSV header and rows as raw strings to avoid formatting
    stream = io.TextIOWrapper(file.stream, encoding="utf-8-sig", newline='')
    lines = list(stream)
    if not lines:
        flash("CSV file is empty.", "error")
        return render_template("split_csv.html")
    header = lines[0]
    data_lines = lines[1:]

    # Split data_lines into chunks
    chunks = [data_lines[i:i+split_count] for i in range(0, len(data_lines), split_count)]

    # Create zip in memory and send after closing file (Windows fix)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "split_csvs.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, chunk in enumerate(chunks, 1):
                fname = f"split_{idx}.csv"
                content = header + ''.join(chunk)
                zf.writestr(fname, content)
        # Read zip to memory after closing
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()
        mem_zip = io.BytesIO(zip_bytes)
        mem_zip.seek(0)
        return send_file(mem_zip, as_attachment=True, download_name="split_csvs.zip", mimetype="application/zip")

# For storing result in session (not for large files, but fine for small CSVs)
import base64

def read_csv_stream(stream):
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline='')
    reader = csv.DictReader(text)
    rows = [OrderedDict((k, r.get(k, "")) for k in reader.fieldnames) for r in reader]
    return reader.fieldnames or [], rows

def rows_to_csv_bytes(fieldnames, rows):
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return io.BytesIO(buf.getvalue().encode("utf-8"))


# Dedicated welcome page
@app.route("/")
def welcome():
    return render_template("welcome.html")

# Compare CSV page moved to /compare_csv
@app.route("/compare_csv", methods=["GET"])
def compare_csv():
    return render_template("index.html")


# Endpoint for File 1 headers (existing)
@app.route("/headers", methods=["POST"])
def headers():
    file1 = request.files.get("file1")
    if not file1:
        return jsonify({"error": "No file uploaded"}), 400
    h1, _ = read_csv_stream(file1.stream)
    return jsonify({"headers": h1})

# Endpoint for File 2 headers (new)
@app.route("/headers2", methods=["POST"])
def headers2():
    file2 = request.files.get("file2")
    if not file2:
        return jsonify({"error": "No file uploaded"}), 400
    h2, _ = read_csv_stream(file2.stream)
    return jsonify({"headers": h2})

@app.route("/compare", methods=["POST"])
def compare():
    file1 = request.files.get("file1")
    file2 = request.files.get("file2")

    column1 = request.form.get("column", "").strip()  # File 1 column
    column2 = request.form.get("column2", "").strip()  # File 2 column
    mode = request.form.get("mode")

    if not file1 or not file2:
        flash("Please upload both files.", "error")
        return redirect(url_for("index"))

    # Read CSVs
    h1, rows1 = read_csv_stream(file1.stream)
    h2, rows2 = read_csv_stream(file2.stream)


    if column1 not in h1:
        flash(f"Column '{column1}' not found in File 1.", "error")
        return redirect(url_for("index"))
    if column2 not in h2:
        flash(f"Column '{column2}' not found in File 2.", "error")
        return redirect(url_for("index"))

    values2 = {r.get(column2, "") for r in rows2 if column2 in h2}

    if mode == "duplicates":
        out_rows = [r for r in rows1 if r.get(column1, "") in values2]
        out_name = f"duplicates_by_{column1}_in_file1_vs_{column2}_in_file2.csv"
    else:
        out_rows = [r for r in rows1 if r.get(column1, "") not in values2]
        out_name = f"in_file1_not_in_file2_by_{column1}_vs_{column2}.csv"

    # Store result in session for download (base64-encoded)
    bio = rows_to_csv_bytes(h1, out_rows)
    bio.seek(0)
    session['csv_result'] = base64.b64encode(bio.read()).decode('utf-8')
    session['csv_result_name'] = out_name

    return render_template(
        "result.html",
        headers=h1,
        rows=out_rows,
        mode=mode,
        column=f"{column1} (File 1) vs {column2} (File 2)",
    )


# Route to download the last result
@app.route("/download_csv")
def download_csv():
    data = session.get('csv_result')
    name = session.get('csv_result_name', 'result.csv')
    if not data:
        flash("No result to download.", "error")
        return redirect(url_for("index"))
    bio = io.BytesIO(base64.b64decode(data))
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name=name, mimetype="text/csv")


# --- Excel to CSV Converter ---
import pandas as pd

@app.route("/excel_to_csv", methods=["GET", "POST"])
def excel_to_csv():
    if request.method == "GET":
        return render_template("excel_to_csv.html")
    file = request.files.get("excelfile")
    if not file or not file.filename.lower().endswith((".xls", ".xlsx")):
        flash("Please upload a valid Excel file (.xls or .xlsx).", "error")
        return render_template("excel_to_csv.html")
    try:
        df = pd.read_excel(file, dtype=str, keep_default_na=False, engine=None)
        base = os.path.splitext(file.filename)[0]
        out_name = f"{base}.csv"
        bio = io.StringIO()
        df.to_csv(bio, index=False, encoding="utf-8", lineterminator='\n')
        bio.seek(0)
        return send_file(
            io.BytesIO(bio.getvalue().encode("utf-8")),
            as_attachment=True,
            download_name=out_name,
            mimetype="text/csv"
        )
    except Exception as e:
        flash(f"Error converting file: {e}", "error")
        return render_template("excel_to_csv.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
