import re
import pandas as pd

def MLP_Dividends(text, input_file):
    insert_dict = {}

    pattern_invoice = '(?<=Abrechnungsnr. )\S+'
    invoice = re.findall(pattern_invoice, text)[0]
    insert_dict['Notiz'] = re.sub('[/-]',  '_', invoice)

    insert_dict['Typ'] = 'Dividende'

    pattern_amount = '(?<=Stück ).+'
    desc_list = re.findall(pattern_amount, text)[0].split(' ')
    insert_dict['Wertpapiername'] = ' '.join(desc_list[1:-2])
    amount = float(desc_list[0].replace(',', '.'))
    insert_dict['Stück'] = amount
    insert_dict['ISIN'] = invoice = desc_list[-2]
    insert_dict['WKN'] = desc_list[-1][1:-1]

    pattern_value = '(?<=Ausschüttung )\d\S+'
    value = re.findall(pattern_value, text)[0]
    value = float(value.replace(',', '.').replace('+',''))
    value

    pattern_value_taxed = '(?<=Ausmachender Betrag )\d\S+'
    value_taxed = re.findall(pattern_value_taxed, text)[0]
    value_taxed = float(value_taxed.replace(',', '.').replace('+',''))
    value_taxed

    insert_dict['Wert'] = round(value_taxed, 2)
    insert_dict['Steuern'] = round(value - value_taxed, 2)

    pattern_day = '(?<=Datum )\S+(?=\\n)'
    day = re.findall(pattern_day, text)[0]
    insert_dict['Datum'] = pd.to_datetime(day, format=('%d.%m.%Y')).strftime('%Y-%m-%dT%H:%M')
    
    insert_dict['Stück'] = str(insert_dict['Stück']).replace('.', ',')
    insert_dict['Wert'] = str(insert_dict['Wert']).replace('.', ',')
    insert_dict['Steuern'] = str(insert_dict['Steuern']).replace('.', ',')
    
    return insert_dict