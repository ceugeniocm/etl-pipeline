import datetime
import openpyxl

wb = openpyxl.load_workbook('agendaAnonimizado.xlsx', read_only=True)
sheet = wb.active
headers = [cell.value for cell in sheet[1]]
sample_row = list(sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]

special_mappings = {
    "AGM_ID": "id_agendamento",
    "BENEF_NOME": "paciente_nome",
    "DTHORAAGENDA": "data_hora",
    "AGP_VALOR": "valor",
    "AG_STATUSAGENDAMENTO": "status"
}

columns = {}
types = {}

for h, val in zip(headers, sample_row):
    target = special_mappings.get(h, h.lower())
    columns[h] = target
    
    # Guess type based on value and header name
    if h in ["AGP_VALOR", "VALOR_PAGO", "DESCONTO", "ACRESCIMO", "PROC_VALOR"]:
        types[target] = "decimal"
    elif isinstance(val, datetime.datetime):
        types[target] = "datetime"
    elif isinstance(val, datetime.date):
        types[target] = "date"
    elif isinstance(val, datetime.time):
        types[target] = "str" # Time not supported, use str
    elif h.endswith("_ID") or h.endswith("ID") or "USERID" in h or h in ["AGM_ID", "AG_ID", "TPA_ID", "USU_ID", "PAC_ID", "CONV_ID", "LOC_ID", "SET_ID", "SIT_ID", "MOT_ID", "CID_ID", "PROC_ID", "CAN_ID", "SALA_ID", "EQUIPE_ID", "ORIGEM_ID", "DESTINO_ID", "PLANO_ID"]:
        types[target] = "int"
    elif isinstance(val, int):
        types[target] = "int"
    elif isinstance(val, float):
        types[target] = "float"
    else:
        # Fallback to header name inspection if value is None
        if any(x in h for x in ["DTHORA", "DATA", "DTNASC", "DTHAGENDAMENTO", "DTHORALIBERACAO", "DTHR_"]):
             types[target] = "datetime"
        elif h.endswith("ID") or "_ID" in h:
             types[target] = "int"
        else:
             types[target] = "str"

# Manual overrides for consistency with previous config
types["id_agendamento"] = "int"
types["paciente_nome"] = "str"
# If data_hora is time in the sample, it must be str
if isinstance(sample_row[headers.index("DTHORAAGENDA")], datetime.time):
    types["data_hora"] = "str"
else:
    types["data_hora"] = "datetime"
types["valor"] = "decimal"
types["status"] = "str"

import json
print(json.dumps({"columns": columns, "types": types}, indent=2, ensure_ascii=False))
