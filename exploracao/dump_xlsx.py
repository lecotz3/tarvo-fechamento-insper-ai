import openpyxl, sys
wb=openpyxl.load_workbook(sys.argv[1])
for ws in wb.worksheets:
    print('=== SHEET', ws.title, ws.dimensions, ws.sheet_state)
    for row in ws.iter_rows():
        vals=[]
        for c in row:
            if c.value is not None:
                s=f'{c.coordinate}={c.value!r}'
                if c.comment: s+=f' [COMMENT: {c.comment.text}]'
                if c.font and c.font.strike: s+=' [STRIKE]'
                vals.append(s)
        if vals: print(' | '.join(vals))
    print('merged:', ws.merged_cells.ranges)
