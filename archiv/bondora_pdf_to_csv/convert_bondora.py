import pdfplumber
import re, os, json, shutil
import pandas as pd
from datetime import datetime
from math import floor

def import_bondora_pdf(path_file):
    text = ''
    with pdfplumber.open(path_file) as pdf:
        for page in pdf.pages:
            text = text + '\n' + page.extract_text()
    text_arr = text.split('\n')
    return text_arr


def convert_bondora_pdf(source_folder):
    files = os.listdir(source_folder)

    f = files[0]
    path_file = os.path.join(source_folder, f)
    text_arr = import_bondora_pdf(path_file)

    results = []
    for i, row in enumerate(text_arr):
        date_pattern = '\d{2}.\d{2}.\d{4}'
        euro_pattern = '[\d,.]+\s€'

        try:
            date = re.findall(date_pattern, row)[0]
            euro = re.findall(euro_pattern, row)
            overall = euro[1]
            income = euro[0]
        except IndexError:
            continue
        
        kind = 'unknown'
        for kind_type in ['Überweisen', 'Zinsen']:
            if kind_type in row:
                kind = kind_type

        results.append([date, kind, income, overall])

    cols = ['date', 'kind', 'income', 'overall']
    df = pd.DataFrame(results, columns=cols)
    df['file'] = f

    for col in ['income', 'overall']:
        df[col] = df[col].str.replace(' €', '').str.replace('.', '').str.replace(',', '.')


source_folder = 'data/examples'
    





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




