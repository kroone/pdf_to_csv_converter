import pandas as pd
import numpy as np
import json
import os
import datetime as dt


def import_csv(source_file):
    file_name = source_file.split('/')[-1]

    df = pd.read_html(source_file)
    df = df[0]
    df.columns = df.loc[0]
    df = df[1:]
    df = df.reset_index(drop=True)
    df.columns = ['Text', 'Buchung', 'PN-Nr.', 'Wert', 'Buchungswährung', 'Betrag']
    return df


def transform_csv(df, file_name, bank_account_json_path='bank_accounts.json'):
    with open(bank_account_json_path) as file:
        bank_account = json.load(file)

    for bank_acc in bank_account.keys():
        if bank_acc in ' '.join(df.Text.values):
            df['Depot'] = bank_account[bank_acc]['D']
            df['Konto'] = bank_account[bank_acc]['K']


    df['Stück'] = df['Text'].str.lower().str.extract('((?<=menge )[\d,]+)')
    df['Stück'] = df['Stück'].str.replace('.', '').str.replace(',', '.')
    df['Stück'] = df['Stück'].fillna(0).astype('float') 

    df['Wert'] = df['Text'].str.lower().str.extract('((?<=kurs )[\d,]+)')
    df['Wert'] = df['Wert'].str.replace('.', '').str.replace(',', '.')
    df['Wert'] = df['Wert'].fillna(0).astype('float') 

    df['Wechselkurs'] = df['Text'].str.lower().str.extract('((?<=devisenkurs )[\d,.]+)')
    df['Wechselkurs'] = df['Wechselkurs'].str.replace('.', '').str.replace(',', '.')
    df['Wechselkurs'] = df['Wechselkurs'].fillna(1).astype('float') 

    df['Datum'] = df['Text'].str.lower().str.extract(r'((?<=handelstag )[\d.]+)')
    missing_trade = df['Datum'] != df['Datum']
    df.loc[missing_trade, 'Datum'] = df.loc[missing_trade, 'Buchung']

    df['Typ'] = df['Text'].str.lower().str.extract(r'((?<=wertpapierabrechnung )\S+)')
    df.loc[df['Text'].str.lower().str.contains('einzahlung'), 'Typ'] = 'Einlieferung'
    df.loc[df['Text'].str.lower().str.contains('dauerauftrag'), 'Typ'] = 'Einlieferung'
    df.loc[df['Text'].str.lower().str.contains('gnisgutschrift investmentfonds'), 'Typ'] = 'Dividende'
    df.loc[df['Text'].str.lower().str.contains('sparplan'), 'Typ'] = 'Einlieferung'
    df.loc[df['Text'].str.lower().str.contains('depotentgelt'), 'Typ'] = 'Gebühren'
    df.loc[df['Text'].str.lower().str.contains('erstattung'), 'Typ'] = 'Gebührenerstattung'

    df['WKN'] = df['Text'].str.extract(r'((?<=WKN )\S+)')
    df['ISIN'] = df['Text'].str.extract(r'((?<=\/ )\S+)')
    df['Wertpapiername'] = df['Text'].str.extract(r'((?<=\/ ).+?(?= DEPOTNR.))')

    for row_iter in df.iterrows():
        try:
            df.loc[row_iter[0], 'Wertpapiername'] = row_iter[1]['Wertpapiername'].replace(row_iter[1]['ISIN'] + ' ', '')
        except:
            pass


    df['Betrag_'] = df['Betrag'].str.extract(r'([+-])') + df['Betrag'].str.extract(r'([\d,.]+)')
    df['Betrag_'] = df['Betrag_'].str.replace(r'.', '').str.replace(',', '.')
    df['Betrag_'] = df['Betrag_'].astype('float')
        

    df['faktor'] = 1
    df.loc[df['Typ'].str.contains('VERKAUF') == True, 'faktor'] = -1

    df['Bruttobetrag'] = df['Stück'] * df['Wert']
    df['Währung Bruttobetrag'] = 'EUR'
    df.loc[df['Wechselkurs'] != 1, 'Bruttobetrag Währung'] = 'USD'

    df['Gebühren'] = (df['Stück'] * (df['Wert'] / df['Wechselkurs'])) + df['Betrag_'] * df['faktor']
    df['Gebühren'] = np.abs(df['Gebühren'].round(2))

    typ_not_buy_sell = df['Typ'].isin(['KAUF', 'VERKAUF']) == False
    df.loc[typ_not_buy_sell, 'Gebühren'] = 0
    df.loc[typ_not_buy_sell, 'Wert'] = df.loc[typ_not_buy_sell, 'Betrag_']
        
    df.loc[(df['Typ'] == 'Einlieferung') & (df['Wert'] < 0), 'Typ'] = 'Auslieferung'

    df['Notiz'] =   pd.Series(["{:02d}".format(row) for row in df.index]) + '_' + file_name
    df['Steuern'] = ''
    df['Ticker-Symbol'] = ''

    return df


