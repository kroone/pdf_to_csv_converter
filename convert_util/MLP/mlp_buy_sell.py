import re
import pandas as pd

from convert_util.util import get_value

def MLP_Buy_Sell_Invoice(text, input_file):
    
    insert_dict = {}

    pattern_invoice = '(?<=Rechnungsnummer )\S+(?=\\n)'
    invoice_1 = re.findall(pattern_invoice, text)[0]
    invoice_1 = re.sub('[/-]',  '_', invoice_1)
    insert_dict['Rechnung'] = invoice_1

    pattern_invoice = '(?<=Auftragsnummer )\S+(?=\\n)'
    invoice_2 = re.findall(pattern_invoice, text)[0]
    insert_dict['Notiz'] = invoice_1 + '_' + invoice_2

    pattern_invoice_type = '(?<=Wertpapier Abrechnung )\S+(?=\\n)'
    invoice_type = re.findall(pattern_invoice_type, text)[0]
    
    if 'Storno' in text:
        insert_dict['Typ'] = 'Storno'
    else:
        insert_dict['Typ'] = invoice_type

    pattern_amount = '(?<=Stück ).+'
    desc_list = re.findall(pattern_amount, text)[0].split(' ')
    insert_dict['Wertpapiername'] = ' '.join(desc_list[1:-2])
    insert_dict['Stück'] = get_value(desc_list[0])
    insert_dict['ISIN'] = invoice = desc_list[-2]
    insert_dict['WKN'] = desc_list[-1][1:-1]

    pattern_price = '(?<=hrungskurs )\S+'
    price_input = re.findall(pattern_price, text)[0]
    insert_dict['Kurs'] = get_value(price_input)

    pattern_day = '(?<=Schlusstag )\S+(?=\\n)'
    day = re.findall(pattern_day, text)[0]
    insert_dict['Datum'] = pd.to_datetime(day, format=('%d.%m.%Y')).strftime('%Y-%m-%dT%H:%M')

    text_array = text.split('\n')
    tax = 0
    for i, text_part in enumerate(text_array):
        pattern1 = 'Kapitalertragsteuer [0-9,]+%'
        pattern2 = 'Solidaritätszuschlag [0-9,]+%'
        pattern3 = 'Kirchensteuer [0-9,]+%'

        for steuer_pattern in [pattern1, pattern2, pattern3]:
            if re.match(steuer_pattern, text_part):
                pattern_euro = '[0-9,-]+ EUR'
                value_str = re.findall(pattern_euro, text_part)[-1]
                value = get_value(value_str)

                #print(i, tax, value, value_str)
                tax = tax + value

                if 'Devisenkurs' in text_part:
                    pattern = '[0-9,]+'
                    insert_dict['Wechselkurs'] = get_value(re.findall(pattern, text_part)[0])
                    
                if 'hrungskurs' in text_part:
                    insert_dict['Währung Bruttobetrag'] = text_part.split(' ')[-1]
                    
                if 'Ausmachender Betrag' in text_part:
                    insert_dict['Buchungswährung'] = text_part.split(' ')[-1]

    insert_dict['Steuern'] = tax   
    pattern_value = '(?<=Kurswert )\S+'
    value_input = re.findall(pattern_value, text)[0]
    value = get_value(value_input)

    pattern_value_final = '(?<=Ausmachender Betrag )\S+'
    value_final_input = re.findall(pattern_value_final, text)[0]
    value_final = get_value(value_final_input)

    insert_dict['Wert'] = value_final
    insert_dict['Bruttobetrag'] = insert_dict['Stück'] * insert_dict['Kurs']
    try:
        insert_dict['Umrechnungsbetrag'] = round(insert_dict['Bruttobetrag'] / insert_dict['Wechselkurs'], 2)
    except KeyError:
        pass

    if invoice_type == 'Kauf':
        insert_dict['Gebühren'] = round(value_final - value - tax, 4)
    else:
        insert_dict['Gebühren'] = round(value_final - value - tax, 4) * -1

    if value_final < 0:
        #insert_dict['Stück'] = insert_dict['Stück'] * -1
        pass

    #format needed for portfolio performance
    for col in [key for key, value in insert_dict.items() if type(value) == float]:
        insert_dict[col] = str(insert_dict[col]).replace('.', ',')

    return insert_dict