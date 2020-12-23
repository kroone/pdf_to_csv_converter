#!/bin/bash

cp data/converted/archiv/* data/examples
rm data/converted/* -r

python convert_to_portfolio_csv.py -f /workspaces/portfolio_performance_utils/mlp_portfolio_csv/data/examples \
                        -m /workspaces/portfolio_performance_utils/mlp_portfolio_csv/data/converted \
                        -b /workspaces/portfolio_performance_utils/mlp_portfolio_csv/bank_accounts.json