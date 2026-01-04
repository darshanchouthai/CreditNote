from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import mysql.connector
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER, TA_LEFT

app = Flask(__name__)

# --- Database Configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Darshan@2003', 
    'database': 'credit_notes_db'
}

# --- Party Data Mapping ---
PARTY_DATA = {
    "Aakshya Infra Projects": {
        "address": "Kempegouda International Airport, Bengaluru",
        "wos": ["6000000055"]
    },
    "Ashok Buildcon – Davanagere": {
        "address": "Davanagere",
        "wos": ["18020076-10-10", "18015821-10-10"]
    },
    "Ashok Buildcon – Tumkur Sec 1": {
        "address": "Tumkur Sect 1",
        "wos": ["18019662-10-10", "18020038-10-10"]
    },
    "Ashok Buildcon – Tumkur Sec 2": {
        "address": "Tumkur Sec 2 ",
        "wos": ["18020039-10-10"]
    }
}

# --- Database Helper Functions ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                credit_note_no VARCHAR(255),
                date VARCHAR(50),
                party_name VARCHAR(255),
                party_address TEXT,
                wo_no VARCHAR(255),
                particulars TEXT,
                amount DECIMAL(10, 2),
                gst_rate INT DEFAULT 18,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()

init_db()

# --- PDF Generation Logic (Refined for Perfect Fit) ---
def create_pdf(note):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # -- Tighter Margins to maximize printable width --
    left_margin = 8 * mm
    right_margin = width - 8 * mm
    top_margin = height - 10 * mm
    bottom_margin = 10 * mm
    content_width = right_margin - left_margin
    
    # Calculations
    amount = float(note['amount'])
    gst_val = amount * 0.18
    net_total = amount + gst_val

    # --- Draw Outer Border ---
    # Main Box Height: roughly from top to footer
    c.setLineWidth(1)
    # We will draw specific boxes rather than one giant rect to ensure clean lines
    
    # === HEADER ===
    y = top_margin - 5*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin + 2*mm, y, "GURUKRUPA EARTHMOVERS")
    
    y -= 5*mm
    c.setFont("Helvetica", 9)
    c.drawString(left_margin + 2*mm, y, "ON HIRE: Construction Equipement") 
    
    y -= 5*mm
    c.setFont("Helvetica", 8)
    address_line1 = "735 A PLOT NO 86, ATHANI ROAD BHIRAV NAGAR VIJAYAPUR -586101,"
    c.drawString(left_margin + 2*mm, y, address_line1)
    y -= 4*mm
    c.drawString(left_margin + 2*mm, y, "Taluk: Dist: Vijayapura")
    y -= 4*mm
    c.drawString(left_margin + 2*mm, y, "Mobile: 9448025191, Email: gcmukund@gmail.com")
    
    # Header Box
    header_bottom = y - 2*mm
    c.rect(left_margin, header_bottom, content_width, top_margin - header_bottom)
    
    # === CREDIT NOTE STRIP ===
    strip_height = 6*mm
    strip_y = header_bottom - strip_height
    c.rect(left_margin, strip_y, content_width, strip_height)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width/2, strip_y + 1.5*mm, "Credit Note")
    
    # === INFO BLOCK ===
    info_height = 45*mm
    info_y = strip_y - info_height
    c.rect(left_margin, info_y, content_width, info_height)
    
    # Left Side Info
    curr_y = strip_y - 5*mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left_margin + 2*mm, curr_y, "Gurukrupa Earthmovers")
    curr_y -= 4*mm
    c.drawString(left_margin + 2*mm, curr_y, "GST No: 29AHSPC4247N1ZP")
    
    # Right Side Info (Project)
    c.drawString(left_margin + 110*mm, strip_y - 5*mm, f"Projects : {note['party_name']}") # Fixed text
    
    # Right Side Info (Dates/Nos)
    right_col_x = right_margin - 65*mm
    curr_y = strip_y - 12*mm
    c.drawString(right_col_x, curr_y, f"Credit note No: {note['credit_note_no']}")
    curr_y -= 4*mm
    c.drawString(right_col_x, curr_y, f"WO No: {note['wo_no']}")
    curr_y -= 4*mm
    c.drawString(right_col_x, curr_y, f"Date: {note['date']}")
    
    # Party Info (Bottom Left of Info Block)
    curr_y = info_y + 15*mm
    c.drawString(left_margin + 2*mm, curr_y, f"Party Name: {note['party_name']}")
    curr_y -= 4*mm
    # Handle address wrapping simply
    addr = note['party_address'][:60] # simple trim for safety, better wrapping below
    c.drawString(left_margin + 2*mm, curr_y, addr)
    curr_y -= 4*mm
    c.drawString(left_margin + 2*mm, curr_y, "GST No: 29AABCA9292J1Z6")

    # === DATA TABLE ===
    # Column Setup - Adjusted for better fit
    # Total Width available = content_width (approx 194mm)
    # SL=8, Period=18, HSN=18, Partic=80, Qty=12, Unit=10, Rate=22, Amt=26
    
    col_widths = [8*mm, 18*mm, 18*mm, 80*mm, 12*mm, 10*mm, 22*mm, 26*mm]
    
    # Verify width matches page
    # current_total = sum(col_widths) # Should be close to content_width
    
    # X coordinates for vertical lines
    x_positions = [left_margin]
    current_x = left_margin
    for w in col_widths:
        current_x += w
        x_positions.append(current_x)
    
    # Ensure last line hits exact margin
    x_positions[-1] = right_margin
    
    table_top = info_y
    header_height = 6*mm
    row_height = 6*mm # Smaller row height as requested
    num_rows = 15 # Fixed number of rows to fill page
    
    table_bottom = table_top - header_height - (row_height * num_rows)
    
    # Draw Grid Outline
    c.rect(left_margin, table_bottom, content_width, header_height + (row_height * num_rows))
    
    # Draw Horizontal Header Line
    c.line(left_margin, table_top - header_height, right_margin, table_top - header_height)
    
    # Draw Vertical Lines
    for x in x_positions:
        c.line(x, table_top, x, table_bottom)
        
    # Draw Headers
    headers = ["SL No", "Period", "HSN Code", "Perticulers", "Bill Qty", "Unit", "Rate", "Amount"]
    c.setFont("Helvetica-Bold", 8) # Smaller font
    text_y = table_top - 4.5*mm
    
    for i, h in enumerate(headers):
        # Center text in column
        col_center = x_positions[i] + (col_widths[i] / 2)
        c.drawCentredString(col_center, text_y, h)
        
    # Draw Data Row (First Row)
    data_y_start = table_top - header_height
    c.setFont("Helvetica-Bold", 8)
    
    # Helper to center text in a specific cell
    def draw_cell_text(col_index, text, y_pos):
        center_x = x_positions[col_index] + (col_widths[col_index] / 2)
        c.drawCentredString(center_x, y_pos - 4.5*mm, str(text))

    # Row 1 Data
    draw_cell_text(0, "1", data_y_start)
    draw_cell_text(4, "1", data_y_start) # Qty
    draw_cell_text(5, "1", data_y_start) # Unit
    draw_cell_text(6, f"{amount:.2f}", data_y_start)
    draw_cell_text(7, f"{amount:.2f}", data_y_start)
    
    # --- Particulars Text Wrapping ---
    # This prevents the text from crossing into the next column
    particulars_text = note['particulars']
    style = getSampleStyleSheet()["Normal"]
    style.fontName = "Helvetica-Bold"
    style.fontSize = 8
    style.alignment = TA_CENTER
    
    # Create a Paragraph
    p = Paragraph(particulars_text, style)
    # Wrap it to fit in the column width (minus padding)
    avail_width = col_widths[3] - 4*mm 
    w, h = p.wrap(avail_width, row_height)
    # Draw it
    p.drawOn(c, x_positions[3] + 2*mm, data_y_start - 4.5*mm)

    # Draw Horizontal Grid Lines for empty rows
    current_y = data_y_start
    for r in range(num_rows):
        current_y -= row_height
        c.line(left_margin, current_y, right_margin, current_y)

    # === TOTALS SECTION ===
    # This sits below the main table grid
    # Columns 0-6 (SL to Rate) are merged visually, but we need lines for the last columns
    
    # We need 3 rows: Net Total, GST, Net Amount
    totals_row_height = 6*mm
    totals_start_y = table_bottom
    
    # Draw the box for totals
    c.rect(left_margin, totals_start_y - (totals_row_height*3), content_width, totals_row_height*3)
    
    # Vertical lines extension for the last 2 columns (Rate/Amount divider)
    # Rate col is index 6, Amount is index 7
    # We need lines at x_positions[6] and x_positions[7] and x_positions[8]
    
    line_x_start = x_positions[6] # Start of Rate Column
    line_x_mid = x_positions[7]   # Start of Amount Column
    
    # Draw vertical lines down through the totals section
    c.line(line_x_start, totals_start_y, line_x_start, totals_start_y - (totals_row_height*3))
    c.line(line_x_mid, totals_start_y, line_x_mid, totals_start_y - (totals_row_height*3))
    
    # Draw Horizontal lines for totals
    c.line(line_x_start, totals_start_y - totals_row_height, right_margin, totals_start_y - totals_row_height)
    c.line(line_x_start, totals_start_y - (totals_row_height*2), right_margin, totals_start_y - (totals_row_height*2))

    # Text for Totals
    c.setFont("Helvetica-Bold", 8)
    
    # Net Total
    y_pos = totals_start_y - 4.5*mm
    c.drawString(line_x_start + 2*mm, y_pos, "Net Total")
    c.drawRightString(right_margin - 2*mm, y_pos, f"{amount:.2f}")
    
    # GST
    y_pos -= totals_row_height
    c.drawString(line_x_start + 2*mm, y_pos, "GST@ 18%")
    c.drawRightString(right_margin - 2*mm, y_pos, f"{gst_val:.2f}")
    
    # Final Amount
    y_pos -= totals_row_height
    c.drawString(line_x_start + 2*mm, y_pos, "Net Amount")
    c.drawRightString(right_margin - 2*mm, y_pos, f"{net_total:.2f}")

    # === FOOTER / SIGNATURE ===
    footer_box_y = totals_start_y - (totals_row_height*3)
    sig_box_width = 70*mm
    sig_box_height = 25*mm
    
    # Signature Box (Bottom Right)
    c.rect(right_margin - sig_box_width, footer_box_y - sig_box_height, sig_box_width, sig_box_height)
    
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.darkblue)

    
    
    # Artificial Signature
   

    c.save()
    buffer.seek(0)
    return buffer

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', parties=PARTY_DATA)

