# Convert PDF to CSV

## Purpose
This script aims to convert MLP Banking Data from PDF to CSV. The CSV will be formatted so that it can be read by portfolio performance.

# Function
The script can be called by `python convert_pdf.py`

It takes three additional parameters:
#### source folder: 
command: -f or --folder <br>
Description: Folder in which the PDFs are stored. All files of the folder will be checked. This input is required.

#### target_folder
command: -m or --move <br>
Description: Folder in which the PDFs are moved after they have been read. This funciton is turned of by default.

#### output file path
command: -o or --output <br>
Description: Folder in which the final CSV will be stored. The file is stored in the current location by default.

#### Example Output:
```python convert_pdf.py -f /workspaces/portfolio_pdf_to_csv/data/example_data -o /workspaces/portfolio_pdf_to_csv/data/example_output -m /workspaces/portfolio_pdf_to_csv/data/example_converted```
