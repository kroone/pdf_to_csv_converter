import pdfplumber
import re, os
import pandas as pd
from datetime import datetime
from math import floor


# # Define

def MLP_Buy_Sell_Invoice(text):
    insert_dict = {}

    pattern_invoice = '(?<=Rechnungsnummer )\S+(?=\\n)'
    invoice = re.findall(pattern_invoice, text)[0]
    insert_dict['Notiz'] = 'File: ' + input_file + '; Rechnung: ' + invoice

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
    price = re.findall(pattern_price, text)[0]
    price = float(price.replace(',', '.'))

    insert_dict['Wert'] = round(price * insert_dict['Stück'], 2)

    pattern_day = '(?<=Schlusstag )\S+(?=\\n)'
    day = re.findall(pattern_day, text)[0]
    insert_dict['Datum'] = pd.to_datetime(day).strftime('%Y-%m-%dT%H:%M')


    pattern_value = '(?<=Kurswert )\S+'
    value_input = re.findall(pattern_value, text)[0]
    value = float(value_input.replace('.', '').replace(',', '.').replace('-', ''))
    pattern_value_final = '(?<=Ausmachender Betrag )\S+'
    value_final = re.findall(pattern_value, text)[0]
    value_final = float(value_final.replace('.', '').replace(',', '.').replace('-', ''))
    insert_dict['Gebühren'] = value_final - value

    insert_dict['Stück'] = str(insert_dict['Stück']).replace('.', ',')
    insert_dict['Wert'] = str(insert_dict['Wert']).replace('.', ',')
    insert_dict['Gebühren'] = str(insert_dict['Gebühren']).replace('.', ',')

    check_values = floor(price * amount) == floor(value_final)
    #print(floor(price * amount), floor(value_final))
    assert(check_values)

    return insert_dict#, {'amount':amount, 'price':price, 'value':value_final}


def MLP_Dividends(text):
    insert_dict = {}

    pattern_invoice = '(?<=Abrechnungsnr. )\S+'
    invoice = re.findall(pattern_invoice, text)[0]
    insert_dict['Notiz'] = 'File: ' + input_file + '; Rechnung: ' + invoice

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
    insert_dict['Datum'] = pd.to_datetime(day).strftime('%Y-%m-%dT%H:%M')
    
    insert_dict['Stück'] = str(insert_dict['Stück']).replace('.', ',')
    insert_dict['Wert'] = str(insert_dict['Wert']).replace('.', ',')
    insert_dict['Steuern'] = str(insert_dict['Steuern']).replace('.', ',')
    
    return insert_dict




options_dict = {'MLP Banking AG': 
                            {'Wertpapier Abrechnung':MLP_Buy_Sell_Invoice,
                            'Ausschüttung Investmentfonds':MLP_Dividends}
               }




cols = ['Datum', 'Typ', 'Wert', 'Buchungswährung', 'Bruttobetrag',
       'Währung Bruttobetrag', 'Wechselkurs', 'Gebühren', 'Steuern', 'Stück',
       'ISIN', 'WKN', 'Ticker-Symbol', 'Wertpapiername', 'Notiz']
result_df = pd.DataFrame(columns = cols)


# # Input File

import argparse

parser = argparse.ArgumentParser(description='Convert MLP PDF to CSV for Portfolio Performance.')

parser.add_argument('--folder', '-f', dest='source_folder', required=True, help='folder with files to be transformed')
parser.add_argument('--move', '-m', dest='target_folder', required=False, default=False, help='folder to move converted files to')
parser.add_argument('--output', '-o', dest='output_folder', required=False, default=False, help='folder to save outputfile in')

args = parser.parse_args()

base_folder = args.source_folder
filelist = os.listdir(base_folder)

for input_file in filelist:
    org_file_path = os.path.join(base_folder, input_file)
    with pdfplumber.open(org_file_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        #print(text)
        
    for bank in options_dict.keys():
        if bank in text:
            for invoice_type in options_dict[bank].keys():
                if invoice_type in text:
                    d = options_dict[bank][invoice_type](text)
                    df_insert = pd.DataFrame.from_dict(d, orient='index').transpose()
                    result_df = result_df.append(df_insert)
           
    if args.target_folder != False:
        new_file_path = os.path.join(args.target_folder, input_file)
        os.replace(org_file_path, new_file_path)



# # Output File

file_name = datetime.now().strftime('%Y%m%d_mlp_transactions.csv')
if args.output_folder != False:
    file_path = os.path.join(args.output_folder, file_name)
else:
    file_path = file_name
result_df.to_csv(file_path, sep=';')







