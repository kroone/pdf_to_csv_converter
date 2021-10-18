import pandas as pd
import re

from convert_util.util import get_value

def MLP_umsatz(path_file):

    df_csv = pd.read_csv(path_file)
    df_csv.head()

    df_umsatz = pd.DataFrame()
    for i, row in df_csv.iterrows():
        insert_dict = {}
        insert_dict['Wert'] = get_value(row.Betrag)
        insert_dict['Datum'] = pd.to_datetime(row.Wert, format=('%d.%m.%Y')).strftime('%Y-%m-%dT%H:%M')
        insert_dict['Typ'] = ''
        
        
        if 'depotentgelt' in row.Text.lower():
            insert_dict['Typ'] = 'Gebühren'
            #print(row.Text)
            
        if 'kauf' in row.Text.lower():
            insert_dict['Typ'] = 'Kauf'
            
            pattern = '(?<=WKN ).+(?= DEPOTNR)'
            text = re.findall(pattern, row.Text)[0]

            wkn, remaining  = text.split('/')
            insert_dict['WKN'] = wkn.replace(' ', '')
            pattern = '\A\S+'
            isin = re.findall(pattern, remaining[1:])[0]
            insert_dict['ISIN'] = isin
            insert_dict['Wertpapiername'] = remaining[len(isin)+2:]
            
            pattern_invoice = '(?<=MENGE )\S+'
            menge = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['Stück'] = get_value(menge)
            
            pattern_invoice = '(?<=KURS )\S+'
            menge = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['Kurs'] = get_value(menge)
            
            pattern_invoice = '(?<=AUFTRAGSNR. )\S+'
            menge = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['Auftrag'] = menge
            
            insert_dict['Bruttobetrag'] = insert_dict['Kurs'] * insert_dict['Stück']
            
            try:
                pattern_invoice = '(?<=DEVISENKURS )\S+'
                devkurs = re.findall(pattern_invoice, row.Text)[0]
                devkurs = re.sub('[A-Z.]', '', devkurs)
                insert_dict['Wechselkurs'] = get_value(devkurs)
                insert_dict['Umrechnungsbetrag'] = round(insert_dict['Bruttobetrag'] / insert_dict['Wechselkurs'], 2)
            except IndexError:
                pass

            
        if 'sparplan' in row.Text.lower():
            insert_dict['Typ'] = 'Einlage'
            
            pattern_invoice = '(?<=WKN )\S+'
            invoice_1 = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['WKN'] = invoice_1
            
        if 'kapitalertragsteuer' in row.Text.lower():
            insert_dict['Typ'] = 'Steuern'
            
        if 'kirchensteuer' in row.Text.lower():
            insert_dict['Typ'] = 'Steuern'
        
        if 'solidaritätszuschlag' in row.Text.lower():
            insert_dict['Typ'] = 'Steuern'
            
        if 'erstattung vertriebsfolgeprovision' in row.Text.lower():
            insert_dict['Typ'] = 'Gebührenerstattung'
            
        if 'vorabpauschale' in row.Text.lower():
            insert_dict['Typ'] = 'Steuern'
            pattern_invoice = '(?<=WKN )\S+'
            invoice_1 = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['WKN'] = invoice_1
            
        if 'erträgnisgutschrift' in row.Text.lower():
            insert_dict['Typ'] = 'Zinsen'
            
            pattern = '(?<=WKN ).+(?= DEPOTNR)'
            text = re.findall(pattern, row.Text)[0]

            wkn, remaining  = text.split('/')
            insert_dict['WKN'] = wkn.replace(' ', '')
            pattern = '\A\S+'
            isin = re.findall(pattern, remaining[1:])[0]
            insert_dict['ISIN'] = isin
            insert_dict['Wertpapiername'] = remaining[len(isin)+2:]
            
            pattern_invoice = '(?<=MENGE )\S+'
            menge = re.findall(pattern_invoice, row.Text)[0]
            insert_dict['Stück'] = get_value(menge)
        
        if 'dauerauftrag' in row.Text.lower():
            insert_dict['Typ'] = 'Einlage'
            
        if insert_dict['Typ'] == '':
            raise Exception
            
        for col in [key for key, value in insert_dict.items() if type(value) == float]:
            insert_dict[col] = str(insert_dict[col]).replace('.', ',')
            pass
                
        pattern = '[\W]'
        key = row.Buchung + row.Betrag + row.Text[:10].lower()
        insert_dict['Notiz'] = re.sub(pattern, '', key)
        insert_dict['file'] = os.path.basename(path_file)
                
        df_insert = pd.DataFrame.from_dict(insert_dict, orient='index').transpose()
        df_umsatz = df_umsatz.append(df_insert)
            
    df_umsatz['depot'] = '8516004237'
    df_umsatz['konto'] = 'MLP'
    df_umsatz = df_umsatz.reset_index(drop=True)
    return df_umsatz