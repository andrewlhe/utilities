% Initialize Workspace
close all
clear all


% Prompt user input

disp('Welcome to the eBay Resell ROI Calculator!');
prompt = 'Please enter name of the item: ';
Name = input(prompt, 's');
prompt = 'Please enter purchase price of the item: ';
Price = input(prompt);
prompt = 'Please enter sales tax (%) on the item: ';
Purchase_sales_tax = input(prompt);
prompt = 'Cash back on purchase (%): ';
cash_back = input(prompt);
prompt = 'Please enter variable final value fee (%) on the item: ';
variable_final_value_fee = input(prompt);
prompt = 'Please enter sales tax (%) for the buyer: ';
Sales_sales_tax = input(prompt);
prompt = 'Please enter estimated shipping on the item: ';
estimated_shipping = input(prompt);
prompt = 'Please enter anticipated sale price the item: ';
anticipated_sale = input(prompt);


%% Calculation and output

% find the cost of the item

cost = Price * (1 + Purchase_sales_tax/100) * (1 - cash_back/100);

% find breakeven price

sale = (cost + estimated_shipping + 0.3)/(1 - (1 + Sales_sales_tax/100) * variable_final_value_fee/100);

% find final value fee

final_value_fee = 0.3 + sale * (1 + Sales_sales_tax/100) * variable_final_value_fee/100; 

% profit or loss

profit = anticipated_sale - 0.3 - anticipated_sale * (1 + Sales_sales_tax/100) * variable_final_value_fee/100 - estimated_shipping - cost; 

% Output

A = ['The breakeven sale price is $', num2str(sale)];
B = ['The final value fee is $', num2str(final_value_fee)];
C = ['The profit/loss is $', num2str(profit)];

disp(Name)
disp(A)
disp(B)
disp(C)

