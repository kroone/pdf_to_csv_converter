import json, os
import pandas as pd

from convert_util.fileio import read_pdf
from convert_util.MLP.mlp_buy_sell import MLP_Buy_Sell_Invoice
from convert_util.MLP.mlp_dividends import MLP_Dividends

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
    if len(df_insert) == 0:
        print('no results')     
    
    return df_insert