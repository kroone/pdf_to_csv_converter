
import re, pdfplumber, os, json
from math import floor
import pandas as pd

def parseNumber(text):
    """
        Return the first number in the given text for any locale.
        TODO we actually don't take into account spaces for only
        3-digited numbers (like "1 000") so, for now, "1 0" is 10.
        TODO parse cases like "125,000.1,0.2" (125000.1).
        :example:
        >>> parseNumber("a 125,00 €")
        125
        >>> parseNumber("100.000,000")
        100000
        >>> parseNumber("100 000,000")
        100000
        >>> parseNumber("100,000,000")
        100000000
        >>> parseNumber("100 000 000")
        100000000
        >>> parseNumber("100.001 001")
        100.001
        >>> parseNumber("$.3")
        0.3
        >>> parseNumber(".003")
        0.003
        >>> parseNumber(".003 55")
        0.003
        >>> parseNumber("3 005")
        3005
        >>> parseNumber("1.190,00 €")
        1190
        >>> parseNumber("1190,00 €")
        1190
        >>> parseNumber("1,190.00 €")
        1190
        >>> parseNumber("$1190.00")
        1190
        >>> parseNumber("$1 190.99")
        1190.99
        >>> parseNumber("$-1 190.99")
        -1190.99
        >>> parseNumber("1 000 000.3")
        1000000.3
        >>> parseNumber('-151.744122')
        -151.744122
        >>> parseNumber('-1')
        -1
        >>> parseNumber("1 0002,1.2")
        10002.1
        >>> parseNumber("")
        >>> parseNumber(None)
        >>> parseNumber(1)
        1
        >>> parseNumber(1.1)
        1.1
        >>> parseNumber("rrr1,.2o")
        1
        >>> parseNumber("rrr1rrr")
        1
        >>> parseNumber("rrr ,.o")
    """
    try:
        # First we return None if we don't have something in the text:
        if text is None:
            return None
        if isinstance(text, int) or isinstance(text, float):
            return text
        text = text.strip()
        if text == "":
            return None
        # Next we get the first "[0-9,. ]+":
        n = re.search("-?[0-9]*([,. ]?[0-9]+)+", text).group(0)
        n = n.strip()
        if not re.match(".*[0-9]+.*", text):
            return None
        # Then we cut to keep only 2 symbols:
        while " " in n and "," in n and "." in n:
            index = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            n = n[0:index]
        n = n.strip()
        # We count the number of symbols:
        symbolsCount = 0
        for current in [" ", ",", "."]:
            if current in n:
                symbolsCount += 1
        # If we don't have any symbol, we do nothing:
        if symbolsCount == 0:
            pass
        # With one symbol:
        elif symbolsCount == 1:
            # If this is a space, we just remove all:
            if " " in n:
                n = n.replace(" ", "")
            # Else we set it as a "." if one occurence, or remove it:
            else:
                theSymbol = "," if "," in n else "."
                if n.count(theSymbol) > 1:
                    n = n.replace(theSymbol, "")
                else:
                    n = n.replace(theSymbol, ".")
        else:
            # Now replace symbols so the right symbol is "." and all left are "":
            rightSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            rightSymbol = n[rightSymbolIndex:rightSymbolIndex+1]
            if rightSymbol == " ":
                return parseNumber(n.replace(" ", "_"))
            n = n.replace(rightSymbol, "R")
            leftSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
            leftSymbol = n[leftSymbolIndex:leftSymbolIndex+1]
            n = n.replace(leftSymbol, "L")
            n = n.replace("L", "")
            n = n.replace("R", ".")
        # And we cast the text to float or int:
        n = float(n)
        if n.is_integer():
            return int(n)
        else:
            return n
    except: pass
    return None


def get_value(text):
    value = parseNumber(text)
    if "-" in text:
        #value = value * -1 #ignored because portfolio performance only accepts positve values and distinguishes by type
        pass
    return round(value, 8)


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
        text = ' '.join([page.extract_text() for page in pdf.pages if page.extract_text() != None])
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
    if len(df_insert) == 0:
        print('no results')     
    
    return df_insert



def MLP_umsatz():
    df_umsatz = pd.DataFrame()

    for i, row in df.iterrows():
        insert_dict = {}
        insert_dict['Wert'] = get_value(row.Betrag)
        insert_dict['Datum'] = row.Buchung
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
        
            
        if 'sparplan' in row.Text.lower():
            insert_dict['Typ'] = 'Einlage'
            
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
                
        pattern = '[\W]'
        key = row.Buchung + row.Betrag + row.Text[:10].lower()
        insert_dict['Notiz'] = re.sub(pattern, '', key)
        insert_dict['File'] = os.path.basename(path_file)
                
        df_insert = pd.DataFrame.from_dict(insert_dict, orient='index').transpose()
        df_umsatz = df_umsatz.append(df_insert)
            
    df_umsatz['depot'] = '8516004237'
    df_umsatz['konto'] = 'MLP'
    return df_umsatz



class portfolio_tracker:
    def __init__(self, path_to_current_transctions):
        self.transactions_path = path_to_current_transctions


    