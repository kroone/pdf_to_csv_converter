
import re, pdfplumber, os, json
from math import floor
import pandas as pd


def get_value(value_str):
    pattern_value = '[0-9,]+'
    value = float(re.findall(pattern_value, value_str)[0].replace(',', '.'))
    if '-' in value_str:
        value = value * -1
    return value


def MLP_Buy_Sell_Invoice(text, input_file):
    
    insert_dict = {}

    pattern_invoice = '(?<=Rechnungsnummer )\S+(?=\\n)'
    invoice = re.findall(pattern_invoice, text)[0]
    insert_dict['Notiz'] = re.sub('[/-]',  '_', invoice)

    pattern_invoice_type = '(?<=Wertpapier Abrechnung )\S+(?=\\n)'
    invoice_type = re.findall(pattern_invoice_type, text)[0]
    insert_dict['Typ'] = invoice_type

    pattern_amount = '(?<=Stück ).+'
    desc_list = re.findall(pattern_amount, text)[0].split(' ')
    insert_dict['Wertpapiername'] = ' '.join(desc_list[1:-2])
    amount = float(desc_list[0].replace(',', '.'))
    insert_dict['Stück'] = amount
    insert_dict['ISIN'] = invoice = desc_list[-2]
    insert_dict['WKN'] = desc_list[-1][1:-1]

    pattern_price = '(?<=hrungskurs )\S+'
    price_input = re.findall(pattern_price, text)[0]
    price = get_value(price_input)
    #insert_dict['Wert'] = round(price * insert_dict['Stück'], 2)

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

    insert_dict['Steuern'] = tax   
    pattern_value = '(?<=Kurswert )\S+'
    value_input = re.findall(pattern_value, text)[0]
    value = get_value(value_input)

    pattern_value_final = '(?<=Ausmachender Betrag )\S+'
    value_final_input = re.findall(pattern_value_final, text)[0]
    value_final = get_value(value_final_input)

    insert_dict['Gebühren'] = round(value_final - value - tax, 4)

    if value_final < 0:
        insert_dict['Stück'] = insert_dict['Stück'] * -1

    insert_dict['Stück'] = str(insert_dict['Stück']).replace('.', ',')
    insert_dict['Wert'] = str(value_final).replace('.', ',')
    insert_dict['Gebühren'] = str(insert_dict['Gebühren']).replace('.', ',')

    return insert_dict#, {'amount':amount, 'price':price, 'value':value_final}


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


def read_pdf(pdf_file_path):
    with pdfplumber.open(pdf_file_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        return text


def extract_mlp_pdf(org_file_path):

    assert '.pdf' in org_file_path

    text = read_pdf(org_file_path)

    options_dict = {'MLP Banking AG': 
                {'Wertpapier Abrechnung':MLP_Buy_Sell_Invoice,
                'Ausschüttung Investmentfonds':MLP_Dividends}
                }

    path_bank_accounts = 'bank_accounts.json'
    if os.path.exists(path_bank_accounts):
        with open(path_bank_accounts) as file:
            bank_accounts = json.load(file)
    else:
        bank_accounts = {}


    cols = ['Datum', 'Typ', 'Wert', 'Buchungswährung', 'Bruttobetrag',
        'Währung Bruttobetrag', 'Wechselkurs', 'Gebühren', 'Steuern', 'Stück',
        'ISIN', 'WKN', 'Ticker-Symbol', 'Wertpapiername', 'Notiz']


    df_insert = pd.DataFrame(columns = cols)

    ## bank_accounts must be a list like ["45364":"Wishes", "2356":"Names"]
    assert type(bank_accounts) == dict

    for bank in options_dict.keys():
        if bank in text:

            for invoice_type in options_dict[bank].keys():
                if invoice_type in text:

                    d = options_dict[bank][invoice_type](text, org_file_path)
                    df_insert = df_insert.append(pd.DataFrame.from_dict(d, orient='index').transpose())

                    for bank_acc in bank_accounts.keys():
                        if bank_acc in text:
                            df_insert['depot'] = bank_acc
                            df_insert['konto'] = 'MLP'
                            df_insert['file'] = os.path.basename(org_file_path)
                            break

                    break
            break
            
    return df_insert



class portfolio_tracker:
    def __init__(self, path_to_current_transctions):
        self.transactions_path = path_to_current_transctions


    