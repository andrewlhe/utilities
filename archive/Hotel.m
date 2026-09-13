% Initialize Workspace
clc
close all
clear all

%Prompt user input
disp('Welcome to the Hotel Points Valuation Calculator!');
prompt = 'Please enter hotel brand';
prompt = [prompt newline '(M - Marriott/H - Hilton/I - IHG/Y - Hyatt/W - Wyndham/C - Choice/R - Radisson/B - Best Western): '];
Brand = input(prompt,'s');
prompt = 'Points required for award night: ';
Points_Required = input(prompt);
prompt = 'Taxes and fees required for award night: ';
Taxfee_p = input(prompt);
prompt = 'Room rate in cash: ';
Cash = input(prompt);
prompt = 'Taxes and fees in the cash rate: ';
Taxfee_c = input(prompt);


switch Brand
    case{'M'}
        FTP_points = 'Marriott Bonvoy Point';
        name = 'Marriott';
        prompt = 'Do you hold any Marriott credit card? [Y/N] ';
        check_CC = input(prompt,'s');
        if strcmp(check_CC,'Y')
            prompt = 'Select credit card, enter:'; 
            prompt = [prompt newline '1 - Marriott Bonvoy (Business) American Express/Chase Marriott Bonvoy Bonundless (Business),'];
            prompt = [prompt newline '2 - Marriott Bonvoy Brillant American Express/Chase Ritz-Carlton Rewards,'];
            prompt = [prompt newline '3 - Chase Marriott Premier ($85 AF),'];
            prompt = [prompt newline '4 - Chase Marriott ($45 AF)/Chase Marriott Bonvoy Bold ($0 AF) '];
            CC = input(prompt,'s');
            cashback = 0;
            switch CC
                case{'1'}
                    Elite_Bonus = 1;
                    CC_Bonus = 6;
                case{'2'}
                    Elite_Bonus = 2.5;
                    CC_Bonus = 6;
                case{'3'}
                    Elite_Bonus = 1;
                    CC_Bonus = 5;
                case{'4'}
                    CC_Bonus = 3;
            end
        else
            prompt = 'Enter credit card cashback (%): ';
            cashback = input(prompt)/100;
            CC_Bonus = 0;
        end
        
        prompt = 'Elite Status with Marriott? N-General Member, S-Silver, G-Gold, P-Platinum, T-Titanium, A-Ambassador: ';
        Elite = input(prompt, 's');
            switch Elite
                case{'N'}
                    Elite_Bonus = 0;
                case{'S'}
                    Elite_Bonus = .1;
                case{'G'}
                    Elite_Bonus = .25;
                case{'P'}
                    Elite_Bonus = .5;
                case{'T','A'}
                    Elite_Bonus = .75;
            end
            
        Brand_Base = 10;
        prompt = 'Is the property Residence Inn, Towneplace Suites, or Element? [Y/N] ';
        property_type1 = input(prompt,'s');
        if strcmp(property_type1,'Y')
            Brand_Base = 5;
        end
        
        prompt = 'Is the property Marriott Executive Apartments or Execustay? [Y/N] ';
        property_type2 = input(prompt,'s');
        if strcmp(property_type1,'Y')
            Brand_Base = 2.5;
        end
        
    case{'H'}
        FTP_points = 'Hilton point';
        name = 'Hilton';
        prompt = 'Do you hold any Hilton credit card? [Y/N] ';
        check_CC = input(prompt,'s');
        if strcmp(check_CC,'Y')
            prompt = 'Select credit card, enter 1-Amex Hilton,';
            prompt = [prompt newline '2-Amex Hilton Ascend/Amex Hilton Business,'];
            prompt = [prompt newline '3-Amex Hilton Aspire: '];
            CC = input(prompt,'s');
            cashback = 0;
            switch CC
                case{'1'}
                    Elite_Bonus = .2;
                    CC_Bonus = 7;
                case{'2'}
                    Elite_Bonus = .8;
                    CC_Bonus = 12;
                case{'3'}
                    Elite_Bonus = 1;
                    CC_Bonus = 14;
            end
        else
            prompt = 'Enter credit card cashback (%): ';
            cashback = input(prompt)/100;
            CC_Bonus = 0;
        end
        
        prompt = 'Elite Status with Hilton? N-Member, S-Silver, G-Gold, D-Diamond: ';
        Elite = input(prompt, 's');
            switch Elite
                case{'N'}
                    Elite_Bonus = 0;
                case{'S'}
                    Elite_Bonus = .2;
                case{'G'}
                    Elite_Bonus = .8;
                case{'D'}
                    Elite_Bonus = 1;
            end
            
        Brand_Base = 10;
        prompt = 'Is the property Home2 Suites by Hilton or Tru by Hilton? [Y/N] ';
        property_type1 = input(prompt,'s');
        if strcmp(property_type1,'Y')
            Brand_Base = 5;
        end
          
    case{'Y'}
        FTP_points = 'World of Hyatt point';
        name = 'Hyatt';
        prompt = 'Do you hold any Hyatt credit card? [Y/N] ';
        check_CC = input(prompt,'s');
        if strcmp(check_CC,'Y')
            prompt = 'Select credit card, enter 1-Chase World of Hyatt ($95 AF),';
            prompt = [prompt newline '2-Chase Hyatt ($75 AF): '];
            CC = input(prompt,'s');
            cashback = 0;
            Elite_Bonus = .1;
            switch CC
                case{'1'}
                    CC_Bonus = 4;
                case{'2'}
                    CC_Bonus = 3;
            end
        else
            prompt = 'Enter credit card cashback (%): ';
            cashback = input(prompt)/100;
            CC_Bonus = 0;
        end
        
        prompt = 'Elite Status with Hyatt? N-General Member, D-Discoverist, E-Explorist, G-Globalist: ';
        Elite = input(prompt, 's');
            switch Elite
                case{'N'}
                    Elite_Bonus = 0;
                case{'D'}
                    Elite_Bonus = .1;
                case{'E'}
                    Elite_Bonus = .2;
                case{'G'}
                    Elite_Bonus = .3;
            end
            
        Brand_Base = 5;
        
    case{'I'}
        FTP_points = 'IHG point';
        name = 'IHG';
        prompt = 'Do you hold any IHG credit card? [Y/N] ';
        check_CC = input(prompt,'s');
        if strcmp(check_CC,'Y')
            prompt = 'Select credit card, enter 1-Chase IHG Premier,';
            prompt = [prompt newline '2-Chase IHG Traveler,'];
            prompt = [prompt newline '3-Chase IHG ($49 AF): '];
            CC = input(prompt,'s');
            cashback = 0;
            switch CC
                case{'1'}
                    Elite_Bonus = .5;
                    CC_Bonus = 10;
                case{'2'}
                    CC_Bonus = 5;
                case{'3'}
                    Elite_Bonus = .5;
                    CC_Bonus = 5;
            end
        else
            prompt = 'Enter credit card cashback (%): ';
            cashback = input(prompt)/100;
            CC_Bonus = 0;
        end
        
        prompt = 'Elite Status with IHG? N-Club Member, G-Gold, P-Platinum, S-Spire, A-Ambassador: ';
        Elite = input(prompt, 's');
            switch Elite
                case{'N'}
                    Elite_Bonus = 0;
                case{'G'}
                    Elite_Bonus = .1;
                case{'P','A'}
                    Elite_Bonus = .5;
                case{'S'}
                    Elite_Bonus = 1;
            end
            
        Brand_Base = 10;
        prompt = 'Is the property Staybridge Suites or Candlewood Suites? [Y/N] ';
        property_type1 = input(prompt,'s');
        if strcmp(property_type1,'Y')
            Brand_Base = 5;
        end

end

Total_Points = Brand_Base*(1 + Elite_Bonus)*(Cash - Taxfee_c)+ CC_Bonus * Cash;
CPP = (Cash-Taxfee_p)*(1-cashback)/(Points_Required+Total_Points)*100;

disp(' ')
A=['This award room from ', name, ' requires ', num2str(Points_Required), ' ', FTP_points,'s. '];
B=['At a cash price of $',num2str(Cash), ', each ', FTP_points, ' is worth ', num2str(CPP), ' cents.'];

disp(A)
disp(B)