@app.route('/save', methods=['POST'])
def save_note():
    data = request.form
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if 'note_id' in data and data['note_id']:
            sql = '''UPDATE notes SET 
                credit_note_no=%s, date=%s, party_name=%s, party_address=%s, 
                wo_no=%s, particulars=%s, amount=%s
                WHERE id=%s'''
            values = (data['cn_no'], data['date'], data['party_name'], data['party_address'], 
                      data['wo_no'], data['particulars'], data['amount'], data['note_id'])
            cursor.execute(sql, values)
        else:
            sql = '''INSERT INTO notes 
                (credit_note_no, date, party_name, party_address, wo_no, particulars, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)'''
            values = (data['cn_no'], data['date'], data['party_name'], data['party_address'], 
                      data['wo_no'], data['particulars'], data['amount'])
            cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('history'))

@app.route('/history')
def history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notes ORDER BY timestamp DESC")
    notes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('history.html', notes=notes)

@app.route('/edit/<int:id>')
def edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('index.html', parties=PARTY_DATA, note=note)

@app.route('/download_pdf/<int:id>')
def download_pdf(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cursor.fetchone()
    cursor.close()
    
    if not note:
        return "Note not found", 404
        
    pdf_buffer = create_pdf(note)
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=Credit_Note_{note["credit_note_no"]}.pdf'
    return response

@app.route('/get_party_details/<party_name>')
def get_party(party_name):
    return jsonify(PARTY_DATA.get(party_name, {}))

@app.route('/delete/<int:id>')
def delete_note(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM notes WHERE id=%s", (id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error deleting note: {err}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True)