def prepare_csv(df):

    typ_dict = {'kauf':'Kauf',
            'verkauf':'Verkauf',
            'Einlieferung':'Einlage',
            'Auslieferung':'Entnahme'}

    cols_depot = ['Datum', 'Typ', 'Wert', 'Buchungswährung', 'Bruttobetrag',
            'Währung Bruttobetrag', 'Wechselkurs', 'Gebühren', 'Steuern', 'Stück',
            'ISIN', 'WKN', 'Ticker-Symbol', 'Wertpapiername', 'Notiz', 'Depot', 'Konto']

    #df_depot_csv = df.loc[df['ISIN'] == df['ISIN'], cols_depot].copy()
    df_csv = df.loc[:, cols_depot].copy()

    for c in ['Wert', 'Steuern', 'Wert', 'Wechselkurs', 'Gebühren', 'Stück', 'Bruttobetrag']:
        df_csv[c] = df_csv[c].astype('str')
        df_csv[c] = df_csv[c].str.replace('.', ',')

    df_csv['Typ'] = df_csv['Typ'].replace(typ_dict)

    df_csv = df_csv.fillna(' ')
    
    return df_csv

    

def convert_to_portfolio_csv(source_folder, target_folder, bank_account_json_path='bank_accounts.json'):
    
    for folder in ['archiv', 'converted']:
        folder_path = os.path.join(target_folder, folder)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

    files = os.listdir(source_folder)
    df = pd.DataFrame()
    for f in files:
        if not '.html' in f:
            continue
        path_file = os.path.join(source_folder, f)
        df_import = import_csv(path_file)
        df_import = transform_csv(df_import, f, bank_account_json_path=bank_account_json_path)
        df = pd.concat([df, df_import], ignore_index=True).reset_index(drop=True)
        os.replace(path_file, os.path.join(target_folder, 'archiv', f))

    df_csv = prepare_csv(df)

    file_name_new = os.path.join(target_folder, 'converted', dt.datetime.now().strftime('%Y%m%d_MLP_Transactions.csv'))
    df_csv.to_csv(file_name_new, sep=';')



#source_folder, target_folder, bank_accounts_file = 'data/examples', 'data/converted', 'data/output', 'bank_accounts.json'
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Convert MLP CSV to CSV for Portfolio Performance.')

    parser.add_argument('--folder', '-f', dest='source_folder', required=True, help='folder with files to be transformed')
    parser.add_argument('--move', '-m', dest='target_folder', required=False, default=False, help='folder to move converted files to')
    parser.add_argument('--bank_accounts', '-b', dest='bank_accounts_file', required=False, default=False, help='file path to bank_accounts.json')

    args = parser.parse_args()

    convert_to_portfolio_csv(args.source_folder, args.target_folder, args.bank_accounts_file)





