"""
Convert PHASE_1_DEEP_EXPLANATION.md to PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Read markdown
with open('PHASE_1_DEEP_EXPLANATION.md', 'r') as f:
    content = f.read()

# Create PDF
doc = SimpleDocTemplate(
    'PHASE_1_DEEP_EXPLANATION.pdf',
    pagesize=A4,
    leftMargin=1.5*cm, rightMargin=1.5*cm,
    topMargin=1.5*cm, bottomMargin=1.5*cm
)

# Colors
DARK = HexColor('#0f172a')
EMERALD = HexColor('#059669')
BLUE = HexColor('#2563eb')
RED = HexColor('#dc2626')
GRAY_TEXT = HexColor('#64748b')
CODE_BG = HexColor('#1e293b')
CODE_FG = HexColor('#e2e8f0')

# Styles
title_style = ParagraphStyle(
    'title', fontSize=20, textColor=DARK,
    fontName='Helvetica-Bold', spaceAfter=12, alignment=TA_CENTER
)
h1_style = ParagraphStyle(
    'h1', fontSize=14, textColor=DARK,
    fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=8
)
h2_style = ParagraphStyle(
    'h2', fontSize=12, textColor=EMERALD,
    fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=6
)
h3_style = ParagraphStyle(
    'h3', fontSize=11, textColor=DARK,
    fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=5
)
body_style = ParagraphStyle(
    'body', fontSize=10, textColor=DARK,
    fontName='Helvetica', leading=15, spaceAfter=6
)
code_style = ParagraphStyle(
    'code', fontSize=8, textColor=CODE_FG,
    fontName='Courier', backColor=CODE_BG,
    leftIndent=8, rightIndent=8, spaceAfter=6, leading=11
)
table_style = ParagraphStyle(
    'table', fontSize=9, textColor=DARK,
    fontName='Helvetica', leading=12
)

elems = []

# Parse markdown
lines = content.split('\n')
i = 0

while i < len(lines):
    line = lines[i]
    
    # Title
    if line.startswith('# '):
        elems.append(Paragraph(line[2:], title_style))
        elems.append(Spacer(1, 8))
    
    # Heading 1
    elif line.startswith('## '):
        elems.append(Paragraph(line[3:], h1_style))
    
    # Heading 2
    elif line.startswith('### '):
        elems.append(Paragraph(line[4:], h2_style))
    
    # Heading 3
    elif line.startswith('#### '):
        elems.append(Paragraph(line[5:], h3_style))
    
    # Code block
    elif line.startswith('```'):
        code_lines = []
        i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            code_lines.append(lines[i])
            i += 1
        
        code_text = '\n'.join(code_lines)
        code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Split into smaller chunks if too long
        if len(code_text) > 500:
            chunks = [code_text[j:j+500] for j in range(0, len(code_text), 500)]
            for chunk in chunks:
                elems.append(Paragraph(chunk, code_style))
        else:
            elems.append(Paragraph(code_text, code_style))
        elems.append(Spacer(1, 6))
    
    # Table
    elif line.startswith('| '):
        table_rows = []
        while i < len(lines) and lines[i].startswith('| '):
            row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
            table_rows.append(row)
            i += 1
        
        if table_rows:
            # Skip header separator
            if len(table_rows) > 1 and all(c.startswith('-') for c in table_rows[1]):
                table_rows = [table_rows[0]] + table_rows[2:]
            
            # Create table
            table = Table(table_rows, colWidths=[2*cm, 4*cm, 7*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), DARK),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elems.append(table)
            elems.append(Spacer(1, 8))
        i -= 1
    
    # Regular text
    elif line.strip():
        elems.append(Paragraph(line, body_style))
    
    # Empty line
    else:
        elems.append(Spacer(1, 4))
    
    i += 1

# Build PDF
doc.build(elems)
print('✓ PDF created: PHASE_1_DEEP_EXPLANATION.pdf')
