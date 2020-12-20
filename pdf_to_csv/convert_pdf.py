import pdfplumber
import re, os, json, shutil
import pandas as pd
from datetime import datetime
from math import floor

# # Define

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
    price = re.findall(pattern_price, text)[0]
    price = float(price.replace(',', '.'))

    insert_dict['Wert'] = round(price * insert_dict['Stück'], 2)

    pattern_day = '(?<=Schlusstag )\S+(?=\\n)'
    day = re.findall(pattern_day, text)[0]
    insert_dict['Datum'] = pd.to_datetime(day, format=('%d.%m.%Y')).strftime('%Y-%m-%dT%H:%M')


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
    #assert(check_values)

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


def convert_pdf(source_folder, target_folder=False, output_folder=False, bank_accounts_file='default'):

    options_dict = {'MLP Banking AG': 
                                {'Wertpapier Abrechnung':MLP_Buy_Sell_Invoice,
                                'Ausschüttung Investmentfonds':MLP_Dividends}
                }

    path_bank_accounts = bank_accounts_file
    if os.path.exists(path_bank_accounts):
        with open(path_bank_accounts) as file:
            bank_accounts = json.load(file)
    else:
        bank_accounts = {}


    cols = ['Datum', 'Typ', 'Wert', 'Buchungswährung', 'Bruttobetrag',
        'Währung Bruttobetrag', 'Wechselkurs', 'Gebühren', 'Steuern', 'Stück',
        'ISIN', 'WKN', 'Ticker-Symbol', 'Wertpapiername', 'Notiz']
    bank_accounts_df_dict = {}
    bank_accounts_df_dict['default'] = pd.DataFrame(columns = cols)
    for bank_acc in bank_accounts.keys():
        bank_accounts_df_dict[bank_acc] = pd.DataFrame(columns = cols)

    ## bank_accounts must be a list like ["45364":"Wishes", "2356":"Names"]
    assert type(bank_accounts) == dict


    # # Input File
    base_folder = source_folder
    filelist = os.listdir(base_folder)

    for input_file in filelist:
        org_file_path = os.path.join(base_folder, input_file)

        if not '.pdf' in input_file:
            'skipped {}'.format(input_file)
            continue

        with pdfplumber.open(org_file_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            #print(text)
        
        bank_account_dict = {}
        for bank in options_dict.keys():
            if bank in text:
                for invoice_type in options_dict[bank].keys():
                    if invoice_type in text:
                        d = options_dict[bank][invoice_type](text, input_file)
                        df_insert = pd.DataFrame.from_dict(d, orient='index').transpose()

                        found_bank_acc = False
                        for bank_acc in bank_accounts.keys():
                            if bank_acc in text:
                                found_bank_acc = True
                                break
                        if found_bank_acc:
                            bank_accounts_df_dict[bank_acc] = bank_accounts_df_dict[bank_acc].append(df_insert)
                        else:
                            bank_accounts_df_dict['default'] = bank_accounts_df_dict['default'].append(df_insert)
                        break


        if target_folder != False:
            path_archiv = os.path.join(target_folder, 'archiv')
            path_converted = os.path.join(target_folder, 'converted')
            for p in [path_archiv, path_converted]:
                if os.path.exists(p) == False:
                    os.mkdir(p)
            
            shutil.copy(org_file_path, path_archiv)
            os.replace(org_file_path, os.path.join(path_converted, '{}_{}_{}'.format(pd.to_datetime(df_insert['Datum'][0]).strftime('%Y%m%d'), df_insert['WKN'][0], df_insert['Notiz'][0])))



    # # Output File

    for bank_acc in bank_accounts_df_dict.keys():
        df_res = bank_accounts_df_dict[bank_acc]
        df_res = df_res.drop_duplicates(subset=['Wertpapiername','Notiz','Stück','Typ','Wert'])
        if len(df_res) == 0:
            continue
        
        if bank_acc == 'default':
            bank_acc_name = bank_acc
        else:
            bank_acc_name = bank_accounts[bank_acc]

        file_name = '{}_{}'.format(bank_acc_name, datetime.now().strftime('%Y%m%d_mlp_transactions.csv'))
        if output_folder != False:
            file_path = os.path.join(output_folder, file_name)
        else:
            file_path = file_name

        df_res.to_csv(file_path, sep=';')



#source_folder, target_folder, output_folder, bank_accounts_file = 'data/examples', 'data/converted', 'data/output', 'bank_accounts.json'
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Convert MLP PDF to CSV for Portfolio Performance.')

    parser.add_argument('--folder', '-f', dest='source_folder', required=True, help='folder with files to be transformed')
    parser.add_argument('--move', '-m', dest='target_folder', required=False, default=False, help='folder to move converted files to')
    parser.add_argument('--output', '-o', dest='output_folder', required=False, default=False, help='folder to save outputfile in')
    parser.add_argument('--bank_accounts', '-b', dest='bank_accounts_file', required=False, default=False, help='file path to bank_accounts.json')

    args = parser.parse_args()

    convert_pdf(args.source_folder, args.target_folder, args.output_folder, args.bank_accounts_file)




